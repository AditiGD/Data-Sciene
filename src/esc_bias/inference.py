"""Permutation inference that respects the structure of voting data.

Dyads that share a voter or a receiver are not independent, so shuffling dyads as if
they were i.i.d. gives p-values that are too small (plan review M1). Two nulls are used:

* **QAP** (quadratic assignment procedure): permute the *node labels* of one matrix,
  i.e. rows and columns together, which keeps each matrix's row/column dependence.
* **Ballot-constrained null**: reshuffle points *within* each ballot, which keeps the
  12/10/8...1 structure and the no-self-vote rule.

All functions take an explicit ``seed`` (or a ``numpy.random.Generator``) so results are
reproducible; report the seed and the number of permutations with every p-value.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

Alternative = Literal["two-sided", "greater", "less"]


def make_rng(seed: int | np.random.Generator | None) -> np.random.Generator:
    """Return a Generator; pass an int for reproducibility (``None`` = fresh entropy)."""
    return seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)


def permute_nodes(matrix: np.ndarray, perm: np.ndarray) -> np.ndarray:
    """Relabel the nodes of a square matrix: ``out[i, j] = matrix[perm[i], perm[j]]``."""
    return matrix[np.ix_(perm, perm)]


def random_node_permutations(
    n_nodes: int, n_perm: int, seed: int | np.random.Generator | None
) -> np.ndarray:
    """``(n_perm, n_nodes)`` array of node-label permutations from one seeded stream."""
    rng = make_rng(seed)
    return np.stack([rng.permutation(n_nodes) for _ in range(n_perm)])


def _offdiag_mask(n: int) -> np.ndarray:
    return ~np.eye(n, dtype=bool)


def matrix_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson correlation of the off-diagonal cells that are finite in both matrices."""
    mask = _offdiag_mask(x.shape[0]) & np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return float("nan")
    return float(np.corrcoef(x[mask], y[mask])[0, 1])


@dataclass(frozen=True)
class PermutationResult:
    """Observed statistic, permutation p-value and the null distribution."""

    statistic: float
    p_value: float
    n_perm: int
    seed: int | None
    alternative: str
    null: np.ndarray = field(repr=False)


def permutation_p_value(observed: float, null: np.ndarray, alternative: Alternative) -> float:
    """Add-one p-value ``(1 + #extreme) / (1 + n)``; never exactly 0."""
    null = null[np.isfinite(null)]
    if alternative == "greater":
        extreme = np.sum(null >= observed)
    elif alternative == "less":
        extreme = np.sum(null <= observed)
    else:
        extreme = np.sum(np.abs(null) >= abs(observed))
    return float((1 + extreme) / (1 + len(null)))


