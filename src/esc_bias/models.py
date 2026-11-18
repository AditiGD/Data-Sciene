"""Joint song-quality + dyad-affinity models (primary estimators, design v2.1 §3-§4).

Why (plan review C1): the leave-one-out baseline is contaminated by the bias it measures
and treats bounded, ordinal, zero-inflated ballot points as interval data. The models
below estimate quality and affinity *jointly*, separately per vote type.

- **M2** :func:`fit_rank_ordered_logit` (primary): top-10 Plackett-Luce on each ballot,
  ``eta = kappa_year * (q_show,receiver + x_vj' beta + b_vj)``, ``b ~ N(0, s2)`` with
  ``s2`` by empirical Bayes (MacKay fixed point on the Laplace approximation).
- **M1** :func:`fit_crossed_effects`: linear crossed model on points with an
  empirical-Bayes ridge on ``b`` (variance ratio from random ballot halves).
- **M0** :func:`m0_leave_one_out`: the v1 leave-one-out residual per pair (descriptive).
- :func:`parametric_bootstrap` simulates ballots from a fitted M2 and refits;
  :func:`delta_points_reference` turns affinities into expected extra points on a
  canonical 26-song final.

Ported from ``pilot/esc_models.py`` (``Design``, ``m0_loo``, ``m1_fit``,
``m1_eb_lambda``, ``pl_nll_grad``, ``m2_fit``, ``simulate_points``).
"""

from __future__ import annotations

import ctypes
import multiprocessing as mp
import os
import warnings
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
import pandas as pd
from scipy.optimize import minimize

from esc_bias.baseline import leave_one_out_mean

KEYS = ["year", "round", "vote_type", "voter", "receiver"]

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

#: Eurovision points by rank (rank 1 = 12 points).
RANK_POINTS = np.array([12, 10, 8, 7, 6, 5, 4, 3, 2, 1])
#: Prior precision of the "fixed" effects (song quality q, covariate slopes beta).
PREC_FIXED = 1e-4
_Z90 = 1.6448536269514722


