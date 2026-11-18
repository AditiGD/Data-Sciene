"""Directed, signed bias network and its statistically grounded backbone.

Nodes are countries; an edge ``voter -> receiver`` carries the estimated dyad bias
(positive = more points than quality predicts, negative = fewer).
"""

from __future__ import annotations

from collections.abc import Sequence

import networkx as nx
import numpy as np
import pandas as pd


def dyads_to_matrix(
    dyads: pd.DataFrame,
    value_col: str,
    voter_col: str = "voter",
    receiver_col: str = "receiver",
    nodes: Sequence[str] | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Pivot a dyad table to a square ``(voter x receiver)`` matrix.

    Rows and columns share one node order (sorted union unless ``nodes`` is given);
    missing dyads and the diagonal are NaN. Input for :func:`esc_bias.inference.qap_correlation`.
    """
    order = (
        list(nodes)
        if nodes is not None
        else sorted(set(dyads[voter_col]) | set(dyads[receiver_col]))
    )
    wide = dyads.pivot_table(
        index=voter_col, columns=receiver_col, values=value_col, aggfunc="mean"
    )
    mat = wide.reindex(index=order, columns=order).to_numpy(dtype=float, copy=True)
    np.fill_diagonal(mat, np.nan)
    return mat, order


def build_bias_graph(
    dyads: pd.DataFrame,
    weight_col: str = "bias",
    voter_col: str = "voter",
    receiver_col: str = "receiver",
) -> nx.DiGraph:
    """Directed signed graph; edge attributes ``weight`` (signed) and ``sign`` (+1/-1).

    Rows with a missing or zero weight and self-loops are skipped. Other columns of
    ``dyads`` (e.g. ``n_obs``, interval bounds) are copied onto the edge.
    """
    g = nx.DiGraph()
    g.add_nodes_from(sorted(set(dyads[voter_col]) | set(dyads[receiver_col])))
    extra = [c for c in dyads.columns if c not in {voter_col, receiver_col, weight_col}]
    for rec in dyads.to_dict(orient="records"):
        u, v, w = rec[voter_col], rec[receiver_col], rec[weight_col]
        if u == v or pd.isna(w) or w == 0:
            continue
        g.add_edge(u, v, weight=float(w), sign=int(np.sign(w)), **{c: rec[c] for c in extra})
    return g


def positive_part(g: nx.DiGraph, weight: str = "weight") -> nx.DiGraph:
    """Subgraph of strictly positive edges (most backbone/community methods need w > 0)."""
    h = nx.DiGraph()
    h.add_nodes_from(g.nodes(data=True))
    h.add_edges_from((u, v, d) for u, v, d in g.edges(data=True) if d[weight] > 0)
    return h


def _disparity_alpha(w: float, strength: float, degree: int) -> float:
    """Serrano et al. (2009) p-value of one edge at one endpoint: ``(1 - w/s)^(k-1)``.

    A node with a single edge gives no evidence (alpha = 1).
    """
    if degree <= 1 or strength <= 0:
        return 1.0
    return float((1.0 - w / strength) ** (degree - 1))


def disparity_filter(g: nx.DiGraph, alpha: float = 0.05, weight: str = "weight") -> nx.DiGraph:
    """Disparity-filter backbone of a directed, positively weighted graph.

    For each edge ``u -> v`` two p-values are computed: against ``u``'s outgoing edges
    (``alpha_out``) and against ``v``'s incoming edges (``alpha_in``). The edge is kept
    if either is below ``alpha`` (Serrano, Boguñá & Vespignani 2009, directed variant).
    Kept edges carry both p-values as attributes.

    Raises:
        ValueError: if any weight is negative (apply :func:`positive_part` first).
    """
    if any(d[weight] < 0 for _, _, d in g.edges(data=True)):
        raise ValueError("disparity_filter needs non-negative weights; use positive_part()")
    out_s = dict(g.out_degree(weight=weight))
    in_s = dict(g.in_degree(weight=weight))
    out_k, in_k = dict(g.out_degree()), dict(g.in_degree())
    backbone = nx.DiGraph()
    backbone.add_nodes_from(g.nodes(data=True))
    for u, v, d in g.edges(data=True):
        a_out = _disparity_alpha(d[weight], out_s[u], out_k[u])
        a_in = _disparity_alpha(d[weight], in_s[v], in_k[v])
        if min(a_out, a_in) < alpha:
            backbone.add_edge(u, v, **d, alpha_out=a_out, alpha_in=a_in)
    return backbone


def detect_communities(
    g: nx.DiGraph,
    resolutions: Sequence[float] = (0.5, 1.0, 1.5),
    seeds: Sequence[int] = tuple(range(100)),
) -> pd.DataFrame:
    """Consensus community detection on the bias network. **Not implemented yet.**

    Intended (plan review M5): on the positive part (or a signed variant), run Louvain /
    Leiden for every (resolution, seed), build a co-assignment consensus matrix, cluster
    it, and compare modularity with a configuration-model or ballot-permutation null.

    Returns (planned): columns ``node, community, resolution, consensus_share``.
    """
    raise NotImplementedError("see docstring and docs/04_study_design_v2.md §7")
