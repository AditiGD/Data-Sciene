"""Smoke test: the full analysis pipeline on a small synthetic contest series."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from esc_bias import analysis
from esc_bias.analysis import Settings, iter_result_files, run_analysis
from esc_bias.figures import main as figures_main
from esc_bias.models import RANK_POINTS

COUNTRIES = ["AL", "AM", "AT", "AZ", "BE", "CY", "DE", "GR", "HR", "RS", "SE", "NO", "DK", "FI"]
YEARS = [2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]


def synthetic_votes(seed: int = 1) -> pd.DataFrame:
    """Every country votes in a final (12 songs) and one semi (11 songs) per year."""
    rng = np.random.default_rng(seed)
    n = len(COUNTRIES)
    aff = rng.normal(0, 1.0, (n, n))
    aff[COUNTRIES.index("GR"), COUNTRIES.index("CY")] = 4.0
    aff[COUNTRIES.index("CY"), COUNTRIES.index("GR")] = 4.0
    rows = []
    for year in YEARS:
        for rnd, size in (("final", 12), ("semifinal1", 11)):
            songs = rng.choice(n, size=size, replace=False)
            quality = rng.normal(0, 1, size)
            types = ["televote"] if rnd != "final" and year >= 2023 else ["jury", "televote"]
            for vt in types:
                scale = 0.5 if vt == "jury" else 1.0
                for v in range(n):
                    elig = [k for k in range(size) if songs[k] != v]
                    u = np.array([quality[k] + scale * aff[v, songs[k]] for k in elig])
                    u += rng.gumbel(size=len(u))
                    pts = np.zeros(len(elig), int)
                    top = np.argsort(-u)[:10]
                    pts[top] = RANK_POINTS[: len(top)]
                    for k, p in zip(elig, pts, strict=True):
                        rows.append((year, rnd, vt, COUNTRIES[v], COUNTRIES[songs[k]], int(p)))
    df = pd.DataFrame(rows, columns=["year", "round", "vote_type", "voter", "receiver", "points"])
    return df.assign(voter_is_country=True, exclude=False, sensitivity=False)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_run_analysis_writes_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    votes = synthetic_votes()
    st = Settings(
        B=4,
        n_perm=3,
        n_dyad_boot=20,
        n_iid=2,
        n_strength=3,
        n_leiden_seeds=3,
        n_qap=10,
        n_mrqap=10,
        n_nmi=10,
        n_jobs=1,
    )
    res = tmp_path / "results"
    summary = run_analysis(votes, res, st)
    for name in iter_result_files():
        assert (res / name).exists(), name

    comb = pd.read_csv(res / "rq1_dyads_combined.csv")
    expected = [
        "voter",
        "receiver",
        "n_obs",
        "b",
        "b_lo",
        "b_hi",
        "delta",
        "delta_lo",
        "delta_hi",
        "lfsr",
        "border_land",
        "same_m49_region",
        "shared_language",
    ]
    assert expected == list(comb.columns[: len(expected)])
    assert comb["lfsr"].between(0, 1).all()
    gr_cy = comb.set_index(["voter", "receiver"]).loc[("GR", "CY"), "delta"]
    assert gr_cy > comb["delta"].quantile(0.9)  # planted affinity is recovered

    stab = pd.read_csv(res / "rq2_stability.csv")
    assert set(stab["split"]) == {"odd_even", "early_late", "early_late_finals"}
    beta = pd.read_csv(res / "rq1_beta.csv")
    assert {"vote_type", "covariate", "beta", "lo", "hi", "p_perm"} <= set(beta.columns)
    assert set(pd.read_csv(res / "rq3_gap.csv").columns) >= {"gap", "gap_lo", "gap_hi"}
    assert "r_corrected" in json.loads((res / "rq3_matrix.json").read_text())
    assert summary["n_countries"] == len(COUNTRIES)

    monkeypatch.chdir(Path(analysis.__file__).resolve().parents[2])  # F7 reads attributes
    written = figures_main(res, tmp_path / "figures")
    stems = {p.stem for p in written}
    assert stems == {
        "fig01_affinity_heatmap",
        "fig03_top_pairs_forest",
        "fig04_stability",
        "fig05_jury_vs_televote",
        "fig06_covariate_effects",
        "fig07_dynamic_backbone",
    }
