"""Reference baseline (proposal metric), checked against hand-computed values."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from esc_bias.baseline import add_baseline, ballot_rank_percentile, leave_one_out_mean, pair_summary


def toy() -> pd.DataFrame:
    """Three voters (A, B, C) rank three receivers (R, S, T) with 3-2-0 ballots.

    points        R  S  T
        A         3  2  0
        B         0  3  2
        C         2  0  3
    """
    pts = {
        "A": {"R": 3, "S": 2, "T": 0},
        "B": {"R": 0, "S": 3, "T": 2},
        "C": {"R": 2, "S": 0, "T": 3},
    }
    rows = [
        {
            "year": 2019,
            "round": "final",
            "vote_type": "jury",
            "voter": v,
            "receiver": r,
            "points": p,
        }
        for v, ballot in pts.items()
        for r, p in ballot.items()
    ]
    return pd.DataFrame(rows)


def test_loo_mean_and_excess_by_hand() -> None:
    out = add_baseline(toy()).set_index(["voter", "receiver"])
    # receiver R gets 3 (A), 0 (B), 2 (C)
    assert out.loc[("A", "R"), "loo_mean"] == pytest.approx((0 + 2) / 2)
    assert out.loc[("A", "R"), "excess"] == pytest.approx(3 - 1)
    assert out.loc[("B", "R"), "excess"] == pytest.approx(0 - 2.5)
    assert out.loc[("C", "R"), "excess"] == pytest.approx(2 - 1.5)


def test_rank_percentile_by_hand() -> None:
    out = add_baseline(toy()).set_index(["voter", "receiver"])
    # each ballot: top = 1.0, middle = 0.5, last = 0.0
    assert out.loc[("A", "R"), "rank_pct"] == 1.0
    assert out.loc[("A", "S"), "rank_pct"] == 0.5
    assert out.loc[("A", "T"), "rank_pct"] == 0.0
    # R: A=1.0, B=0.0, C=0.5 -> residual for A = 1.0 - mean(0.0, 0.5)
    assert out.loc[("A", "R"), "rank_pct_residual"] == pytest.approx(0.75)


def test_ties_get_average_rank() -> None:
    df = toy()
    df.loc[(df.voter == "A") & (df.receiver == "S"), "points"] = 0  # A: 3, 0, 0
    pct = ballot_rank_percentile(df)[df.voter == "A"].tolist()
    assert pct == [1.0, 0.25, 0.25]


def test_singleton_group_is_nan() -> None:
    df = pd.DataFrame({"g": ["x", "y", "y"], "v": [1.0, 2.0, 4.0]})
    loo = leave_one_out_mean(df, "v", ["g"])
    assert np.isnan(loo.iloc[0])
    assert loo.iloc[1:].tolist() == [4.0, 2.0]


def test_excess_sums_to_zero_per_receiver_scaled() -> None:
    out = add_baseline(toy())
    # sum_i (x_i - mean_{-i}) = n/(n-1) * sum_i (x_i - mean) = 0
    assert out.groupby("receiver")["excess"].sum().abs().max() == pytest.approx(0)


def test_pair_summary() -> None:
    df = pd.concat([toy(), toy().assign(year=2021)])
    s = pair_summary(add_baseline(df)).set_index(["voter", "receiver"])
    assert s.loc[("A", "R"), "n_obs"] == 2
    assert s.loc[("A", "R"), "n_years"] == 2
    assert s.loc[("A", "R"), "mean"] == pytest.approx(2.0)
