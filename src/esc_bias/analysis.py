"""End-to-end study analyses (design v2.1 §3-§7, §9) -> ``reports/results/``.

:func:`run_analysis` fits the models, runs the bootstrap / permutation / null procedures
and writes the CSV/JSON files that :mod:`esc_bias.figures` reads (column names are a
contract). Settings that control cost (bootstrap size, permutations, null replicates)
live in :class:`Settings`, so the smoke test can run the same code on a tiny problem.

Affinity used for pairs. M2 is ``eta = kappa (q + x'beta + b)``; ``b`` alone is the
affinity *net of* the in-likelihood covariates. Pair-level outputs (``b``, ``delta``,
the network, RQ2, RQ3, sensitivities) use the model-implied **total** pair affinity
``a = x'beta + b`` (draws ``x'beta* + b*`` from the same bootstrap replicate), so a
pair's geography/culture share is not removed from its own estimate. ``b_resid`` is kept
in the dyad tables. ``beta`` is the in-likelihood group contrast (logit units).
"""

from __future__ import annotations

import json
import logging
import multiprocessing as mp
import time
import warnings
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import spearmanr

from esc_bias.covariates import REFERENCE_DIR, dyad_covariates, vif
from esc_bias.inference import (
    lfsr_from_draws,
    make_rng,
    mrqap,
    permutation_p_value,
    permute_covariate_labels,
    qap_correlation,
    reliability_corrected_r,
)
from esc_bias.models import (
    DyadModelResult,
    _eta,
    _limit_blas_threads,
    _m2_curvature,
    _m2_estimate,
    _m2_objective,
    _M2Fit,
    _simulate_order,
    _unpack,
    delta_points_reference,
    fit_crossed_effects,
    fit_rank_ordered_logit,
    m0_leave_one_out,
    model_frame,
    parametric_bootstrap,
)
from esc_bias.network import (
    backbone_credible,
    build_bias_graph,
    concentration_table,
    detect_communities,
    dyads_to_matrix,
    nmi_permutation_test,
    strength_preserving_null,
)

log = logging.getLogger(__name__)

VOTE_TYPES = ("jury", "televote")
ROUNDS = ("final", "semifinal1", "semifinal2")
PERIODS = {"2016-2019": (2016, 2019), "2021-2023": (2021, 2023), "2024-2025": (2024, 2025)}
EARLY, LATE = (2016, 2019), (2021, 2025)
DYAD_COVS_OUT = ["border_land", "same_m49_region", "shared_language"]
BLOC_COLS = ("border_land", "ex_yugoslavia", "ex_ussr", "nordic")
FACE_PAIRS = [
    ("GR", "CY"),
    ("CY", "GR"),
    ("RO", "MD"),
    ("ME", "RS"),
    ("HR", "RS"),
    ("LV", "LT"),
    ("LT", "LV"),
    ("AM", "AZ"),
    ("AZ", "AM"),
]
Z90 = 1.6448536269514722
Z80_POWER = 0.8416212335729143
TOP_K = 20


@dataclass
class Settings:
    """Cost knobs; defaults are the study settings (deviations go to summary.json)."""

    seed: int = 20251117
    B: int = 200
    n_perm: int = 200
    n_dyad_boot: int = 1000
    n_iid: int = 20
    n_strength: int = 100
    n_leiden_seeds: int = 50
    n_qap: int = 2000
    n_mrqap: int = 2000
    n_nmi: int = 2000
    n_jobs: int = 4
    delta_min: float = 2.0
    lfsr_max: float = 0.05


# ----------------------------------------------------------------- parallel helpers
_G: dict[str, Any] = {}


def _worker_init() -> None:
    _limit_blas_threads(1)


