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


# --------------------------------------------------------------------------- stubs
def mrqap(
    y: np.ndarray,
    xs: dict[str, np.ndarray],
    n_perm: int = 1000,
    seed: int | None = None,
) -> pd.DataFrame:
    """Multiple-regression QAP (Dekker, Krackhardt & Snijders 2007). **Not implemented yet.**

    Intended estimator: OLS of the off-diagonal cells of ``y`` (e.g. estimated dyad bias)
    on the covariate matrices in ``xs`` (contiguity, distance, shared language, migrant
    stock), with p-values from *double semi-partialling* (permute the residuals of each
    covariate regressed on the others), seeded via ``seed``.

    Returns (planned): one row per covariate with ``coef``, ``t``, ``p_value``,
    ``n_perm``, ``seed``.
    """
    raise NotImplementedError("MRQAP: see docstring and docs/04_study_design_v2.md §4")


def ballot_null_from_quality_model(
    votes: pd.DataFrame,
    quality: pd.DataFrame,
    n_draws: int,
    seed: int | None = None,
) -> pd.DataFrame:
    """Quality-aware ballot-constrained null. **Not implemented yet.**

    Intended: for each draw and each ballot, sample a full ranking of the performers
    (excluding the voter) from a Plackett-Luce model whose worths are the fitted
    receiver x year x vote-type quality effects (no dyad effects), then map ranks to
    12, 10, 8...1, 0. Statistics recomputed on each simulated table form the null for
    group-level hypotheses (e.g. "within-region excess > 0").
    """
    raise NotImplementedError("see docstring and docs/04_study_design_v2.md §4")