def qap_correlation(
    x: np.ndarray,
    y: np.ndarray,
    n_perm: int = 1000,
    seed: int | None = None,
    alternative: Alternative = "two-sided",
) -> PermutationResult:
    """QAP test of the correlation between two square dyad matrices on the same nodes.

    Uses: jury vs televote bias matrices (RQ3), bias B vs Bᵀ (reciprocity), bias vs a
    dyad covariate (shared border). The diagonal and non-finite cells are ignored.

    Args:
        x, y: ``(n, n)`` arrays with rows = voters, columns = receivers, same node order.
        n_perm: number of node-label permutations of ``y``.
        seed: integer seed (stored in the result).
        alternative: ``"two-sided"``, ``"greater"`` or ``"less"``.
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.shape != y.shape or x.ndim != 2 or x.shape[0] != x.shape[1]:
        raise ValueError(f"need two square matrices of equal shape, got {x.shape}, {y.shape}")
    observed = matrix_correlation(x, y)
    perms = random_node_permutations(x.shape[0], n_perm, seed)
    null = np.array([matrix_correlation(x, permute_nodes(y, p)) for p in perms])
    return PermutationResult(
        observed, permutation_p_value(observed, null, alternative), n_perm, seed, alternative, null
    )


def permute_within_ballots(
    votes: pd.DataFrame,
    seed: int | np.random.Generator | None,
    points_col: str = "points",
    ballot_keys: tuple[str, ...] = ("year", "round", "vote_type", "voter"),
) -> pd.DataFrame:
    """One draw of the simplest ballot-constrained null: shuffle points within each ballot.

    Each voter still awards 12, 10, 8...1 once and never to itself, but to receivers
    chosen uniformly at random. This null ignores song quality, so it is only a sanity
    baseline; the quality-aware null is :func:`ballot_null_from_quality_model`.
    """
    rng = make_rng(seed)
    out = votes.copy()
    shuffled = out[points_col].to_numpy().copy()
    for idx in out.groupby(list(ballot_keys)).indices.values():
        shuffled[idx] = rng.permutation(shuffled[idx])
    out[points_col] = shuffled
    return out


# ------------------------------------------------------------------- regression / refit
def _ols_t(
    y: np.ndarray, x: np.ndarray, w: np.ndarray | None
) -> tuple[np.ndarray, np.ndarray, float]:
    """(Weighted) OLS with intercept column already in ``x``: coefficients, t, R²."""
    if w is not None:
        sw = np.sqrt(w)
        y, x = y * sw, x * sw[:, None]
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ beta
    dof = max(len(y) - x.shape[1], 1)
    sigma2 = resid @ resid / dof
    xtx_inv = np.linalg.pinv(x.T @ x)
    se = np.sqrt(np.maximum(np.diag(xtx_inv) * sigma2, 0))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(se > 0, beta / se, np.nan)
    # R² about the (weighted) mean; in the weighted case column 0 is the scaled intercept
    c0 = x[:, 0]
    yc = y - c0 * (y @ c0) / (c0 @ c0) if w is not None else y - y.mean()
    r2 = float(1.0 - resid @ resid / (yc @ yc)) if yc @ yc > 0 else float("nan")
    return beta, t, r2


def mrqap(
    y: np.ndarray,
    xs: dict[str, np.ndarray],
    n_perm: int = 1000,
    seed: int | None = None,
    weights: np.ndarray | None = None,
) -> pd.DataFrame:
    """Multiple-regression QAP with Dekker double semi-partialling (Dekker et al. 2007).

    OLS (optionally weighted by ``weights``, e.g. precision) of the off-diagonal cells of
    ``y`` on the matrices in ``xs``, using cells finite in all inputs. For covariate k,
    X_k is regressed on the other covariates (with intercept); the residual matrix has its
    node labels permuted (rows and columns together) and replaces X_k in the regression of
    ``y``; the permutation p-value compares |t| with the observed |t| (add-one rule).

    Returns one row per covariate: ``coef``, ``t``, ``p_value``, ``r2``, ``n_perm``,
    ``seed``, ``n_cells``.
    """
    y = np.asarray(y, dtype=float)
    n = y.shape[0]
    names = list(xs)
    mats = [np.asarray(xs[k], dtype=float) for k in names]
    mask = _offdiag_mask(n) & np.isfinite(y)
    for m in mats:
        if m.shape != y.shape:
            raise ValueError("all matrices must be square with the same shape as y")
        mask &= np.isfinite(m)
    if weights is not None:
        weights = np.asarray(weights, dtype=float)
        mask &= np.isfinite(weights) & (weights > 0)
    w = weights[mask] if weights is not None else None
    yv = y[mask]
    cols = np.column_stack([np.ones(mask.sum())] + [m[mask] for m in mats])
    beta, t_obs, r2 = _ols_t(yv, cols, w)
    rng = make_rng(seed)
    perms = [rng.permutation(n) for _ in range(n_perm)]
    pvals = []
    for k in range(len(names)):
        others = np.delete(cols, k + 1, axis=1)
        sw = np.ones(len(yv)) if w is None else np.sqrt(w)
        g, *_ = np.linalg.lstsq(others * sw[:, None], cols[:, k + 1] * sw, rcond=None)
        resid_vec = cols[:, k + 1] - others @ g
        resid_mat = np.zeros((n, n))
        resid_mat[mask] = resid_vec
        null_t = np.empty(n_perm)
        for b, p in enumerate(perms):
            col = permute_nodes(resid_mat, p)[mask]
            x = np.column_stack([cols[:, 0], col, np.delete(others, 0, axis=1)])
            null_t[b] = _ols_t(yv, x, w)[1][1]
        pvals.append(permutation_p_value(float(t_obs[k + 1]), null_t, "two-sided"))
    return pd.DataFrame(
        {
            "coef": beta[1:],
            "t": t_obs[1:],
            "p_value": pvals,
            "r2": r2,
            "n_perm": n_perm,
            "seed": seed,
            "n_cells": int(mask.sum()),
        },
        index=pd.Index(names, name="covariate"),
    )


@dataclass(frozen=True)
class RefitResult:
    """Permutation-refit output: observed fit, null draws and p-values."""

    observed: pd.Series
    null: pd.DataFrame = field(repr=False)
    p_values: pd.Series
    joint_stat: float
    joint_null: np.ndarray = field(repr=False)
    joint_p: float
    n_perm: int
    seed: int | None


def permute_covariate_labels(covariates: pd.DataFrame, perm_map: dict[str, str]) -> pd.DataFrame:
    """Relabel countries in a (voter, receiver)-indexed table, same map for both levels."""
    idx = covariates.index
    new = pd.MultiIndex.from_arrays(
        [idx.get_level_values(0).map(perm_map), idx.get_level_values(1).map(perm_map)],
        names=idx.names,
    )
    out = covariates.copy()
    out.index = new
    return out.reindex(idx)


def permutation_refit(
    fit_fn: Callable[[pd.DataFrame], dict[str, float]],
    covariates: pd.DataFrame,
    n_perm: int = 1000,
    seed: int | None = None,
    block: Sequence[str] | None = None,
) -> RefitResult:
    """Permutation refit: shuffle country labels of the covariates, refit, collect nulls.

    ``covariates`` is indexed by (voter, receiver). Each draw applies one random relabeling
    of countries to both levels (so dyad structure is kept), then calls
    ``fit_fn(permuted) -> {coef_name: value}``. Per-coefficient two-sided add-one p-values
    and a joint block statistic, the sum of squared standardized coefficients
    (observed beta / null SD), over ``block`` (default all coefficients) are returned.
    """
    countries = sorted(
        set(covariates.index.get_level_values(0)) | set(covariates.index.get_level_values(1))
    )
    observed = pd.Series(fit_fn(covariates), dtype=float)
    rng = make_rng(seed)
    draws = []
    for _ in range(n_perm):
        shuffled = rng.permutation(len(countries))
        mapping = {c: countries[j] for c, j in zip(countries, shuffled, strict=True)}
        draws.append(fit_fn(permute_covariate_labels(covariates, mapping)))
    null = pd.DataFrame(draws, columns=observed.index).astype(float)
    p = pd.Series(
        {
            k: permutation_p_value(observed[k], null[k].to_numpy(), "two-sided")
            for k in observed.index
        }
    )
    cols = list(block) if block is not None else list(observed.index)
    sd = null[cols].std(ddof=1).replace(0, np.nan)
    joint_null = ((null[cols] / sd) ** 2).sum(axis=1).to_numpy()
    joint = float(((observed[cols] / sd) ** 2).sum())
    return RefitResult(
        observed,
        null,
        p,
        joint,
        joint_null,
        permutation_p_value(joint, joint_null, "greater"),
        n_perm,
        seed,
    )


def reliability_corrected_r(r: float, rel_a: float, rel_b: float) -> float:
    """Spearman disattenuation: ``r / sqrt(rel_a * rel_b)`` (can exceed 1 when noisy)."""
    if rel_a <= 0 or rel_b <= 0:
        raise ValueError("reliabilities must be positive")
    return float(r / np.sqrt(rel_a * rel_b))


def lfsr_from_draws(draws: np.ndarray) -> np.ndarray:
    """Local false sign rate per column: ``min(P(theta <= 0), P(theta >= 0))`` over axis 0."""
    d = np.asarray(draws, dtype=float)
    return np.minimum((d <= 0).mean(axis=0), (d >= 0).mean(axis=0))


def ballot_null_from_quality_model(
    votes: pd.DataFrame,
    quality: pd.DataFrame,
    n_draws: int,
    seed: int | None = None,
) -> pd.DataFrame:
    """Quality-aware ballot-constrained null.

    Provided by ``models.parametric_bootstrap`` (needs the fitted model); this stub
    only documents the design.

    Intended: for each draw and each ballot, sample a full ranking of the performers
    (excluding the voter) from a Plackett-Luce model whose worths are the fitted
    receiver x year x vote-type quality effects (no dyad effects), then map ranks to
    12, 10, 8...1, 0. Statistics recomputed on each simulated table form the null for
    group-level hypotheses (e.g. "within-region excess > 0").
    """
    raise NotImplementedError("see docstring and docs/04_study_design_v2.md §4")