def model_frame(
    votes: pd.DataFrame,
    vote_type: str,
    sensitivity_run: bool = False,
    rounds: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Rows a model for one vote type should see, with categorical id columns.

    Args:
        votes: tidy table *with* anomaly columns (``exclude``, ``sensitivity``).
        vote_type: ``"jury"``, ``"televote"`` or ``"combined"``.
        sensitivity_run: also drop rows marked ``sensitivity`` (e.g. 2016-17 juries).
        rounds: restrict to these rounds (e.g. ``("final",)`` for the finals-only check).

    Adds ``dyad`` (``"VOTER>RECEIVER"``) and ``receiver_year_round`` (the quality unit).
    """
    for col in ("exclude", "sensitivity"):
        if col not in votes:
            raise KeyError(f"column {col!r} missing: apply anomalies.apply_register first")
    keep = (votes["vote_type"] == vote_type) & ~votes["exclude"]
    if sensitivity_run:
        keep &= ~votes["sensitivity"]
    if rounds is not None:
        keep &= votes["round"].isin(rounds)
    df = votes.loc[keep].copy()
    df["dyad"] = (df["voter"] + ">" + df["receiver"]).astype("category")
    df["receiver_year_round"] = (
        df["receiver"] + ":" + df["year"].astype(str) + ":" + df["round"]
    ).astype("category")
    for col in ("voter", "receiver", "round"):
        df[col] = df[col].astype("category")
    return df.reset_index(drop=True)


@dataclass
class DyadModelResult:
    """Common return type of the fitting functions.

    Attributes:
        vote_type: the vote type the model was fitted on.
        dyad_effects: one row per (voter, receiver): ``estimate``, ``se``, ``lower``,
            ``upper`` (shrunken / partially pooled), ``n_obs``.
        quality_effects: one row per (receiver, year, round): ``estimate``, ``se``.
        variance_components: e.g. ``{"dyad": ..., "quality": ..., "voter": ...}``.
        info: estimator name, convergence diagnostics, seed, package versions.
    """

    vote_type: str
    dyad_effects: pd.DataFrame
    quality_effects: pd.DataFrame
    variance_components: dict[str, float] = field(default_factory=dict)
    info: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- design
@dataclass
class _Design:
    """Ballot matrices for one vote type (rows = ballots, columns = eligible receivers).

    A ballot is ``(year, round, voter)``; its eligible set is every receiver with a row
    on that ballot (0-point rows included). ``order[i, k]`` is the column ranked
    ``k + 1`` on ballot ``i``; ``rvalid[i, k]`` is False for padding when a ballot ranks
    fewer than ``K`` entries.
    """

    qidx: IntArray  # (B, M) quality index of each cell
    didx: IntArray  # (B, M) dyad index of each cell
    mask: npt.NDArray[np.bool_]  # (B, M) cell is an eligible receiver
    order: IntArray  # (B, K)
    rvalid: npt.NDArray[np.bool_]  # (B, K)
    ybal: IntArray  # (B,) year index of each ballot
    years: IntArray  # (ny,)
    dyads: pd.MultiIndex  # (voter, receiver)
    q_keys: pd.DataFrame  # receiver, year, round
    row_bal: IntArray  # long-format rows: ballot, column, points
    row_col: IntArray
    row_points: FloatArray

    @property
    def n_ballots(self) -> int:
        return int(self.qidx.shape[0])

    @property
    def nq(self) -> int:
        return len(self.q_keys)

    @property
    def nd(self) -> int:
        return len(self.dyads)

    @property
    def ny(self) -> int:
        return len(self.years)

    @property
    def qflat(self) -> IntArray:
        return self.qidx[self.mask]

    @property
    def dflat(self) -> IntArray:
        return self.didx[self.mask]

    @property
    def row_q(self) -> IntArray:
        return self.qidx[self.row_bal, self.row_col]

    @property
    def row_d(self) -> IntArray:
        return self.didx[self.row_bal, self.row_col]

    def n_obs_dyad(self) -> IntArray:
        return np.bincount(self.dflat, minlength=self.nd)

    def with_order(self, order: IntArray) -> _Design:
        """Same design with simulated rankings (points rows are then stale)."""
        return replace(self, order=order)


def _single_vote_type(frame: pd.DataFrame) -> str:
    if "vote_type" not in frame:
        return "unknown"
    vts = pd.unique(frame["vote_type"].astype(str))
    if len(vts) != 1:
        raise ValueError(f"fit one vote type at a time (got {sorted(vts)}); use model_frame")
    return str(vts[0])


def _build_design(frame: pd.DataFrame) -> _Design:
    """Index the long table of one vote type into ballot matrices."""
    df = pd.DataFrame(
        {
            "year": frame["year"].astype(int).to_numpy(),
            "round": frame["round"].astype(str).to_numpy(),
            "voter": frame["voter"].astype(str).to_numpy(),
            "receiver": frame["receiver"].astype(str).to_numpy(),
            "points": frame["points"].astype(float).to_numpy(),
        }
    )
    if df.duplicated(["year", "round", "voter", "receiver"]).any():
        raise ValueError("duplicate (year, round, voter, receiver) rows: one vote type only")
    df["bal"] = df.groupby(["year", "round", "voter"], sort=True).ngroup()
    df["qk"] = df.groupby(["receiver", "year", "round"], sort=True).ngroup()
    dyads = pd.MultiIndex.from_frame(
        df[["voter", "receiver"]].drop_duplicates().sort_values(["voter", "receiver"])
    )
    df["dk"] = dyads.get_indexer(pd.MultiIndex.from_frame(df[["voter", "receiver"]]))
    df = df.sort_values(["bal", "receiver"]).reset_index(drop=True)
    df["col"] = df.groupby("bal").cumcount()
    n_bal, n_col = int(df["bal"].max()) + 1, int(df["col"].max()) + 1
    bal = df["bal"].to_numpy()
    col = df["col"].to_numpy()
    qidx = np.zeros((n_bal, n_col), np.int64)
    didx = np.zeros((n_bal, n_col), np.int64)
    mask = np.zeros((n_bal, n_col), bool)
    qidx[bal, col] = df["qk"].to_numpy()
    didx[bal, col] = df["dk"].to_numpy()
    mask[bal, col] = True

    top = df.loc[df["points"] > 0].sort_values(["bal", "points"], ascending=[True, False])
    if top.duplicated(["bal", "points"]).any():
        raise ValueError("tied positive points on a ballot: not a ranked ballot")
    rank = np.asarray(top.groupby("bal").cumcount().to_numpy(), dtype=np.int64)
    n_rank = int(np.max(rank)) + 1 if len(rank) else 0
    order = np.zeros((n_bal, max(n_rank, 1)), np.int64)
    rvalid = np.zeros_like(order, dtype=bool)
    order[top["bal"].to_numpy(), rank] = top["col"].to_numpy()
    rvalid[top["bal"].to_numpy(), rank] = True

    bal_info = df.drop_duplicates("bal").sort_values("bal")
    years = np.sort(df["year"].unique()).astype(np.int64)
    ybal = np.searchsorted(years, bal_info["year"].to_numpy()).astype(np.int64)
    q_keys = (
        df.drop_duplicates("qk").sort_values("qk")[["receiver", "year", "round"]]
    ).reset_index(drop=True)
    return _Design(
        qidx=qidx,
        didx=didx,
        mask=mask,
        order=order,
        rvalid=rvalid,
        ybal=ybal,
        years=years,
        dyads=dyads,
        q_keys=q_keys,
        row_bal=bal.astype(np.int64),
        row_col=col.astype(np.int64),
        row_points=df["points"].to_numpy(float),
    )


def _covariate_matrix(
    dyads: pd.MultiIndex, covariates: pd.DataFrame | None
) -> tuple[FloatArray, list[str]]:
    """Dyad x covariate matrix aligned with ``dyads``; missing pairs get 0."""
    if covariates is None or covariates.shape[1] == 0:
        return np.zeros((len(dyads), 0)), []
    if covariates.index.nlevels != 2:
        raise ValueError("covariates must be indexed by (voter, receiver)")
    cov = covariates.copy()
    cov.index = pd.MultiIndex.from_arrays(
        [cov.index.get_level_values(i).astype(str) for i in (0, 1)]
    )
    x = cov.reindex(dyads).fillna(0.0).to_numpy(dtype=float)
    return x, [str(c) for c in covariates.columns]


# --------------------------------------------------------------------------- M2 core
def _pl_nll(
    eta: FloatArray, des: _Design, want_hess: bool = False
) -> tuple[float, FloatArray, FloatArray | None]:
    """Top-K Plackett-Luce negative log-likelihood, gradient and Hessian diagonal in eta."""
    n_bal = des.n_ballots
    rows = np.arange(n_bal)
    avail = des.mask.copy()
    nll = 0.0
    g_eta = np.zeros_like(eta)
    h_eta = np.zeros_like(eta) if want_hess else None
    for k in range(des.order.shape[1]):
        valid = des.rvalid[:, k]
        c = des.order[:, k]
        e = np.where(avail, eta, -np.inf)
        m = e.max(1)
        m = np.where(np.isfinite(m), m, 0.0)
        w = np.exp(e - m[:, None])
        z = w.sum(1)
        z = np.where(z > 0, z, 1.0)
        p = w / z[:, None]
        p[~valid] = 0.0
        nll -= float((eta[rows, c] - m - np.log(z))[valid].sum())
        g_eta += p
        g_eta[rows[valid], c[valid]] -= 1.0
        if h_eta is not None:
            h_eta += p * (1.0 - p)
        avail[rows[valid], c[valid]] = False
    return nll, g_eta, h_eta


@dataclass
class _M2Params:
    """``q`` is stored on the eta scale (``kappa_y * q``); see :attr:`quality`."""

    q: FloatArray
    beta: FloatArray
    b: FloatArray
    log_kappa: FloatArray  # mean zero (empty when not scaled by year)


def _unpack(theta: FloatArray, nq: int, p: int, nd: int) -> _M2Params:
    u = theta[nq + p + nd :]
    return _M2Params(
        q=theta[:nq],
        beta=theta[nq : nq + p],
        b=theta[nq + p : nq + p + nd],
        log_kappa=u - u.mean() if len(u) else u,
    )


def _kappa_bal(des: _Design, par: _M2Params) -> FloatArray:
    if len(par.log_kappa) == 0:
        return np.ones(des.n_ballots)
    return np.exp(par.log_kappa)[des.ybal]


def _eta(des: _Design, x: FloatArray, par: _M2Params) -> tuple[FloatArray, FloatArray]:
    """``eta = kappa*q + kappa*(x'beta + b)`` with ``kappa*q`` a free parameter per show."""
    dyad_u = par.b + (x @ par.beta if x.shape[1] else 0.0)
    kap = _kappa_bal(des, par)
    return par.q[des.qidx] + kap[:, None] * dyad_u[des.didx], kap


def _m2_objective(
    theta: FloatArray,
    des: _Design,
    x: FloatArray,
    prec_b: float,
    tcorr: FloatArray,
) -> tuple[float, FloatArray]:
    """Penalised NLL; ``0.5 * sum_y kappa_y^2 T_y`` is the linearised Laplace log-det term.

    Without it the joint mode is degenerate: inflating ``kappa`` shrinks the ``b`` needed
    and so the prior penalty (``kappa`` scales the dyad variance like a variance
    component). The term makes the ``kappa`` update a Laplace-EM step on the marginal
    likelihood.
    """
    p = x.shape[1]
    par = _unpack(theta, des.nq, p, des.nd)
    eta, kap = _eta(des, x, par)
    nll, g_eta, _ = _pl_nll(eta, des)
    gq = np.bincount(des.qflat, g_eta[des.mask], minlength=des.nq) + PREC_FIXED * par.q
    gd = np.bincount(des.dflat, (g_eta * kap[:, None])[des.mask], minlength=des.nd)
    gb = gd + prec_b * par.b
    gbeta = x.T @ gd + PREC_FIXED * par.beta
    nll += 0.5 * (
        PREC_FIXED * float(par.q @ par.q + par.beta @ par.beta) + prec_b * float(par.b @ par.b)
    )
    parts = [gq, gbeta, gb]
    if len(par.log_kappa):
        k2 = np.exp(2.0 * par.log_kappa)
        nll += 0.5 * float(k2 @ tcorr)
        dyad_part = eta - par.q[des.qidx]
        g_logk = np.bincount(des.ybal, (g_eta * dyad_part).sum(1), minlength=des.ny)
        g_logk += k2 * tcorr
        parts.append(g_logk - g_logk.mean())
    return nll, np.concatenate(parts)


def _m2_curvature(
    des: _Design, x: FloatArray, par: _M2Params, prec_b: float
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Laplace diagonal posterior precision of (kappa*q, b) and the kappa correction T_y."""
    eta, kap = _eta(des, x, par)
    _, _, h = _pl_nll(eta, des, want_hess=True)
    assert h is not None
    hq = np.bincount(des.qflat, h[des.mask], minlength=des.nq) + PREC_FIXED
    hb = np.bincount(des.dflat, (h * (kap**2)[:, None])[des.mask], minlength=des.nd) + prec_b
    vb = 1.0 / hb
    tcorr = np.bincount(des.ybal, (h * vb[des.didx] * des.mask).sum(1), minlength=des.ny)
    return hq, hb, tcorr


@dataclass
class _M2Fit:
    """Everything needed to re-simulate and refit an M2 model (kept in ``info['_fit']``)."""

    design: _Design
    x: FloatArray
    scale_by_year: bool
    theta: FloatArray
    s2: float
    converged: bool
    n_em: int
    nll: float
    beta_names: list[str] = field(default_factory=list)

    @property
    def params(self) -> _M2Params:
        return _unpack(self.theta, self.design.nq, self.x.shape[1], self.design.nd)


def _m2_map(
    des: _Design,
    x: FloatArray,
    s2: float,
    tcorr: FloatArray,
    theta0: FloatArray,
    maxiter: int = 5000,
) -> tuple[FloatArray, bool, float]:
    res = minimize(
        _m2_objective,
        theta0,
        args=(des, x, 1.0 / s2, tcorr),
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": maxiter, "maxcor": 20, "gtol": 1e-5},
    )
    return np.asarray(res.x, float), bool(res.success), float(res.fun)


def _m2_estimate(
    des: _Design,
    x: FloatArray,
    scale: bool,
    s2: float | None,
    theta0: FloatArray | None = None,
    s2_init: float = 0.5,
    tol: float = 1e-3,
    max_em: int = 100,
) -> _M2Fit:
    """Laplace-EM: MAP of (q, beta, b) and kappa given s2, then MacKay update of s2.

    Runs until the relative change of ``s2`` and the absolute change of every
    ``log kappa_y`` are below ``tol`` (or ``max_em`` outer iterations). With ``s2``
    given, only ``kappa`` is iterated (one MAP when ``scale`` is False).
    """
    ny = des.ny if scale else 0
    theta = np.zeros(des.nq + x.shape[1] + des.nd + ny) if theta0 is None else theta0.copy()
    estimate = s2 is None
    cur = s2_init if s2 is None else float(s2)
    observed = des.n_obs_dyad() > 0
    par = _unpack(theta, des.nq, x.shape[1], des.nd)
    _, _, tcorr = _m2_curvature(des, x, par, 1.0 / cur)
    tcorr = tcorr[:ny]
    iterate = estimate or scale
    converged = False
    ok, nll, n_em = False, np.nan, 0
    for n_em in range(1, (max_em if iterate else 1) + 1):  # noqa: B007
        old_lk = par.log_kappa
        theta, ok, nll = _m2_map(des, x, cur, tcorr, theta)
        par = _unpack(theta, des.nq, x.shape[1], des.nd)
        _, hb, tc = _m2_curvature(des, x, par, 1.0 / cur)
        tcorr = tc[:ny]
        change = float(np.max(np.abs(par.log_kappa - old_lk))) if ny else 0.0
        if estimate:
            pvar = 1.0 / hb[observed]
            gamma = float(np.sum(1.0 - pvar / cur))
            new = max(float(np.sum(par.b[observed] ** 2) / max(gamma, 1.0)), 1e-6)
            change = max(change, abs(new - cur) / cur)
            cur = new
        if not iterate or change < tol:
            converged = True
            if estimate:  # final MAP at the converged s2
                theta, ok, nll = _m2_map(des, x, cur, tcorr, theta)
            break
    return _M2Fit(
        design=des,
        x=x,
        scale_by_year=scale,
        theta=theta,
        s2=cur,
        converged=converged and ok,
        n_em=n_em,
        nll=nll,
    )


def fit_rank_ordered_logit(
    frame: pd.DataFrame,
    covariates: pd.DataFrame | None = None,
    scale_by_year: bool = True,
    s2: float | None = None,
    seed: int | None = 0,
) -> DyadModelResult:
    """M2: top-10 rank-ordered logit (Plackett-Luce) with crossed effects, one vote type.

    Each ballot ``(year, round, voter)`` is a top-K ranking (K = number of receivers
    with points, 10 in real data) of its eligible set (all receivers with a row on that
    ballot, 0-point ones included)::

        eta_vj = kappa_y * (q_{j,show} + x_vj' beta + b_vj),   b_vj ~ N(0, s2)

    ``q`` (receiver x year x round) and ``beta`` get a vague N(0, 1e4) prior; ``kappa_y``
    is a per-year precision with ``mean(log kappa) = 0`` (identified because ``b`` and
    ``beta`` are shared across years). ``kappa`` scales the dyad variance, so it is
    estimated on the Laplace marginal likelihood (Laplace-EM; a joint MAP over ``kappa``
    and ``b`` is degenerate), and ``s2`` by empirical Bayes (MacKay fixed point), both
    iterated to convergence (tolerance 1e-3, at most 100 outer iterations) unless ``s2``
    is given. Dyad SEs are Laplace-diagonal posterior SDs.

    Args:
        frame: rows of one vote type, e.g. from :func:`model_frame`.
        covariates: numeric dyad covariates indexed by ``(voter, receiver)``; missing
            pairs are 0.
        scale_by_year: estimate ``kappa_y`` (False: ``kappa = 1``).
        s2: fix the dyad variance instead of estimating it.
        seed: recorded only (the fit is deterministic).

    Returns:
        :class:`DyadModelResult` with ``info`` keys ``beta``, ``kappa``, ``converged``,
        ``n_ballots``, ``n_em``, ``nll`` and ``_fit`` (internal state used by
        :func:`parametric_bootstrap`).
    """
    vote_type = _single_vote_type(frame)
    des = _build_design(frame)
    x, names = _covariate_matrix(des.dyads, covariates)
    fit = _m2_estimate(des, x, scale_by_year, s2)
    fit.beta_names = names
    return _m2_result(vote_type, fit, seed, s2_estimated=s2 is None)


def _m2_result(
    vote_type: str, fit: _M2Fit, seed: int | None, s2_estimated: bool
) -> DyadModelResult:
    des, par = fit.design, fit.params
    hq, hb, _ = _m2_curvature(des, fit.x, par, 1.0 / fit.s2)
    kap_q = np.ones(des.nq)
    if len(par.log_kappa):
        kap_q = np.exp(par.log_kappa)[np.searchsorted(des.years, des.q_keys["year"].to_numpy())]
    se_b, se_q = 1.0 / np.sqrt(hb), 1.0 / np.sqrt(hq) / kap_q
    dyad = pd.DataFrame(
        {
            "voter": des.dyads.get_level_values(0),
            "receiver": des.dyads.get_level_values(1),
            "estimate": par.b,
            "se": se_b,
            "lower": par.b - _Z90 * se_b,
            "upper": par.b + _Z90 * se_b,
            "n_obs": des.n_obs_dyad(),
        }
    )
    quality = des.q_keys.assign(estimate=par.q / kap_q, se=se_q)
    kappa = dict(zip(des.years.tolist(), np.exp(par.log_kappa).tolist(), strict=False))
    if not fit.scale_by_year:
        kappa = dict.fromkeys(des.years.tolist(), 1.0)
    return DyadModelResult(
        vote_type=vote_type,
        dyad_effects=dyad,
        quality_effects=quality,
        variance_components={"dyad": fit.s2},
        info={
            "estimator": "M2 top-K rank-ordered logit (Plackett-Luce), Laplace EB",
            "beta": dict(zip(fit.beta_names, par.beta.tolist(), strict=True)),
            "kappa": kappa,
            "converged": fit.converged,
            "s2_estimated": s2_estimated,
            "n_em": fit.n_em,
            "nll": fit.nll,
            "n_ballots": des.n_ballots,
            "seed": seed,
            "interval": "90% Laplace (estimate +/- 1.645 se)",
            "_fit": fit,
        },
    )


def _simulate_order(des: _Design, eta: FloatArray, rng: np.random.Generator) -> IntArray:
    """Rankings from the random-utility form of Plackett-Luce (Gumbel noise)."""
    u = eta + rng.gumbel(size=eta.shape)
    u[~des.mask] = -np.inf
    k = des.order.shape[1]
    top = np.argsort(-u, axis=1)[:, :k]
    return np.where(des.rvalid, top, 0).astype(np.int64)


# --------------------------------------------------------------------------- bootstrap
@dataclass
class BootstrapResult:
    """Parametric-bootstrap draws for an M2 fit.

    Attributes:
        dyads: ``voter``, ``receiver`` rows aligned with the columns of ``b_draws`` (the
            same order as ``result.dyad_effects``).
        b_draws: ``(B, n_dyads)`` draws of the dyad affinities.
        beta_draws: ``(B, n_covariates)`` draws of ``beta``.
        kappa_draws: ``(B, n_years)`` draws of ``kappa_y``.
        s2_draws: ``(B,)`` dyad variance used/estimated in each refit.
        beta_names: covariate names (columns of ``beta_draws``).
        info: settings (``B``, ``seed``, ``mode``, ``refit_s2``, ``n_jobs``, convergence).
    """

    dyads: pd.DataFrame
    b_draws: FloatArray
    beta_draws: FloatArray
    kappa_draws: FloatArray
    s2_draws: FloatArray
    beta_names: list[str]
    info: dict[str, Any] = field(default_factory=dict)

    def summaries(self, level: float = 0.90) -> pd.DataFrame:
        """Per-dyad ``mean``, equal-tailed ``lower``/``upper`` and ``lfsr`` from the draws.

        ``lfsr = min(P(b >= 0), P(b <= 0))`` (equal to ``min(P(b>0), P(b<0))`` for
        continuous draws; a dyad whose draws are all 0 gets lfsr 1).
        """
        alpha = (1.0 - level) / 2.0
        d = self.b_draws
        lo, hi = np.quantile(d, [alpha, 1.0 - alpha], axis=0)
        lfsr = np.minimum((d >= 0).mean(0), (d <= 0).mean(0))
        return self.dyads.assign(mean=d.mean(0), lower=lo, upper=hi, lfsr=lfsr)


_BOOT: dict[str, Any] = {}


_BLAS_SET_THREADS = (
    "scipy_openblas_set_num_threads64_",
    "scipy_openblas_set_num_threads",
    "openblas_set_num_threads64_",
    "openblas_set_num_threads",
)


def _limit_blas_threads(n: int = 1) -> None:
    """Best-effort: one BLAS thread per worker (OpenBLAS loaded by numpy/scipy, Linux).

    Without it each forked worker runs a full OpenBLAS thread pool and the bootstrap is
    slower in parallel than serially. No-op where ``/proc/self/maps`` is unavailable.
    """
    try:
        with open("/proc/self/maps") as fh:
            libs = {ln.split()[-1] for ln in fh if "openblas" in ln.lower() and "/" in ln}
    except OSError:
        return
    for lib in libs:
        try:
            handle = ctypes.CDLL(lib)
        except OSError:
            continue
        for name in _BLAS_SET_THREADS:
            fn = getattr(handle, name, None)
            if fn is not None:
                fn(ctypes.c_int(n))
                break


def _boot_init(fit: _M2Fit, limit_threads: bool = False) -> None:
    """Worker initialiser: the fitted model is shipped once per process."""
    if limit_threads:
        _limit_blas_threads(1)
    _BOOT["fit"] = fit


def _boot_one(task: tuple[np.random.SeedSequence, str, bool]) -> tuple[Any, ...]:
    ss, mode, refit_s2 = task
    fit: _M2Fit = _BOOT["fit"]
    des, x, par = fit.design, fit.x, fit.params
    rng = np.random.default_rng(ss)
    observed = des.n_obs_dyad() > 0
    if mode == "prior":
        b_true = np.where(observed, rng.normal(0.0, np.sqrt(fit.s2), des.nd), 0.0)
    else:
        b_true = par.b
    truth = replace(par, b=b_true)
    eta, _ = _eta(des, x, truth)
    sim = des.with_order(_simulate_order(des, eta, rng))
    refit = _m2_estimate(
        sim,
        x,
        fit.scale_by_year,
        None if refit_s2 else fit.s2,
        theta0=fit.theta,
        s2_init=fit.s2,
    )
    rp = refit.params
    return rp.b, b_true, rp.beta, np.exp(rp.log_kappa), refit.s2, refit.converged


def parametric_bootstrap(
    frame: pd.DataFrame,
    result: DyadModelResult,
    B: int = 200,
    seed: int = 0,
    refit_s2: bool = False,
    mode: Literal["prior", "fitted"] = "prior",
    n_jobs: int | None = None,
) -> BootstrapResult:
    """Parametric bootstrap of an M2 fit: simulate ballots on the real design and refit.

    Ballots are simulated with Gumbel noise from the fitted ``(q, kappa, beta)`` on the
    design stored in ``result`` (``frame`` is checked for consistency only) and refitted
    with a warm start; ``s2`` stays at the original EB value unless ``refit_s2``.

    ``mode="prior"`` (default): each replicate draws fresh affinities
    ``b* ~ N(0, s2_hat)``; the reported draw is ``b_hat - (b_hat* - b*)``, i.e. the fitted
    estimate minus a replicate of the estimation error. This gives EB-calibrated
    intervals and lfsr (the error includes shrinkage bias, q-b covariance and, with
    ``refit_s2``, s2 uncertainty). ``mode="fitted"``: simulate from ``b_hat`` itself and
    report the refitted ``b_hat*`` (percentile bootstrap; under-covers because the
    shrunken ``b_hat`` is shrunk again). ``beta`` draws are ``2 beta_hat - beta_hat*`` in
    both modes (basic bootstrap).

    Args:
        n_jobs: worker processes (default ``min(4, cpu count)``; 1 = serial).
    """
    fit = result.info.get("_fit")
    if not isinstance(fit, _M2Fit):
        raise TypeError("result must come from fit_rank_ordered_logit")
    if len(frame) != len(fit.design.row_bal):
        raise ValueError("frame does not match the design of the fitted result")
    if mode not in ("prior", "fitted"):
        raise ValueError(f"unknown mode {mode!r}")
    tasks = [(ss, mode, refit_s2) for ss in np.random.SeedSequence(seed).spawn(B)]
    n_jobs = min(4, os.cpu_count() or 1) if n_jobs is None else max(1, n_jobs)
    if n_jobs == 1 or B < 2:
        _boot_init(fit)
        try:
            out = [_boot_one(t) for t in tasks]
        finally:
            _BOOT.clear()
    else:
        # fork: no `if __name__ == "__main__"` guard needed in scripts; workers only run
        # numpy/scipy code, so the "multi-threaded fork" warning is not a concern here.
        ctx = mp.get_context("fork" if "fork" in mp.get_all_start_methods() else "spawn")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*fork.*", category=DeprecationWarning)
            with ProcessPoolExecutor(
                max_workers=n_jobs, mp_context=ctx, initializer=_boot_init, initargs=(fit, True)
            ) as ex:
                out = list(ex.map(_boot_one, tasks, chunksize=max(1, B // (4 * n_jobs))))
    par = fit.params
    b_star = np.array([o[0] for o in out])
    b_true = np.array([o[1] for o in out])
    b_draws = par.b[None, :] - (b_star - b_true) if mode == "prior" else b_star
    beta_star = np.array([o[2] for o in out]).reshape(B, -1)
    des = fit.design
    return BootstrapResult(
        dyads=pd.DataFrame(
            {"voter": des.dyads.get_level_values(0), "receiver": des.dyads.get_level_values(1)}
        ),
        b_draws=b_draws,
        beta_draws=2.0 * par.beta[None, :] - beta_star,
        kappa_draws=np.array([o[3] for o in out]).reshape(B, -1),
        s2_draws=np.array([o[4] for o in out], float),
        beta_names=list(fit.beta_names),
        info={
            "B": B,
            "seed": seed,
            "mode": mode,
            "refit_s2": refit_s2,
            "n_jobs": n_jobs,
            "n_converged": int(sum(bool(o[5]) for o in out)),
            "vote_type": result.vote_type,
        },
    )


# --------------------------------------------------------------------------- delta points
def _reference_quality(result: DyadModelResult) -> FloatArray:
    """Fitted q of the final in the median year of ``result`` (lower middle if even)."""
    qe = result.quality_effects
    finals = qe.loc[qe["round"].astype(str) == "final"]
    if finals.empty:
        finals = qe
    years = np.sort(finals["year"].unique())
    year = years[(len(years) - 1) // 2]
    sel = finals.loc[finals["year"] == year]
    if "round" in sel:
        sel = sel.loc[sel["round"].astype(str) == str(sel["round"].iloc[0])]
    return sel["estimate"].to_numpy(float)


def delta_points_reference(
    b: npt.ArrayLike,
    n_songs: int = 26,
    quality: npt.ArrayLike | None = None,
    n_mc: int = 4000,
    seed: int = 0,
    result: DyadModelResult | None = None,
) -> FloatArray:
    """Expected extra points from affinity ``b`` on a canonical ``n_songs`` ballot.

    Receiver *j* has the median of ``quality``; the ``n_songs - 1`` competitors take
    ``quality``'s quantiles (used as-is when it has exactly ``n_songs - 1`` values).
    Utilities get Gumbel noise (Plackett-Luce, ``kappa = 1``) with common random numbers
    across all ``b``, so ``Delta(0) = 0`` exactly and ``Delta`` is monotone in ``b``.
    Points are 12, 10, 8, ..., 1 for ranks 1-10.

    Args:
        b: affinities, any shape (e.g. ``(B, n_dyads)`` bootstrap draws).
        quality: song qualities of the reference show; default (needs ``result``) the
            fitted q of the median-year final of that vote type.
        result: an M2 result supplying the default ``quality``.

    Returns:
        Array of the same shape as ``b``.
    """
    b_arr = np.asarray(b, dtype=float)
    if quality is None:
        if result is None:
            raise ValueError("give `quality` or an M2 `result` to take it from")
        quality = _reference_quality(result)
    qual = np.asarray(quality, dtype=float).ravel()
    n_other = n_songs - 1
    q_j = float(np.median(qual))
    if len(qual) == n_other:
        q_others = np.sort(qual)
    else:
        q_others = np.quantile(qual, (np.arange(n_other) + 0.5) / n_other)
    rng = np.random.default_rng(seed)
    g = rng.gumbel(size=(n_mc, n_songs))
    base = q_j + g[:, 0]
    others = np.sort(q_others[None, :] + g[:, 1:], axis=1)
    pts_by_beaten = np.zeros(n_other + 1)
    k = min(len(RANK_POINTS), n_songs)
    # number of competitors *below* j -> points (all n_other below = rank 1)
    pts_by_beaten[n_other - np.arange(k)] = RANK_POINTS[:k]

    values = np.unique(np.append(b_arr.ravel(), 0.0))
    if len(values) > 2001:
        values = np.unique(np.append(np.linspace(values[0], values[-1], 2001), 0.0))
    # vectorised per-row searchsorted via row offsets on one flattened sorted array
    span = 2.0 * float(np.abs(others).max() + np.abs(values).max() + np.abs(base).max()) + 1.0
    offs = np.arange(n_mc)[:, None] * span
    flat = (others + offs).ravel()
    expected = np.empty(len(values))
    chunk = max(1, 2_000_000 // n_mc)
    for s in range(0, len(values), chunk):
        v = values[s : s + chunk]
        u = base[:, None] + v[None, :] + offs
        beaten = np.searchsorted(flat, u, side="right") - np.arange(n_mc)[:, None] * n_other
        expected[s : s + chunk] = pts_by_beaten[beaten].mean(0)
    f0 = expected[np.searchsorted(values, 0.0)]
    return np.interp(b_arr, values, expected) - f0


# --------------------------------------------------------------------------- M1
def _random_half_s2b(des: _Design, resid: FloatArray, rng: np.random.Generator) -> float:
    """Dyad variance: covariance of dyad mean residuals between random ballot halves."""
    half = rng.random(des.n_ballots) < 0.5
    in_a = half[des.row_bal]
    rd = des.row_d
    means = []
    for sel in (in_a, ~in_a):
        c = np.bincount(rd[sel], minlength=des.nd)
        s = np.bincount(rd[sel], resid[sel], minlength=des.nd)
        means.append((s / np.maximum(c, 1), c))
    both = (means[0][1] > 0) & (means[1][1] > 0)
    if both.sum() < 3:
        return 1e-3
    return max(float(np.cov(means[0][0][both], means[1][0][both])[0, 1]), 1e-3)


def fit_crossed_effects(
    frame: pd.DataFrame, seed: int | None = 0, max_iter: int = 2000, tol: float = 1e-8
) -> DyadModelResult:
    """M1: linear crossed model on points with an empirical-Bayes ridge, one vote type.

    ``points = q_{receiver,show} + b_vj + e``, ``e ~ (0, s2_e)``, ridge on ``b`` with
    ``lambda = s2_e / s2_b``. ``s2_b`` is the covariance of dyad mean residuals (points
    minus receiver-show mean) between two *random* halves of the ballots (seeded; not the
    odd/even split used for RQ2), ``s2_e`` the remaining residual variance. Fitted by
    backfitting; SEs use this fit's residual variance, ``se_b = sqrt(s2_e / (n + lambda))``.
    Estimates are in points. ``dyad_effects`` also has ``shrinkage = n / (n + lambda)``.
    """
    vote_type = _single_vote_type(frame)
    des = _build_design(frame)
    y, rq, rd = des.row_points, des.row_q, des.row_d
    nq_cnt = np.bincount(rq, minlength=des.nq)
    nd_cnt = np.bincount(rd, minlength=des.nd)
    q0 = np.bincount(rq, y, minlength=des.nq) / np.maximum(nq_cnt, 1)
    r0 = y - q0[rq]
    rng = np.random.default_rng(seed)
    s2b = _random_half_s2b(des, r0, rng)
    s2e0 = max(float(r0.var()) - s2b, 1e-3)
    lam = s2e0 / s2b
    b = np.zeros(des.nd)
    q = q0
    converged = False
    it = 0
    for it in range(1, max_iter + 1):  # noqa: B007
        q = np.bincount(rq, y - b[rd], minlength=des.nq) / np.maximum(nq_cnt, 1)
        b_new = np.bincount(rd, y - q[rq], minlength=des.nd) / (nd_cnt + lam)
        delta = float(np.max(np.abs(b_new - b)))
        b = b_new
        if delta < tol:
            converged = True
            break
    resid = y - q[rq] - b[rd]
    s2e = float(resid.var())
    se_b = np.sqrt(s2e / (nd_cnt + lam))
    se_q = np.sqrt(s2e / np.maximum(nq_cnt, 1))
    dyad = pd.DataFrame(
        {
            "voter": des.dyads.get_level_values(0),
            "receiver": des.dyads.get_level_values(1),
            "estimate": b,
            "se": se_b,
            "lower": b - _Z90 * se_b,
            "upper": b + _Z90 * se_b,
            "n_obs": nd_cnt,
            "shrinkage": nd_cnt / (nd_cnt + lam),
        }
    )
    return DyadModelResult(
        vote_type=vote_type,
        dyad_effects=dyad,
        quality_effects=des.q_keys.assign(estimate=q, se=se_q),
        variance_components={"dyad": s2b, "residual": s2e},
        info={
            "estimator": "M1 linear crossed model, EB ridge (random ballot halves)",
            "lambda": lam,
            "converged": converged,
            "n_iter": it,
            "n_ballots": des.n_ballots,
            "seed": seed,
            "interval": "90% (estimate +/- 1.645 se)",
        },
    )


# --------------------------------------------------------------------------- M0
def m0_leave_one_out(frame: pd.DataFrame) -> pd.DataFrame:
    """M0: v1 leave-one-out residual averaged per (voter, receiver).

    Row residual = points minus the mean points the receiver got from the *other* voters
    of the same year x round x vote type (:func:`esc_bias.baseline.leave_one_out_mean`);
    rows of singleton groups are dropped. Returns ``voter``, ``receiver``, ``estimate``,
    ``sd``, ``n_obs`` and ``n_8plus`` (rows with 8+ points, Charron 2013 style).
    """
    df = pd.DataFrame(
        {
            "year": frame["year"].to_numpy(),
            "round": frame["round"].astype(str).to_numpy(),
            "vote_type": frame["vote_type"].astype(str).to_numpy()
            if "vote_type" in frame
            else "unknown",
            "voter": frame["voter"].astype(str).to_numpy(),
            "receiver": frame["receiver"].astype(str).to_numpy(),
            "points": frame["points"].astype(float).to_numpy(),
        }
    )
    df["resid"] = df["points"] - leave_one_out_mean(df, "points")
    df["is8"] = (df["points"] >= 8).astype(int)
    df = df.dropna(subset=["resid"])
    g = df.groupby(["voter", "receiver"], sort=True)
    return g.agg(
        estimate=("resid", "mean"),
        sd=("resid", "std"),
        n_obs=("resid", "size"),
        n_8plus=("is8", "sum"),
    ).reset_index()
