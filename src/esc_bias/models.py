"""Joint song-quality + dyad-bias models (primary estimators). **Fitting is stubbed.**

Why (plan review C1): the leave-one-out baseline is contaminated by the bias it measures
and treats bounded, ordinal, zero-inflated ballot points as interval data. The models
below estimate quality and bias *jointly*, separately per vote type.

What is implemented now: :func:`model_frame`, which selects exactly the rows every model
must use (anomaly register applied, one vote type). The two fitting functions document
the intended estimator and their return type so analysis code can be written against
them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

KEYS = ["year", "round", "vote_type", "voter", "receiver"]


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


def fit_crossed_effects(frame: pd.DataFrame, seed: int | None = None) -> DyadModelResult:
    """Crossed-effects quality + dyad model for one vote type. **Not implemented yet.**

    Intended estimator (``docs/04_study_design_v2.md`` §3)::

        y_{v,r,t,k} = mu + q_{r,t,k} + a_v + d_{v,r} + e

    where ``y`` is the ballot outcome (points, or rank-percentile as a robustness
    outcome), ``q`` the receiver x year x round quality (fixed or random), ``a_v`` a
    voter generosity/scale term, and ``d_{v,r} ~ N(0, sigma_d^2)`` the dyad effect with
    **partial pooling** (shrinkage toward 0 for dyads with few observations; plan review
    M2). First implementation: ``statsmodels`` ``MixedLM`` with variance components,
    or an alternating empirical-Bayes estimator if MixedLM is too slow for the crossed
    design. Report shrunken dyad estimates with intervals.
    """
    raise NotImplementedError("see docstring and docs/04_study_design_v2.md §3")


def fit_rank_ordered_logit(frame: pd.DataFrame, seed: int | None = None) -> DyadModelResult:
    """Rank-ordered logit (Plackett-Luce) robustness model. **Not implemented yet.**

    Intended: each ballot is a partial ranking of the performers (top-10 ordered, rest
    tied last). Worth of receiver ``r`` for voter ``v`` = ``exp(q_{r,t,k} + d_{v,r})``,
    with a ridge / Gaussian penalty on ``d`` for shrinkage. Fitted by maximum
    (penalised) likelihood with ``scipy.optimize``. Respects the ordinal, constrained
    nature of ballots that a linear model ignores (plan review C1).
    """
    raise NotImplementedError("see docstring and docs/04_study_design_v2.md §3")
