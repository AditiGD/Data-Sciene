"""The proposal's original metric, kept as a transparent *reference* implementation.

For every row of the tidy table (one voter -> receiver pair in one year, round and vote
type)::

    loo_mean = mean points the receiver got from all *other* voters in that
               (year, round, vote_type)
    excess   = points - loo_mean

Known limitation (plan review C1): if a bloc over-votes a receiver, the other bloc members
inflate ``loo_mean`` and shrink each member's ``excess`` toward zero. The joint quality +
dyad model in :mod:`esc_bias.models` is the primary estimator; this baseline is the
benchmark it is compared with.

The rank-percentile variant replaces points by the receiver's percentile *within the
voter's ballot* (0 = ranked last, 1 = ranked first), which removes the non-linear
12/10/8 spacing of the points scale.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

RECEIVER_KEYS: list[str] = ["year", "round", "vote_type", "receiver"]
BALLOT_KEYS: list[str] = ["year", "round", "vote_type", "voter"]


def leave_one_out_mean(
    df: pd.DataFrame, value_col: str, group_cols: Sequence[str] = RECEIVER_KEYS
) -> pd.Series:
    """Mean of ``value_col`` over the *other* rows of each group (NaN for singletons)."""
    grouped = df.groupby(list(group_cols))[value_col]
    total = grouped.transform("sum")
    n = grouped.transform("count")
    loo = (total - df[value_col]) / (n - 1)
    return loo.where(n > 1)


def ballot_rank_percentile(df: pd.DataFrame, points_col: str = "points") -> pd.Series:
    """Percentile of each receiver within its voter's ballot.

    Ties (the many zeros) get the average rank. ``(rank - 1) / (n - 1)`` maps the
    ballot's lowest value to 0 and the 12-point song to 1.
    """
    grouped = df.groupby(BALLOT_KEYS)[points_col]
    rank = grouped.rank(method="average")
    n = grouped.transform("count")
    return ((rank - 1) / (n - 1)).where(n > 1)


def add_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the tidy table with the reference baseline columns added.

    Added columns: ``loo_mean``, ``excess``, ``rank_pct``, ``loo_rank_pct``,
    ``rank_pct_residual``. Filter the table (e.g. drop ``exclude`` rows, pick vote
    types) *before* calling this: the leave-one-out mean uses whatever rows it is given.
    """
    out = df.copy()
    out["loo_mean"] = leave_one_out_mean(out, "points")
    out["excess"] = out["points"] - out["loo_mean"]
    out["rank_pct"] = ballot_rank_percentile(out)
    out["loo_rank_pct"] = leave_one_out_mean(out, "rank_pct")
    out["rank_pct_residual"] = out["rank_pct"] - out["loo_rank_pct"]
    return out


def pair_summary(
    df: pd.DataFrame,
    value_col: str = "excess",
    by: Sequence[str] = ("vote_type", "voter", "receiver"),
) -> pd.DataFrame:
    """Aggregate a per-row metric to the dyad level.

    Returns mean, standard deviation, number of observations and number of distinct
    years per dyad. Ranking dyads by ``mean`` alone suffers from the winner's curse
    (plan review M2): always show ``n_obs`` next to it and prefer shrunken estimates.
    """
    g = df.groupby(list(by))
    return (
        g[value_col]
        .agg(mean="mean", sd="std", n_obs="count")
        .join(g["year"].nunique().rename("n_years"))
        .reset_index()
    )
