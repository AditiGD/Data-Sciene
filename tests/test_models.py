"""M0/M1/M2, parametric bootstrap and Delta-points on data simulated from the model."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

from esc_bias.config import PROJECT_ROOT
from esc_bias.models import (
    RANK_POINTS,
    delta_points_reference,
    fit_crossed_effects,
    fit_rank_ordered_logit,
    m0_leave_one_out,
    model_frame,
    parametric_bootstrap,
)


def simulate_frame(
    n_countries: int = 24,
    years: tuple[int, ...] = (2016, 2017, 2018, 2019, 2021, 2022),
    rounds: tuple[str, ...] = ("final", "semifinal1"),
    n_perf: int = 18,
    sd_b: float = 1.0,
    beta: float = 0.0,
    log_kappa: np.ndarray | None = None,
    seed: int = 1,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Tidy one-vote-type table simulated from M2 (Gumbel random utilities, top-10).

    Returns the frame, the planted b (indexed by voter, receiver) and a covariate table.
    """
    rng = np.random.default_rng(seed)
    cc = [f"C{i:02d}" for i in range(n_countries)]
    b = rng.normal(0.0, sd_b, (n_countries, n_countries))
    x = (rng.random((n_countries, n_countries)) < 0.2).astype(float)
    lk = np.zeros(len(years)) if log_kappa is None else np.asarray(log_kappa)
    rows = []
    for yi, year in enumerate(years):
        for rnd in rounds:
            perf = rng.choice(n_countries, n_perf, replace=False)
            q = rng.normal(0.0, 1.0, n_perf)
            for v in range(n_countries):
                elig = [k for k in range(n_perf) if perf[k] != v]
                j = perf[elig]
                eta = np.exp(lk[yi]) * (q[elig] + beta * x[v, j] + b[v, j])
                u = eta + rng.gumbel(size=len(elig))
                pts = np.zeros(len(elig), int)
                pts[np.argsort(-u)[:10]] = RANK_POINTS
                rows += [
                    (year, rnd, "jury", cc[v], cc[jj], int(p)) for jj, p in zip(j, pts, strict=True)
                ]
    df = pd.DataFrame(rows, columns=["year", "round", "vote_type", "voter", "receiver", "points"])
    df["exclude"] = False
    df["sensitivity"] = False
    idx = pd.MultiIndex.from_product([cc, cc], names=["voter", "receiver"])
    truth = pd.Series(b.ravel(), index=idx)
    cov = pd.DataFrame({"border": x.ravel()}, index=idx)
    return model_frame(df, "jury"), truth, cov


@pytest.fixture(scope="module")
def sim() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    return simulate_frame(beta=1.0, log_kappa=np.array([-0.4, -0.2, 0.0, 0.0, 0.2, 0.4]))


@pytest.fixture(scope="module")
def m2(sim):
    frame, _, cov = sim
    return fit_rank_ordered_logit(frame, covariates=cov)


def _truth(res, truth: pd.Series) -> np.ndarray:
    de = res.dyad_effects
    return truth.reindex(pd.MultiIndex.from_arrays([de.voter, de.receiver])).to_numpy()


def test_m2_recovers_b_beta_kappa(m2, sim) -> None:
    _, truth, _ = sim
    assert m2.info["converged"]
    de = m2.dyad_effects
    assert list(de.columns[:7]) == [
        "voter",
        "receiver",
        "estimate",
        "se",
        "lower",
        "upper",
        "n_obs",
    ]
    assert np.corrcoef(de.estimate, _truth(m2, truth))[0, 1] > 0.8
    assert m2.info["beta"]["border"] == pytest.approx(1.0, abs=0.25)
    assert 0.6 < m2.variance_components["dyad"] < 1.5
    lk = np.log(list(m2.info["kappa"].values()))
    assert lk.mean() == pytest.approx(0.0, abs=1e-9)
    assert np.max(np.abs(lk - np.array([-0.4, -0.2, 0.0, 0.0, 0.2, 0.4]))) < 0.15
    assert (de.se > 0).all() and m2.info["n_ballots"] == 6 * 2 * 24
    assert {"receiver", "year", "round", "estimate", "se"} <= set(m2.quality_effects)


def test_m2_fixed_s2_and_no_kappa(sim) -> None:
    frame, _, _ = sim
    res = fit_rank_ordered_logit(frame, scale_by_year=False, s2=0.5)
    assert res.variance_components["dyad"] == 0.5
    assert set(res.info["kappa"].values()) == {1.0}
    assert res.info["beta"] == {}


