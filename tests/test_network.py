"""Bias graph and disparity-filter backbone."""

from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from esc_bias.network import (
    adjusted_rand_index,
    backbone_credible,
    build_bias_graph,
    concentration_table,
    detect_communities,
    disparity_filter,
    dyads_to_matrix,
    nmi_permutation_test,
    positive_part,
    strength_preserving_null,
)


def star() -> nx.DiGraph:
    """A sends one strong edge (10) and four weak ones (1); F -> B adds a 2nd in-edge to B."""
    g = nx.DiGraph()
    g.add_edge("A", "B", weight=10.0)
    for t in "CDEF":
        g.add_edge("A", t, weight=1.0)
    g.add_edge("F", "B", weight=1.0)
    return g


def test_disparity_filter_keeps_only_dominant_edge() -> None:
    bb = disparity_filter(star(), alpha=0.05)
    assert set(bb.edges()) == {("A", "B")}
    # alpha_out = (1 - 10/14)^(5-1)
    assert bb.edges["A", "B"]["alpha_out"] == pytest.approx((4 / 14) ** 4)
    assert set(bb.nodes()) == set(star().nodes())  # nodes are never dropped


def test_disparity_filter_alpha_one_keeps_multi_edge_nodes() -> None:
    bb = disparity_filter(star(), alpha=1.0)
    # every edge whose source or target has degree > 1 has alpha < 1
    assert ("A", "C") in bb.edges()


def test_disparity_filter_rejects_negative_weights() -> None:
    g = star()
    g.add_edge("C", "D", weight=-1.0)
    with pytest.raises(ValueError, match="positive_part"):
        disparity_filter(g)
    assert ("C", "D") not in positive_part(g).edges()


def test_build_bias_graph_signs_and_skips() -> None:
    dyads = pd.DataFrame(
        {
            "voter": ["A", "A", "B", "C", "C"],
            "receiver": ["B", "C", "A", "C", "A"],
            "bias": [1.5, -0.5, np.nan, 2.0, 0.0],
            "n_obs": [9, 8, 7, 6, 5],
        }
    )
    g = build_bias_graph(dyads)
    assert set(g.edges()) == {("A", "B"), ("A", "C")}  # NaN, self-loop and zero skipped
    assert g.edges["A", "C"]["sign"] == -1
    assert g.edges["A", "B"]["n_obs"] == 9


def test_dyads_to_matrix() -> None:
    dyads = pd.DataFrame({"voter": ["A", "B"], "receiver": ["B", "A"], "bias": [1.0, 2.0]})
    m, nodes = dyads_to_matrix(dyads, "bias", nodes=["A", "B", "C"])
    assert nodes == ["A", "B", "C"]
    assert m[0, 1] == 1.0 and m[1, 0] == 2.0
    assert np.isnan(m[0, 0]) and np.isnan(m[2, 0])


def planted_graph(seed: int = 0) -> tuple[nx.DiGraph, dict[str, int]]:
    rng = np.random.default_rng(seed)
    names = [f"n{i}" for i in range(12)]
    truth = {n: int(i >= 6) for i, n in enumerate(names)}
    g = nx.DiGraph()
    g.add_nodes_from(names)
    for u in names:
        for v in names:
            if u != v and rng.random() < (0.8 if truth[u] == truth[v] else 0.05):
                g.add_edge(u, v, weight=float(rng.uniform(1, 3)))
    return g, truth


def test_detect_communities_planted() -> None:
    g, truth = planted_graph()
    res = detect_communities(g, n_seeds=10, seed=1)
    assert len(set(res["partition"].values())) == 2
    assert adjusted_rand_index(list(res["partition"].values()), list(truth.values())) > 0.9
    assert res["mean_pairwise_ARI"] > 0.9 and res["modularity"] > 0.3
    assert res["coassignment"].shape == (12, 12)
    null = strength_preserving_null(g, n=10, seed=0)
    assert null.shape == (10,) and null.mean() < res["modularity"]
    t = nmi_permutation_test(res["partition"], truth, n_perm=200, seed=0)
    assert t["nmi"] > 0.9 and t["p_value"] < 0.05


def test_concentration_and_backbone() -> None:
    w = np.array([[0.0, 2.0, -1.0], [1.0, 0.0, 3.0], [-2.0, 0.5, 0.0]])
    tab = concentration_table(w, ["a", "b", "c"])
    assert tab.loc["a", "out_strength_pos"] == 2.0 and tab.loc["b", "in_strength_pos"] == 2.5
    assert tab.loc["a", "row_sd"] == pytest.approx(np.std([2.0, -1.0], ddof=1))
    d = pd.DataFrame(
        {
            "voter": ["a", "a", "b"],
            "receiver": ["b", "c", "c"],
            "delta": [3.0, 1.0, 5.0],
            "lfsr": [0.01, 0.01, 0.2],
        }
    )
    assert set(backbone_credible(d).edges()) == {("a", "b")}
