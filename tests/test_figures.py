from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from esc_bias import figures

C = ["GR", "CY", "RS", "HR", "SE", "NO", "DE", "FR"]
NAMES = [
    "fig01_affinity_heatmap", "fig03_top_pairs_forest", "fig04_stability",
    "fig05_jury_vs_televote", "fig06_covariate_effects", "fig07_dynamic_backbone",
]  # fmt: skip


def _dyads(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for v in C:
        for r in C:
            if v != r:
                d = rng.normal()
                rows.append(dict(voter=v, receiver=r, n_obs=int(rng.integers(1, 9)), b=d,
                                 b_lo=d - 1, b_hi=d + 1, delta=d, delta_lo=d - 1,
                                 delta_hi=d + 1, lfsr=float(rng.uniform()), border_land=0,
                                 same_m49_region=1, shared_language=0))  # fmt: skip
    return pd.DataFrame(rows)


@pytest.fixture
def results(tmp_path: Path) -> Path:
    rng = np.random.default_rng(0)
    res = tmp_path / "res"
    res.mkdir()
    j, t = _dyads(rng), _dyads(rng)
    j.to_csv(res / "rq1_dyads_jury.csv", index=False)
    t.to_csv(res / "rq1_dyads_televote.csv", index=False)
    _dyads(rng).to_csv(res / "rq1_dyads_combined.csv", index=False)
    pd.DataFrame(
        [dict(vote_type=v, covariate=c, beta=0.5, lo=0.1, hi=0.9, p_perm=0.1)
         for v in ("jury", "televote") for c in ("border_land", "shared_language")]
    ).to_csv(res / "rq1_beta.csv", index=False)  # fmt: skip
    pd.DataFrame(
        [dict(vote_type=v, split=s, pearson=0.4, spearman=0.3, n_pairs=50,
              diff_lo=np.nan if s == "odd_even" else -0.1,
              diff_hi=np.nan if s == "odd_even" else 0.2)
         for v in ("jury", "televote") for s in ("odd_even", "early_late")]
    ).to_csv(res / "rq2_stability.csv", index=False)  # fmt: skip
    g = j[["voter", "receiver"]].copy()
    g["n_jury"], g["n_televote"] = j["n_obs"], t["n_obs"]
    g["delta_jury"], g["delta_televote"] = j["delta"], t["delta"]
    g["gap"] = g["delta_jury"] - g["delta_televote"]
    g["gap_lo"], g["gap_hi"] = g["gap"] - 1, g["gap"] + 1
    g.to_csv(res / "rq3_gap.csv", index=False)
    pd.DataFrame({"country": C, "community": [0, 0, 1, 1, 2, 2, 3, 3]}).to_csv(
        res / "communities.csv", index=False
    )
    for p in figures.PERIODS:
        e = pd.concat([j.assign(vote_type="jury"), t.assign(vote_type="televote")])
        e[["voter", "receiver", "delta", "vote_type"]].to_csv(
            res / f"network_edges_{p}.csv", index=False
        )
    return res


def test_all_figures(results: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attrs = pd.DataFrame(
        {"code": C, "capital_lat": np.linspace(35, 60, 8), "capital_lon": np.linspace(5, 35, 8)}
    )
    (tmp_path / "attrs.csv").write_text(attrs.to_csv(index=False))
    monkeypatch.setattr(figures, "ATTRIBUTES", tmp_path / "attrs.csv")
    out = tmp_path / "out"
    figures.main(results, out)
    for n in NAMES:
        assert (out / f"{n}.png").exists() and (out / f"{n}.svg").exists()


def test_missing_inputs_skipped(tmp_path: Path) -> None:
    assert figures.main(tmp_path / "empty", tmp_path / "out") == []