def _pmap(fn: Callable[[Any], Any], tasks: list[Any], n_jobs: int) -> list[Any]:
    """Map ``fn`` over ``tasks`` in forked workers (state in ``_G`` is inherited)."""
    if n_jobs <= 1 or len(tasks) < 2:
        return [fn(t) for t in tasks]
    ctx = mp.get_context("fork" if "fork" in mp.get_all_start_methods() else "spawn")
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*fork.*", category=DeprecationWarning)
        with ProcessPoolExecutor(
            max_workers=n_jobs, mp_context=ctx, initializer=_worker_init
        ) as ex:
            return list(ex.map(fn, tasks, chunksize=max(1, len(tasks) // (4 * n_jobs))))


# ----------------------------------------------------------------- small helpers
def _fit_of(res: DyadModelResult) -> _M2Fit:
    fit = res.info["_fit"]
    assert isinstance(fit, _M2Fit)
    return fit


def total_affinity(res: DyadModelResult) -> pd.DataFrame:
    """Per-dyad total affinity ``a = x'beta + b`` with the Laplace SE of ``b``."""
    fit = _fit_of(res)
    par = fit.params
    xb = fit.x @ par.beta if fit.x.shape[1] else np.zeros(len(par.b))
    d = res.dyad_effects
    return pd.DataFrame(
        {
            "voter": d["voter"].astype(str).to_numpy(),
            "receiver": d["receiver"].astype(str).to_numpy(),
            "a": par.b + xb,
            "b_resid": par.b,
            "se": d["se"].to_numpy(float),
            "n_obs": d["n_obs"].to_numpy(int),
        }
    )


def _summary_fit(res: DyadModelResult) -> dict[str, Any]:
    return {
        "aff": total_affinity(res),
        "beta": dict(res.info["beta"]),
        "s2": float(res.variance_components["dyad"]),
        "kappa": dict(res.info["kappa"]),
        "converged": bool(res.info["converged"]),
        "n_ballots": int(res.info["n_ballots"]),
    }


def _fit_task(task: tuple[str, pd.DataFrame]) -> tuple[str, dict[str, Any]]:
    key, frame = task
    res = fit_rank_ordered_logit(frame, _G["cov"])
    out = _summary_fit(res)
    if key.startswith("s13nb"):
        fit = _fit_of(res)
        out["q_keys"] = fit.design.q_keys.copy()
        out["q_eta"] = fit.params.q.copy()
    return key, out


def _top_overlap(a: pd.Series, b: pd.Series, k: int = TOP_K) -> float:
    k = min(k, len(a))
    if k == 0:
        return float("nan")
    return len(set(a.nlargest(k).index) & set(b.nlargest(k).index)) / k


def _compare(primary: pd.DataFrame, other: pd.DataFrame, col: str = "a") -> dict[str, float]:
    """Spearman and top-20 overlap of two dyad tables on their common pairs."""
    p = primary.set_index(["voter", "receiver"])["a"]
    o = other.set_index(["voter", "receiver"])[col]
    common = p.index.intersection(o.index)
    if len(common) < 3:
        return {"spearman": float("nan"), "top20_overlap": float("nan"), "n_pairs": len(common)}
    p, o = p.loc[common], o.loc[common]
    return {
        "spearman": float(spearmanr(p, o).statistic),
        "top20_overlap": _top_overlap(p, o),
        "n_pairs": float(len(common)),
    }


def _q(draws: np.ndarray, lo: float = 0.05, hi: float = 0.95) -> tuple[np.ndarray, np.ndarray]:
    q = np.quantile(draws, [lo, hi], axis=0)
    return q[0], q[1]


def _jsonable(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, list | tuple):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating | float):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    return o


def _write_json(obj: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(_jsonable(obj), indent=2) + "\n")


# ----------------------------------------------------------------- frames
def primary_votes(votes: pd.DataFrame) -> pd.DataFrame:
    """Country voters, finals + semis (the ``exclude`` filter is applied by model_frame)."""
    return votes.loc[votes["voter_is_country"] & votes["round"].isin(ROUNDS)].reset_index(drop=True)


def _years(frame: pd.DataFrame, lo: int, hi: int) -> pd.DataFrame:
    return frame.loc[frame["year"].between(lo, hi)].reset_index(drop=True)


def _bloc_mask(frame: pd.DataFrame, cov: pd.DataFrame) -> np.ndarray:
    bloc = (cov[list(BLOC_COLS)] > 0).any(axis=1)
    idx = pd.MultiIndex.from_arrays([frame["voter"].astype(str), frame["receiver"].astype(str)])
    return bloc.reindex(idx).fillna(False).to_numpy(bool)


def batch_frames(
    v: pd.DataFrame, frames: dict[str, pd.DataFrame], cov: pd.DataFrame
) -> list[tuple[str, pd.DataFrame]]:
    """All point-estimate M2 fits (RQ2 splits, periods, sensitivities)."""
    tasks: list[tuple[str, pd.DataFrame]] = []
    v_all = v.assign(exclude=False)
    for t in VOTE_TYPES:
        f = frames[t]
        fin = f.loc[f["round"].astype(str) == "final"].reset_index(drop=True)
        for tag, src in (("all", f), ("fin", fin)):
            odd = src.loc[src["year"] % 2 == 1].reset_index(drop=True)
            even = src.loc[src["year"] % 2 == 0].reset_index(drop=True)
            tasks += [
                (f"rq2_{tag}_odd_{t}", odd),
                (f"rq2_{tag}_even_{t}", even),
                (f"rq2_{tag}_early_{t}", _years(src, *EARLY)),
                (f"rq2_{tag}_late_{t}", _years(src, *LATE)),
            ]
        for p, (lo, hi) in PERIODS.items():
            tasks.append((f"period_{p}_{t}", _years(f, lo, hi)))
        tasks.append((f"s2_{t}", fin))
        tasks.append((f"s3a_{t}", model_frame(v_all, t)))
        if t == "televote":
            semi_new = (f["year"] >= 2023) & (f["round"].astype(str) != "final")
            tasks.append((f"s5_{t}", f.loc[~semi_new].reset_index(drop=True)))
        for y in sorted(f["year"].unique()):
            tasks.append((f"s7_{y}_{t}", f.loc[f["year"] != y].reset_index(drop=True)))
        tasks.append((f"s13nb_{t}", f.loc[~_bloc_mask(f, cov)].reset_index(drop=True)))
    return [(k, fr) for k, fr in tasks if len(fr) and fr["year"].nunique() >= 1]


# ----------------------------------------------------------------- permutation refit
def _perm_task(task: tuple[str, dict[str, str]]) -> np.ndarray:
    t, mapping = task
    fit: _M2Fit = _G["fits"][t]
    from esc_bias.models import _covariate_matrix

    cov_p = permute_covariate_labels(_G["cov"], mapping)
    x, _ = _covariate_matrix(fit.design.dyads, cov_p)
    refit = _m2_estimate(fit.design, x, fit.scale_by_year, fit.s2, theta0=fit.theta, s2_init=fit.s2)
    return np.asarray(refit.params.beta, float).copy()


def permutation_mappings(cov: pd.DataFrame, n_perm: int, seed: int) -> list[dict[str, str]]:
    """Country relabelings drawn exactly as :func:`esc_bias.inference.permutation_refit`."""
    countries = sorted(set(cov.index.get_level_values(0)) | set(cov.index.get_level_values(1)))
    rng = make_rng(seed)
    out = []
    for _ in range(n_perm):
        sh = rng.permutation(len(countries))
        out.append({c: countries[j] for c, j in zip(countries, sh, strict=True)})
    return out


def permutation_pvalues(
    observed: np.ndarray, null: np.ndarray, names: list[str]
) -> tuple[dict[str, float], float, float]:
    """Per-coefficient two-sided p, and the joint block statistic and p (as permutation_refit)."""
    p = {
        n: permutation_p_value(float(observed[i]), null[:, i], "two-sided")
        for i, n in enumerate(names)
    }
    sd = null.std(axis=0, ddof=1)
    sd = np.where(sd > 0, sd, np.nan)
    joint_null = np.nansum((null / sd) ** 2, axis=1)
    joint = float(np.nansum((observed / sd) ** 2))
    return p, joint, permutation_p_value(joint, joint_null, "greater")


# ----------------------------------------------------------------- iid-affinity null
def _iid_task(task: tuple[str, int]) -> np.ndarray:
    """Simulate ballots with iid affinities (same total variance, beta = 0) and refit."""
    t, seed = task
    fit: _M2Fit = _G["fits"][t]
    des, x, par = fit.design, fit.x, fit.params
    rng = np.random.default_rng(seed)
    observed = des.n_obs_dyad() > 0
    s2_tot = float(_G["s2_tot"][t])
    b_true = np.where(observed, rng.normal(0.0, np.sqrt(s2_tot), des.nd), 0.0)
    truth = replace(par, b=b_true, beta=np.zeros_like(par.beta))
    eta, _ = _eta(des, x, truth)
    sim = des.with_order(_simulate_order(des, eta, rng))
    refit = _m2_estimate(sim, x, fit.scale_by_year, None, theta0=fit.theta, s2_init=fit.s2)
    rp = refit.params
    return rp.b + (x @ rp.beta if x.shape[1] else 0.0)


# ----------------------------------------------------------------- S13
def fit_fixed_quality(fit: _M2Fit, q_eta: np.ndarray) -> np.ndarray:
    """MAP of (beta, b, kappa) on the full design with ``kappa*q`` held at ``q_eta``.

    ``s2`` is held at the primary EB value; one MAP (the kappa Laplace correction is
    linearised at the primary fit). Returns the total affinity ``x'beta + b``.
    """
    des, x = fit.design, fit.x
    nq = des.nq
    theta0 = fit.theta.copy()
    theta0[:nq] = q_eta
    par = _unpack(theta0, nq, x.shape[1], des.nd)
    _, _, tc = _m2_curvature(des, x, par, 1.0 / fit.s2)
    tc = tc[: des.ny if fit.scale_by_year else 0]

    def obj(free: np.ndarray) -> tuple[float, np.ndarray]:
        f, g = _m2_objective(np.concatenate([q_eta, free]), des, x, 1.0 / fit.s2, tc)
        return f, g[nq:]

    res = minimize(
        obj, theta0[nq:], jac=True, method="L-BFGS-B", options={"maxiter": 5000, "maxcor": 20}
    )
    p = _unpack(np.concatenate([q_eta, res.x]), nq, x.shape[1], des.nd)
    return p.b + (x @ p.beta if x.shape[1] else 0.0)


# ----------------------------------------------------------------- RQ2
def stability_table(
    fits: dict[str, dict[str, Any]], n_boot: int, seed: int
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Odd/even ceiling vs early/late drift on a common pair set, dyad-bootstrap CI."""
    rows, extra = [], {}
    rng = np.random.default_rng(seed)

    def series(key: str) -> pd.Series | None:
        f = fits.get(key)
        return None if f is None else f["aff"].set_index(["voter", "receiver"])["a"]

    def corr(x: np.ndarray, y: np.ndarray) -> float:
        return float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 else float("nan")

    for t in VOTE_TYPES:
        for tag, split in (("all", "early_late"), ("fin", "early_late_finals")):
            maybe = {k: series(f"rq2_{tag}_{k}_{t}") for k in ("odd", "even", "early", "late")}
            if any(v is None for v in maybe.values()):
                continue
            s = {k: v for k, v in maybe.items() if v is not None}
            common = s["odd"].index
            for k in ("even", "early", "late"):
                common = common.intersection(s[k].index)
            m = {k: v.loc[common].to_numpy() for k, v in s.items()}
            n = len(common)
            ceil_p, drift_p = corr(m["odd"], m["even"]), corr(m["early"], m["late"])
            sp = lambda a, b: float(spearmanr(a, b).statistic) if len(a) > 2 else np.nan  # noqa: E731
            ceil_s, drift_s = sp(m["odd"], m["even"]), sp(m["early"], m["late"])
            diffs = np.empty(n_boot)
            for i in range(n_boot):
                ix = rng.integers(n, size=n)
                diffs[i] = corr(m["odd"][ix], m["even"][ix]) - corr(m["early"][ix], m["late"][ix])
            lo, hi = np.nanquantile(diffs, [0.025, 0.975]) if n > 2 else (np.nan, np.nan)
            if tag == "all":
                rows.append(
                    {
                        "vote_type": t,
                        "split": "odd_even",
                        "pearson": ceil_p,
                        "spearman": ceil_s,
                        "n_pairs": n,
                        "diff_lo": np.nan,
                        "diff_hi": np.nan,
                    }
                )
            rows.append(
                {
                    "vote_type": t,
                    "split": split,
                    "pearson": drift_p,
                    "spearman": drift_s,
                    "n_pairs": n,
                    "diff_lo": lo,
                    "diff_hi": hi,
                }
            )
            sb = 2 * ceil_p / (1 + ceil_p) if ceil_p > 0 else np.nan
            extra[f"{t}_{tag}"] = {
                "ceiling_pearson": ceil_p,
                "ceiling_spearman": ceil_s,
                "drift_pearson": drift_p,
                "drift_spearman": drift_s,
                "ceiling_minus_drift": ceil_p - drift_p,
                "diff_ci95": [lo, hi],
                "drift_claimed": bool(lo > 0),
                "spearman_brown_reliability": sb,
                "n_pairs": n,
            }
    return pd.DataFrame(rows), extra


def pair_change(
    fits: dict[str, dict[str, Any]], primary: dict[str, DyadModelResult], seed: int
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Early vs late change in total affinity per pair (Laplace SEs), and the MDC."""
    out, mdc = [], {}
    for t in VOTE_TYPES:
        e = fits.get(f"rq2_all_early_{t}")
        lt = fits.get(f"rq2_all_late_{t}")
        if e is None or lt is None:
            continue
        m = e["aff"].merge(lt["aff"], on=["voter", "receiver"], suffixes=("_early", "_late"))
        se = np.sqrt(m["se_early"] ** 2 + m["se_late"] ** 2)
        ch = m["a_late"] - m["a_early"]
        de = delta_points_reference(m["a_early"], result=primary[t], seed=seed)
        dl = delta_points_reference(m["a_late"], result=primary[t], seed=seed)
        df = pd.DataFrame(
            {
                "vote_type": t,
                "voter": m["voter"],
                "receiver": m["receiver"],
                "n_early": m["n_obs_early"],
                "n_late": m["n_obs_late"],
                "b_early": m["a_early"],
                "b_late": m["a_late"],
                "change": ch,
                "change_lo": ch - Z90 * se,
                "change_hi": ch + Z90 * se,
                "delta_early": de,
                "delta_late": dl,
                "delta_change": dl - de,
            }
        )
        df["excludes_zero"] = (df["change_lo"] > 0) | (df["change_hi"] < 0)
        out.append(df)
        n_med = float(np.median(m["n_obs_early"] + m["n_obs_late"]))
        se_med = float(np.median(se))
        mdc_b = (Z90 + Z80_POWER) * se_med
        mdc[t] = {
            "median_n_early_plus_late": n_med,
            "median_se_change": se_med,
            "mdc_logit": mdc_b,
            "mdc_points": float(delta_points_reference(mdc_b, result=primary[t], seed=seed)),
            "n_pairs": len(df),
            "n_excluding_zero": int(df["excludes_zero"].sum()),
            "expected_by_chance_10pct": 0.10 * len(df),
        }
    return (pd.concat(out, ignore_index=True) if out else pd.DataFrame()), mdc


# ----------------------------------------------------------------- MRQAP
def mrqap_table(
    frames: dict[str, pd.DataFrame], cov: pd.DataFrame, n_perm: int, seed: int
) -> pd.DataFrame:
    """MRQAP (Dekker DSP) of b-hat from M2 fitted *without* covariates, per vote type.

    The covariate-free fit keeps the geography/culture signal in b-hat (with covariates
    in the likelihood, the total affinity regresses back to beta by construction).
    """
    rows = []
    for t in VOTE_TYPES:
        res = fit_rank_ordered_logit(frames[t], None, seed=seed)
        aff = res.dyad_effects.astype({"voter": str, "receiver": str})
        y, nodes = dyads_to_matrix(aff, "estimate")
        cf = cov.reset_index()
        xs = {n: dyads_to_matrix(cf, n, nodes=nodes)[0] for n in cov.columns}
        mq = mrqap(y, xs, n_perm=n_perm, seed=seed).reset_index()
        mq.insert(0, "vote_type", t)
        mq["s2_no_covariates"] = float(res.variance_components["dyad"])
        rows.append(mq)
    return pd.concat(rows, ignore_index=True)


# ----------------------------------------------------------------- main
def run_analysis(
    votes: pd.DataFrame,
    results_dir: str | Path = "reports/results",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Run every analysis on the tidy ``votes`` table and write ``results_dir``."""
    st = settings or Settings()
    out = Path(results_dir)
    out.mkdir(parents=True, exist_ok=True)
    runtimes: dict[str, float] = {}
    clock = time.perf_counter()

    def lap(name: str) -> None:
        nonlocal clock
        now = time.perf_counter()
        runtimes[name] = round(now - clock, 1)
        log.info("%s done in %.1fs", name, now - clock)
        clock = now

    v = primary_votes(votes)
    countries = sorted(set(v["voter"].astype(str)) | set(v["receiver"].astype(str)))
    cov = dyad_covariates(countries)
    cov_names = list(cov.columns)
    attrs = pd.read_csv(REFERENCE_DIR / "country_attributes.csv").set_index("code")
    frames = {t: model_frame(v, t) for t in VOTE_TYPES}
    _G.clear()
    _G["cov"] = cov

    # ---- primary fits + bootstrap
    prim: dict[str, DyadModelResult] = {}
    boots = {}
    for t in VOTE_TYPES:
        prim[t] = fit_rank_ordered_logit(frames[t], cov, seed=st.seed)
    lap("primary_fits")
    for t in VOTE_TYPES:
        boots[t] = parametric_bootstrap(
            frames[t],
            prim[t],
            B=st.B,
            seed=st.seed + (0 if t == "jury" else 1),
            n_jobs=st.n_jobs,
        )
    lap("bootstrap")
    _G["fits"] = {t: _fit_of(prim[t]) for t in VOTE_TYPES}

    # ---- RQ1 dyad tables (total affinity draws -> delta draws)
    dyad_tab, a_draws, d_draws = {}, {}, {}
    for t in VOTE_TYPES:
        fit, bt = _fit_of(prim[t]), boots[t]
        aff = total_affinity(prim[t])
        ad = bt.b_draws + (bt.beta_draws @ fit.x.T if fit.x.shape[1] else 0.0)
        dd = delta_points_reference(ad, result=prim[t], seed=st.seed)
        a_draws[t], d_draws[t] = ad, dd
        blo, bhi = _q(ad)
        dlo, dhi = _q(dd)
        c = cov.reindex(pd.MultiIndex.from_frame(aff[["voter", "receiver"]]))
        tab = pd.DataFrame(
            {
                "voter": aff["voter"],
                "receiver": aff["receiver"],
                "n_obs": aff["n_obs"],
                "b": aff["a"],
                "b_lo": blo,
                "b_hi": bhi,
                "delta": dd.mean(0),
                "delta_lo": dlo,
                "delta_hi": dhi,
                "lfsr": lfsr_from_draws(dd),
                **{k: c[k].to_numpy() for k in DYAD_COVS_OUT},
                "b_resid": aff["b_resid"],
                "se_resid": aff["se"],
            }
        )
        dyad_tab[t] = tab
        tab.to_csv(out / f"rq1_dyads_{t}.csv", index=False)
    key = ["voter", "receiver"]
    jt = (
        dyad_tab["jury"][key]
        .reset_index()
        .merge(dyad_tab["televote"][key].reset_index(), on=key, suffixes=("_j", "_t"))
    )
    ij, it_ = jt["index_j"].to_numpy(), jt["index_t"].to_numpy()
    comb_d = (d_draws["jury"][:, ij] + d_draws["televote"][:, it_]) / 2
    comb_a = (a_draws["jury"][:, ij] + a_draws["televote"][:, it_]) / 2
    clo, chi = _q(comb_d)
    alo, ahi = _q(comb_a)
    tj, tt = (
        dyad_tab["jury"].iloc[ij].reset_index(drop=True),
        dyad_tab["televote"].iloc[it_].reset_index(drop=True),
    )
    combined = pd.DataFrame(
        {
            "voter": jt["voter"],
            "receiver": jt["receiver"],
            "n_obs": tj["n_obs"] + tt["n_obs"],
            "b": (tj["b"] + tt["b"]) / 2,
            "b_lo": alo,
            "b_hi": ahi,
            "delta": comb_d.mean(0),
            "delta_lo": clo,
            "delta_hi": chi,
            "lfsr": lfsr_from_draws(comb_d),
            **{k: tj[k] for k in DYAD_COVS_OUT},
            "n_jury": tj["n_obs"],
            "n_televote": tt["n_obs"],
        }
    )
    combined.to_csv(out / "rq1_dyads_combined.csv", index=False)
    lap("rq1_dyads")

    # ---- RQ1 beta: permutation refits (parallel, warm start, fixed s2)
    mappings = permutation_mappings(cov, st.n_perm, st.seed)
    tasks = [(t, m) for t in VOTE_TYPES for m in mappings]
    res_perm = _pmap(_perm_task, tasks, st.n_jobs)
    beta_rows, joint = [], {}
    for t in VOTE_TYPES:
        null = np.array([r for (tt_, _), r in zip(tasks, res_perm, strict=True) if tt_ == t])
        obs = np.array([prim[t].info["beta"][n] for n in cov_names])
        pvals, jstat, jp = permutation_pvalues(obs, null, cov_names)
        joint[t] = {"joint_stat": jstat, "joint_p": jp, "n_perm": st.n_perm}
        bd = boots[t].beta_draws
        sd_b = bd.std(axis=0, ddof=1) if len(bd) > 1 else np.zeros(len(obs))
        lo, hi = obs - Z90 * sd_b, obs + Z90 * sd_b
        pts = delta_points_reference(obs, result=prim[t], seed=st.seed)
        plo = delta_points_reference(lo, result=prim[t], seed=st.seed)
        phi = delta_points_reference(hi, result=prim[t], seed=st.seed)
        for i, n in enumerate(cov_names):
            beta_rows.append(
                {
                    "vote_type": t,
                    "covariate": n,
                    "beta": obs[i],
                    "lo": lo[i],
                    "hi": hi[i],
                    "p_perm": pvals[n],
                    "beta_points": pts[i],
                    "lo_points": plo[i],
                    "hi_points": phi[i],
                    "joint_p_block": jp,
                }
            )
    beta_tab = pd.DataFrame(beta_rows)
    beta_tab.to_csv(out / "rq1_beta.csv", index=False)
    lap("permutation_refits")

    # ---- VIF + MRQAP cross-check
    vif_rows = []
    for t in VOTE_TYPES:
        aff = total_affinity(prim[t])
        c = cov.reindex(pd.MultiIndex.from_frame(aff[["voter", "receiver"]]))
        for cov_name, val in vif(c).items():
            vif_rows.append({"vote_type": t, "covariate": str(cov_name), "vif": val})
    pd.DataFrame(vif_rows).to_csv(out / "rq1_vif.csv", index=False)
    mq_tab = mrqap_table(frames, cov, st.n_mrqap, st.seed)
    mq_tab.to_csv(out / "rq1_mrqap.csv", index=False)
    lap("vif_mrqap")

    # ---- batch of point-estimate fits
    batch = _pmap(_fit_task, batch_frames(v, frames, cov), st.n_jobs)
    fits = dict(batch)
    lap("batch_fits")

    # ---- RQ2
    stab, stab_extra = stability_table(fits, st.n_dyad_boot, st.seed)
    stab.to_csv(out / "rq2_stability.csv", index=False)
    pc, mdc = pair_change(fits, prim, st.seed)
    pc.to_csv(out / "rq2_pair_change.csv", index=False)
    lap("rq2")

    # ---- RQ3
    gd = d_draws["televote"][:, it_] - d_draws["jury"][:, ij]
    glo, ghi = _q(gd)
    gap = pd.DataFrame(
        {
            "voter": jt["voter"],
            "receiver": jt["receiver"],
            "n_jury": tj["n_obs"],
            "n_televote": tt["n_obs"],
            "delta_jury": tj["delta"],
            "delta_televote": tt["delta"],
            "gap": gd.mean(0),
            "gap_lo": glo,
            "gap_hi": ghi,
            "lfsr": lfsr_from_draws(gd),
        }
    )
    gap.to_csv(out / "rq3_gap.csv", index=False)
    m1 = {t: fit_crossed_effects(frames[t], seed=st.seed) for t in VOTE_TYPES}
    m1j = (
        m1["jury"]
        .dyad_effects[["voter", "receiver", "estimate", "se", "n_obs"]]
        .astype({"voter": str, "receiver": str})
    )
    m1t = (
        m1["televote"]
        .dyad_effects[["voter", "receiver", "estimate", "se", "n_obs"]]
        .astype({"voter": str, "receiver": str})
    )
    mm = m1j.merge(m1t, on=key, suffixes=("_j", "_t"))
    g1 = mm["estimate_t"] - mm["estimate_j"]
    s1 = np.sqrt(mm["se_t"] ** 2 + mm["se_j"] ** 2)
    pd.DataFrame(
        {
            "voter": mm["voter"],
            "receiver": mm["receiver"],
            "n_jury": mm["n_obs_j"],
            "n_televote": mm["n_obs_t"],
            "m1_jury": mm["estimate_j"],
            "m1_televote": mm["estimate_t"],
            "gap": g1,
            "gap_lo": g1 - Z90 * s1,
            "gap_hi": g1 + Z90 * s1,
        }
    ).to_csv(out / "rq3_gap_m1.csv", index=False)
    nodes = sorted(set(countries))
    mj, _ = dyads_to_matrix(total_affinity(prim["jury"]), "a", nodes=nodes)
    mt, _ = dyads_to_matrix(total_affinity(prim["televote"]), "a", nodes=nodes)
    qap = qap_correlation(mj, mt, n_perm=st.n_qap, seed=st.seed)
    m1mj, _ = dyads_to_matrix(m1j, "estimate", nodes=nodes)
    m1mt, _ = dyads_to_matrix(m1t, "estimate", nodes=nodes)
    qap1 = qap_correlation(m1mj, m1mt, n_perm=st.n_qap, seed=st.seed)
    rel = {t: stab_extra.get(f"{t}_all", {}).get("spearman_brown_reliability") for t in VOTE_TYPES}
    try:
        corr_r = reliability_corrected_r(qap.statistic, float(rel["jury"]), float(rel["televote"]))
    except (TypeError, ValueError):
        corr_r = float("nan")
    rq3 = {
        "r_raw": qap.statistic,
        "p_qap": qap.p_value,
        "n_perm": st.n_qap,
        "reliability_jury": rel["jury"],
        "reliability_televote": rel["televote"],
        "reliability_source": "odd/even Pearson of total affinity, Spearman-Brown (approximate)",
        "r_corrected": corr_r,
        "r_raw_m1": qap1.statistic,
        "p_qap_m1": qap1.p_value,
        "n_common_pairs": len(gap),
        "gap_mean": float(gap["gap"].mean()),
        "n_gap_interval_excludes_0": int(((gap["gap_lo"] > 0) | (gap["gap_hi"] < 0)).sum()),
        "n_gap_lfsr_lt_005": int((gap["lfsr"] < 0.05).sum()),
    }
    _write_json(rq3, out / "rq3_matrix.json")
    lap("rq3")

    # ---- Network
    g = build_bias_graph(combined[["voter", "receiver", "delta"]], weight_col="delta")
    comm = detect_communities(g, 1.0, n_seeds=st.n_leiden_seeds, seed=st.seed)
    part = comm["partition"]
    pd.DataFrame({"country": list(part), "community": list(part.values())}).to_csv(
        out / "communities.csv", index=False
    )
    bb = backbone_credible(combined, lfsr_max=st.lfsr_max, delta_min=st.delta_min)
    sp_null = strength_preserving_null(g, n=st.n_strength, seed=st.seed)
    # iid-affinity null: simulate ballots with b ~ N(0, var of total affinity), refit
    _G["s2_tot"] = {}
    for t in VOTE_TYPES:
        fit = _fit_of(prim[t])
        obs_mask = fit.design.n_obs_dyad() > 0
        xb = fit.x @ fit.params.beta if fit.x.shape[1] else np.zeros(fit.design.nd)
        _G["s2_tot"][t] = float(fit.s2 + np.var(xb[obs_mask]))
    seeds = np.random.SeedSequence(st.seed).generate_state(st.n_iid)
    itasks = [(t, int(s)) for s in seeds for t in VOTE_TYPES]
    isims = _pmap(_iid_task, itasks, st.n_jobs)
    iid_mod = []
    for r in range(st.n_iid):
        aj, at = isims[2 * r], isims[2 * r + 1]
        dj = delta_points_reference(aj, result=prim["jury"], seed=st.seed)[ij]
        dt = delta_points_reference(at, result=prim["televote"], seed=st.seed)[it_]
        w = jt[key].assign(delta=(dj + dt) / 2)
        gi = build_bias_graph(w, weight_col="delta")
        iid_mod.append(
            detect_communities(gi, 1.0, n_seeds=min(10, st.n_leiden_seeds), seed=st.seed)[
                "modularity"
            ]
        )
    iid_mod_arr = np.array(iid_mod)
    m49 = {c: attrs.loc[c, "un_m49_subregion"] for c in part if c in attrs.index}
    nmi = nmi_permutation_test(part, m49, n_perm=st.n_nmi, seed=st.seed)
    W, wn = dyads_to_matrix(combined, "delta")
    conc = concentration_table(pd.DataFrame(W, index=wn, columns=wn))
    conc.reset_index().to_csv(out / "network_concentration.csv", index=False)
    q_obs = float(comm["modularity"])

    def null_stats(null: np.ndarray) -> dict[str, Any]:
        return {
            "mean": float(np.mean(null)),
            "sd": float(np.std(null, ddof=1)) if len(null) > 1 else float("nan"),
            "max": float(np.max(null)),
            "p": float((1 + np.sum(null >= q_obs)) / (1 + len(null))),
            "n": len(null),
        }

    members: dict[int, list[str]] = {}
    for c, k in part.items():
        members.setdefault(int(k), []).append(c)
    net = {
        "modularity": q_obs,
        "mean_pairwise_ARI": comm["mean_pairwise_ARI"],
        "n_communities": len(members),
        "communities": {str(k): sorted(vs) for k, vs in sorted(members.items())},
        "resolution": 1.0,
        "n_leiden_seeds": st.n_leiden_seeds,
        "null_iid_affinity": null_stats(iid_mod_arr),
        "null_strength_preserving": null_stats(sp_null),
        "nmi_m49": nmi["nmi"],
        "nmi_p": nmi["p_value"],
        "nmi_n_perm": st.n_nmi,
        "backbone_n_edges": bb.number_of_edges(),
        "backbone_edges_top": sorted(
            ((u, v_, round(d["weight"], 2)) for u, v_, d in bb.edges(data=True)),
            key=lambda e: -e[2],
        )[:30],
        "n_positive_edges": int((combined["delta"] > 0).sum()),
        "iid_null_total_variance": _G["s2_tot"],
        "notes": "iid null: b ~ N(0, s2 + var(x'beta_hat)), beta = 0, full M2 refit with "
        "covariates and EB s2, consensus Leiden over 10 seeds; strength null: best of 1 "
        "Leiden per rewired graph (in/out degree exact, strength approximate).",
    }
    _write_json(net, out / "network_summary.json")
    for p in PERIODS:
        rows = []
        for t in VOTE_TYPES:
            f = fits.get(f"period_{p}_{t}")
            if f is None:
                continue
            aff = f["aff"]
            d = delta_points_reference(aff["a"], result=prim[t], seed=st.seed)
            keep = (d >= st.delta_min) & (aff["a"] / aff["se"] > Z90)
            rows.append(
                aff.loc[keep, ["voter", "receiver"]].assign(
                    delta=d[keep.to_numpy()],
                    vote_type=t,
                    b=aff.loc[keep, "a"],
                    n_obs=aff.loc[keep, "n_obs"],
                )
            )
        cols = ["voter", "receiver", "delta", "vote_type", "b", "n_obs"]
        (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=cols)).to_csv(
            out / f"network_edges_{p}.csv", index=False
        )
    lap("network")

    # ---- Sensitivities (point estimates)
    sens: list[dict[str, Any]] = []

    def add(analysis: str, t: str, metric: str, value: float) -> None:
        sens.append({"analysis": analysis, "vote_type": t, "metric": metric, "value": value})

    for t in VOTE_TYPES:
        pa = total_affinity(prim[t])
        add("primary", t, "beta_border_land", prim[t].info["beta"]["border_land"])
        add("primary", t, "s2", prim[t].variance_components["dyad"])
        m1d = m1[t].dyad_effects.astype({"voter": str, "receiver": str})
        for name, df_, col in (
            ("S1_M1", m1d, "estimate"),
            (
                "S1_M0",
                m0_leave_one_out(frames[t]).astype({"voter": str, "receiver": str}),
                "estimate",
            ),
        ):
            for k, val in _compare(pa, df_, col).items():
                add(name, t, k, val)
        for name, k_ in (
            ("S2_finals_only", f"s2_{t}"),
            ("S3a_include_excluded", f"s3a_{t}"),
            ("S5_drop_2023_25_semis", f"s5_{t}"),
        ):
            f = fits.get(k_)
            if f is None:
                if name.startswith("S5"):
                    add(name, t, "note_identical_to_primary", 1.0)
                continue
            for k, val in _compare(pa, f["aff"]).items():
                add(name, t, k, val)
            add(name, t, "beta_border_land", f["beta"]["border_land"])
            add(name, t, "s2", f["s2"])
        loyo = [k for k in fits if k.startswith("s7_") and k.endswith(f"_{t}")]
        if loyo:
            bvals = [fits[k]["beta"]["border_land"] for k in loyo]
            cmp_ = [_compare(pa, fits[k]["aff"]) for k in loyo]
            add("S7_leave_one_year_out", t, "beta_border_land_min", min(bvals))
            add("S7_leave_one_year_out", t, "beta_border_land_max", max(bvals))
            add(
                "S7_leave_one_year_out",
                t,
                "top20_overlap_min",
                min(c["top20_overlap"] for c in cmp_),
            )
            add(
                "S7_leave_one_year_out",
                t,
                "top20_overlap_max",
                max(c["top20_overlap"] for c in cmp_),
            )
            add("S7_leave_one_year_out", t, "spearman_min", min(c["spearman"] for c in cmp_))
            add("S7_leave_one_year_out", t, "n_refits", len(loyo))
        nb = fits.get(f"s13nb_{t}")
        if nb is not None:
            fit = _fit_of(prim[t])
            qk = fit.design.q_keys.astype({"receiver": str, "round": str})
            nbk = nb["q_keys"].astype({"receiver": str, "round": str}).assign(q=nb["q_eta"])
            qm = qk.merge(nbk, on=["receiver", "year", "round"], how="left")["q"].to_numpy()
            prim_q = fit.params.q
            n_missing = int(np.isnan(qm).sum())
            qfix = np.where(np.isnan(qm), prim_q, qm)
            a13 = fit_fixed_quality(fit, qfix)
            s13 = pa.assign(a13=a13)
            for k, val in _compare(pa, s13, "a13").items():
                add("S13_q_from_nonbloc", t, k, val)
            bloc = _bloc_mask(pa, cov)
            add("S13_q_from_nonbloc", t, "mean_a_bloc_primary", float(pa["a"][bloc].mean()))
            add("S13_q_from_nonbloc", t, "mean_a_bloc_s13", float(a13[bloc].mean()))
            dd13 = delta_points_reference(a13[bloc], result=prim[t], seed=st.seed)
            dd0 = delta_points_reference(pa["a"][bloc].to_numpy(), result=prim[t], seed=st.seed)
            add("S13_q_from_nonbloc", t, "mean_delta_bloc_primary", float(dd0.mean()))
            add("S13_q_from_nonbloc", t, "mean_delta_bloc_s13", float(dd13.mean()))
            add("S13_q_from_nonbloc", t, "n_bloc_dyads", int(bloc.sum()))
            add("S13_q_from_nonbloc", t, "q_cells_missing_in_nonbloc_fit", n_missing)
    sens_tab = pd.DataFrame(sens)
    sens_tab.to_csv(out / "sensitivity.csv", index=False)
    lap("sensitivity")

    # ---- Face validity
    fv = []
    tabs = {**dyad_tab, "combined": combined}
    for vt, tab in tabs.items():
        ix = tab.set_index(key)
        for a_, b_ in FACE_PAIRS:
            row = ix.loc[[(a_, b_)]].iloc[0] if (a_, b_) in ix.index else None
            fv.append(
                {
                    "item": f"{a_}->{b_}",
                    "vote_type": vt,
                    "delta": np.nan if row is None else row["delta"],
                    "delta_lo": np.nan if row is None else row["delta_lo"],
                    "delta_hi": np.nan if row is None else row["delta_hi"],
                    "lfsr": np.nan if row is None else row["lfsr"],
                    "n_obs": np.nan if row is None else row["n_obs"],
                }
            )
    nordic = set(attrs.index[attrs["nordic"].astype(bool)])
    for vt, draws, tab in (
        ("jury", d_draws["jury"], dyad_tab["jury"]),
        ("televote", d_draws["televote"], dyad_tab["televote"]),
        ("combined", comb_d, combined),
    ):
        sel = (tab["voter"].isin(nordic) & tab["receiver"].isin(nordic)).to_numpy()
        if sel.any():
            md = draws[:, sel].mean(1)
            lo, hi = np.quantile(md, [0.05, 0.95])
            fv.append(
                {
                    "item": "Nordic within-bloc mean",
                    "vote_type": vt,
                    "delta": md.mean(),
                    "delta_lo": lo,
                    "delta_hi": hi,
                    "lfsr": float(lfsr_from_draws(md[:, None])[0]),
                    "n_obs": int(sel.sum()),
                }
            )
    fv_tab = pd.DataFrame(fv)
    fv_tab.to_csv(out / "face_validity.csv", index=False)
    lap("face_validity")

    # ---- summary
    top10 = combined.nlargest(10, "delta")[
        ["voter", "receiver", "delta", "delta_lo", "delta_hi", "lfsr", "n_obs"]
    ]
    summary = {
        "settings": asdict(st),
        "n_ballots": {t: prim[t].info["n_ballots"] for t in VOTE_TYPES},
        "n_rows": {t: len(frames[t]) for t in VOTE_TYPES},
        "n_dyads": {t: len(dyad_tab[t]) for t in VOTE_TYPES} | {"combined": len(combined)},
        "n_countries": len(countries),
        "sigma2": {t: prim[t].variance_components["dyad"] for t in VOTE_TYPES},
        "kappa": {t: prim[t].info["kappa"] for t in VOTE_TYPES},
        "converged": {t: prim[t].info["converged"] for t in VOTE_TYPES},
        "bootstrap_converged": {t: boots[t].info["n_converged"] for t in VOTE_TYPES},
        "beta": beta_tab.to_dict(orient="records"),
        "beta_joint_block": joint,
        "mrqap": mq_tab[["vote_type", "covariate", "coef", "p_value"]].to_dict(orient="records"),
        "top10_combined": top10.to_dict(orient="records"),
        "n_combined_lfsr_lt_005": int((combined["lfsr"] < 0.05).sum()),
        "expected_false_signs_combined_lfsr_lt_005": float(
            combined.loc[combined["lfsr"] < 0.05, "lfsr"].sum()
        ),
        "rq2": stab_extra,
        "rq2_minimum_detectable_change": mdc,
        "rq3": rq3,
        "network": {k: v_ for k, v_ in net.items() if k != "backbone_edges_top"},
        "face_validity": fv_tab.loc[fv_tab["vote_type"] == "combined"].to_dict(orient="records"),
        "batch_fits_not_converged": sorted(k for k, f in fits.items() if not f["converged"]),
        "runtimes_s": runtimes,
        "affinity_definition": "pair outputs use total affinity a = x'beta + b (b_resid kept)",
        "deviations": _deviations(st),
    }
    lap("summary")
    summary["runtimes_s"] = runtimes
    summary["runtime_total_s"] = round(sum(runtimes.values()), 1)
    _write_json(summary, out / "summary.json")
    return summary


def _deviations(st: Settings) -> list[str]:
    d = [
        f"permutation refits: {st.n_perm} per vote type (spec 1,000), warm start, s2 fixed "
        "at the EB value, kappa re-iterated",
        f"MRQAP / QAP / NMI permutations: {st.n_mrqap} / {st.n_qap} / {st.n_nmi} "
        "(config n_permutations 10,000)",
        f"iid-affinity network null: {st.n_iid} replicates",
        "pair outputs (b, delta, network, RQ2, RQ3, sensitivities) use total affinity "
        "x'beta + b from the covariate model; b_resid is reported alongside",
        "RQ2 per-pair change and period backbone thresholds use Laplace SEs of b "
        "(no bootstrap); MDC at 90% two-sided, 80% power",
        "RQ2 finals-only drift CI is against a finals-only odd/even ceiling",
        "S13: q (eta scale) from an M2 fit without bloc cells (shared land border, "
        "ex-Yugoslavia, ex-USSR, Nordic), then one MAP of (beta, b, kappa) on all cells with "
        "q fixed and s2 at the primary value",
        "S5 applies to televote only (jury has no 2023-25 semi rows)",
        "rq1_beta.csv: beta/lo/hi in logit units, lo/hi = beta +- 1.645 bootstrap SD "
        "(normal approximation; basic-bootstrap quantiles need not contain beta); "
        "beta_points/lo_points/hi_points map them to reference-design points",
        "delta for combined n_obs = n_jury + n_televote",
    ]
    return d


def load_votes(processed_dir: str | Path) -> pd.DataFrame:
    """Read ``votes.parquet`` from the processed directory."""
    return pd.read_parquet(Path(processed_dir) / "votes.parquet")


def iter_result_files() -> Iterable[str]:
    """Names of the files :func:`run_analysis` writes."""
    yield from [
        *(f"rq1_dyads_{t}.csv" for t in ("jury", "televote", "combined")),
        "rq1_beta.csv",
        "rq1_mrqap.csv",
        "rq1_vif.csv",
        "rq2_stability.csv",
        "rq2_pair_change.csv",
        "rq3_gap.csv",
        "rq3_gap_m1.csv",
        "rq3_matrix.json",
        "communities.csv",
        "network_summary.json",
        "network_concentration.csv",
        *(f"network_edges_{p}.csv" for p in PERIODS),
        "sensitivity.csv",
        "face_validity.csv",
        "summary.json",
    ]
