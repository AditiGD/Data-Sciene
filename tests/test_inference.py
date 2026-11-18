"""QAP and permutation helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from esc_bias.inference import (
    lfsr_from_draws,
    matrix_correlation,
    mrqap,
    permutation_p_value,
    permutation_refit,
    permute_nodes,
    permute_within_ballots,
    qap_correlation,
    random_node_permutations,
    reliability_corrected_r,
)


def random_matrix(n: int, seed: int) -> np.ndarray:
    m = np.random.default_rng(seed).normal(size=(n, n))
    np.fill_diagonal(m, np.nan)
    return m


def test_qap_detects_correlated_matrices() -> None:
    x = random_matrix(15, 0)
    y = x + 0.3 * random_matrix(15, 1)
    res = qap_correlation(x, y, n_perm=499, seed=42)
    assert res.statistic > 0.9
    assert res.p_value == pytest.approx(1 / 500)  # nothing in the null is as extreme


def test_qap_random_matrices_not_significant() -> None:
    res = qap_correlation(random_matrix(15, 2), random_matrix(15, 3), n_perm=499, seed=42)
    assert abs(res.statistic) < 0.2
    assert res.p_value > 0.05


def test_qap_is_seed_reproducible() -> None:
    x, y = random_matrix(10, 4), random_matrix(10, 5)
    a = qap_correlation(x, y, n_perm=200, seed=7)
    b = qap_correlation(x, y, n_perm=200, seed=7)
    c = qap_correlation(x, y, n_perm=200, seed=8)
    np.testing.assert_array_equal(a.null, b.null)
    assert a.p_value == b.p_value
    assert not np.array_equal(a.null, c.null)


def test_qap_rejects_bad_shapes() -> None:
    with pytest.raises(ValueError):
        qap_correlation(np.zeros((3, 3)), np.zeros((3, 4)))


def test_permute_nodes_relabels_rows_and_columns_together() -> None:
    m = np.arange(9.0).reshape(3, 3)
    perm = np.array([2, 0, 1])
    out = permute_nodes(m, perm)
    assert out[0, 1] == m[2, 0]
    assert sorted(np.diag(out)) == sorted(np.diag(m))  # diagonal stays on the diagonal


def test_random_node_permutations_shape_and_validity() -> None:
    perms = random_node_permutations(6, 5, seed=1)
    assert perms.shape == (5, 6)
    assert all(sorted(p) == list(range(6)) for p in perms)


def test_matrix_correlation_ignores_nan_and_diagonal() -> None:
    x = random_matrix(5, 9)
    y = x.copy()
    y[0, 1] = np.nan
    assert matrix_correlation(x, y) == pytest.approx(1.0)


def test_p_value_alternatives() -> None:
    null = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    assert permutation_p_value(1.5, null, "greater") == pytest.approx(2 / 6)
    assert permutation_p_value(1.5, null, "less") == pytest.approx(5 / 6)
    assert permutation_p_value(1.5, null, "two-sided") == pytest.approx(3 / 6)


def test_permute_within_ballots_preserves_ballots() -> None:
    votes = pd.DataFrame(
        {
            "year": 2019,
            "round": "final",
            "vote_type": "jury",
            "voter": ["A"] * 4 + ["B"] * 4,
            "receiver": list("BCDE") + list("ACDE"),
            "points": [3, 2, 1, 0, 0, 1, 2, 3],
        }
    )
    a = permute_within_ballots(votes, seed=3)
    b = permute_within_ballots(votes, seed=3)
    pd.testing.assert_frame_equal(a, b)
    for _, g in a.groupby("voter"):
        assert sorted(g.points) == [0, 1, 2, 3]
    assert (a.voter != a.receiver).all()


def test_mrqap_recovers_planted_and_null() -> None:
    rng = np.random.default_rng(1)
    n = 25
    x1, x2 = rng.normal(size=(n, n)), rng.normal(size=(n, n))
    y = 2.0 * x1 + rng.normal(size=(n, n))
    res = mrqap(y, {"x1": x1, "x2": x2}, n_perm=200, seed=3)
    assert abs(res.loc["x1", "coef"] - 2.0) < 0.3
    assert res.loc["x1", "p_value"] < 0.02
    assert res.loc["x2", "p_value"] > 0.1
    assert 0.5 < res.loc["x1", "r2"] < 1
    w = mrqap(y, {"x1": x1}, n_perm=20, seed=3, weights=np.ones((n, n)))
    assert abs(w.loc["x1", "coef"] - 2.0) < 0.3


def test_permutation_refit_trivial_fit() -> None:
    countries = list("ABCDEFGH")
    idx = pd.MultiIndex.from_product([countries, countries], names=["voter", "receiver"])
    idx = idx[idx.get_level_values(0) != idx.get_level_values(1)]
    cov = pd.DataFrame({"x": np.arange(len(idx), dtype=float)}, index=idx)

    def fit(c: pd.DataFrame) -> dict[str, float]:
        return {"ab": float(c.loc[("A", "B"), "x"])}

    res = permutation_refit(fit, cov, n_perm=50, seed=0)
    assert res.null.shape == (50, 1)
    assert 0 < res.p_values["ab"] <= 1 and 0 < res.joint_p <= 1
    again = permutation_refit(fit, cov, n_perm=50, seed=0)
    assert np.allclose(res.null["ab"], again.null["ab"])
    const = permutation_refit(lambda c: {"s": float(c["x"].sum())}, cov, n_perm=5, seed=1)
    assert const.p_values["s"] == 1.0


def test_reliability_and_lfsr() -> None:
    assert reliability_corrected_r(0.4, 0.8, 0.5) == pytest.approx(0.4 / np.sqrt(0.4))
    draws = np.column_stack([np.full(100, 1.0), np.r_[np.ones(60), -np.ones(40)]])
    assert lfsr_from_draws(draws) == pytest.approx([0.0, 0.4])