def test_bootstrap_coverage_tiny() -> None:
    frame, truth, _ = simulate_frame(
        n_countries=14, years=(2016, 2017, 2018), rounds=("final",), n_perf=12, seed=4
    )
    res = fit_rank_ordered_logit(frame, scale_by_year=False)
    boot = parametric_bootstrap(frame, res, B=40, seed=1, n_jobs=2)
    assert boot.b_draws.shape == (40, len(res.dyad_effects))
    assert boot.info["n_converged"] == 40
    summ = boot.summaries(0.90)
    assert list(summ[["voter", "receiver"]].itertuples(index=False)) == list(
        res.dyad_effects[["voter", "receiver"]].itertuples(index=False)
    )
    t = _truth(res, truth)
    cover = ((summ.lower <= t) & (t <= summ.upper)).mean()
    assert 0.75 < cover < 0.99
    assert summ.lfsr.between(0, 0.5).all()
    # lfsr flags are mostly the right sign
    flag = summ.lfsr < 0.05
    if flag.sum() >= 5:
        assert (np.sign(summ["mean"][flag]) == np.sign(t[flag])).mean() > 0.85


def test_delta_points_monotone_and_zero() -> None:
    q = np.random.default_rng(0).normal(0, 1, 26)
    b = np.linspace(-3, 3, 41)
    d = delta_points_reference(b, quality=q, n_mc=2000)
    assert d[20] == 0.0  # b = 0
    assert np.all(np.diff(d) >= 0) and d[-1] > 3 and d[0] < -1.5
    assert d.max() <= 12
    draws = np.random.default_rng(1).normal(0, 1, (50, 7))
    d2 = delta_points_reference(draws, quality=q, n_mc=2000)
    assert d2.shape == draws.shape
    assert np.allclose(d2[0], delta_points_reference(draws[0], quality=q, n_mc=2000), atol=1e-9)
    with pytest.raises(ValueError):
        delta_points_reference(b)


def test_delta_default_quality_from_result(m2) -> None:
    d = delta_points_reference(np.array([0.0, 1.0]), result=m2)
    assert d[0] == 0.0 and d[1] > 0


def test_m1_shrinks_low_n_more(sim) -> None:
    frame, truth, _ = sim
    rng = np.random.default_rng(0)
    # voters C00..C11 keep every row, the others keep ~25% -> a spread of dyad n
    keep = (frame["voter"].astype(str) < "C12") | (rng.random(len(frame)) < 0.25)
    fr = frame.loc[keep].reset_index(drop=True)
    res = fit_crossed_effects(fr, seed=0)
    assert res.info["converged"] and res.info["lambda"] > 0
    de = res.dyad_effects
    q = res.quality_effects.set_index(["receiver", "year", "round"])["estimate"]
    qi = pd.MultiIndex.from_arrays([fr.receiver.astype(str), fr.year, fr["round"].astype(str)])
    raw = (
        (fr.points - q.reindex(qi).to_numpy())
        .groupby([fr.voter.astype(str), fr.receiver.astype(str)])
        .mean()
    )
    ratio = (
        de.estimate.to_numpy()
        / raw.reindex(pd.MultiIndex.from_arrays([de.voter, de.receiver])).to_numpy()
    )
    ok = np.abs(raw.reindex(pd.MultiIndex.from_arrays([de.voter, de.receiver]))).to_numpy() > 0.5
    low, high = ok & (de.n_obs <= 3).to_numpy(), ok & (de.n_obs >= 9).to_numpy()
    assert low.sum() > 20 and high.sum() > 20
    assert np.median(ratio[low]) < np.median(ratio[high])
    assert de.loc[low, "se"].mean() > de.loc[high, "se"].mean()
    assert np.all(np.diff(de.sort_values("n_obs").shrinkage.to_numpy()) >= -1e-12)
    assert np.corrcoef(de.estimate, _truth(res, truth))[0, 1] > 0.5
    assert res.variance_components["residual"] > 0


def test_m0_leave_one_out(sim) -> None:
    frame, truth, _ = sim
    m0 = m0_leave_one_out(frame)
    assert {"voter", "receiver", "estimate", "n_obs", "n_8plus"} <= set(m0)
    assert m0.n_obs.sum() == len(frame)
    t = truth.reindex(pd.MultiIndex.from_arrays([m0.voter, m0.receiver])).to_numpy()
    assert np.corrcoef(m0.estimate, t)[0, 1] > 0.5


def test_fit_rejects_mixed_vote_types(sim) -> None:
    frame, _, _ = sim
    two = pd.concat([frame, frame.assign(vote_type="televote")])
    with pytest.raises(ValueError, match="one vote type"):
        fit_rank_ordered_logit(two)


@pytest.mark.rawdata
def test_real_data_jury_televote() -> None:
    path = PROJECT_ROOT / "data" / "processed" / "votes.parquet"
    if not path.is_file():
        pytest.skip("run `make data` first")
    votes = pd.read_parquet(path)
    votes = votes.loc[votes["voter_is_country"]]
    res = {}
    for vt in ("jury", "televote"):
        t0 = time.perf_counter()
        res[vt] = fit_rank_ordered_logit(model_frame(votes, vt))
        res[vt].info["seconds"] = time.perf_counter() - t0
        assert res[vt].info["converged"], vt
        assert 0.05 < res[vt].variance_components["dyad"] < 5
    top = res["televote"].dyad_effects.nlargest(10, "estimate")
    pairs = set(zip(top.voter, top.receiver, strict=True))
    assert {("CY", "GR"), ("GR", "CY")} <= pairs
