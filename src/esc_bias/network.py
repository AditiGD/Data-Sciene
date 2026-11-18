"""Directed, signed bias network and its statistically grounded backbone.

Nodes are countries; an edge ``voter -> receiver`` carries the estimated dyad bias
(positive = more points than quality predicts, negative = fewer).
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from typing import Any

import igraph as ig  # type: ignore[import-untyped]
import leidenalg as la  # type: ignore[import-untyped]
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
        g.add_edge(u, v, weight=float(w), sign=int(np.sign(w)), **{str(c): rec[c] for c in extra})
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


def _positive_igraph(g: nx.DiGraph, nodes: list) -> ig.Graph:
    idx = {n: i for i, n in enumerate(nodes)}
    edges, w = [], []
    for u, v, d in g.edges(data=True):
        if d.get("weight", 0) > 0 and u != v:
            edges.append((idx[u], idx[v]))
            w.append(float(d["weight"]))
    h = ig.Graph(n=len(nodes), edges=edges, directed=True)
    h.es["weight"] = w
    return h


def _leiden(h: ig.Graph, resolution: float, seed: int) -> list[int]:
    part = la.find_partition(
        h,
        la.RBConfigurationVertexPartition,
        weights="weight" if h.ecount() else None,
        resolution_parameter=resolution,
        seed=seed,
    )
    return list(part.membership)


def _modularity(h: ig.Graph, membership: Sequence[int], resolution: float = 1.0) -> float:
    if h.ecount() == 0:
        return 0.0
    return float(
        la.RBConfigurationVertexPartition(
            h,
            weights="weight",
            initial_membership=list(membership),
            resolution_parameter=resolution,
        ).quality()
        / sum(h.es["weight"])
    )


def adjusted_rand_index(a: Any, b: Any) -> float:
    """Adjusted Rand index of two labelings of the same items."""
    a_codes = np.asarray(pd.factorize(pd.Series(list(a)))[0], dtype=int)
    b_codes = np.asarray(pd.factorize(pd.Series(list(b)))[0], dtype=int)
    table = np.zeros((int(a_codes.max()) + 1, int(b_codes.max()) + 1))
    np.add.at(table, (a_codes, b_codes), 1)
    comb = lambda x: x * (x - 1) / 2  # noqa: E731
    sum_cells = comb(table).sum()
    sum_a, sum_b = comb(table.sum(1)).sum(), comb(table.sum(0)).sum()
    total = comb(float(len(a_codes)))
    expected = sum_a * sum_b / total if total else 0.0
    denom = (sum_a + sum_b) / 2 - expected
    return float((sum_cells - expected) / denom) if denom != 0 else 1.0


def normalized_mutual_info(a: Any, b: Any) -> float:
    """NMI (arithmetic-mean normalisation) of two labelings."""
    a_codes = np.asarray(pd.factorize(pd.Series(list(a)))[0], dtype=int)
    b_codes = np.asarray(pd.factorize(pd.Series(list(b)))[0], dtype=int)
    n = len(a_codes)
    joint = np.zeros((int(a_codes.max()) + 1, int(b_codes.max()) + 1))
    np.add.at(joint, (a_codes, b_codes), 1)
    joint /= n
    pa, pb = joint.sum(1), joint.sum(0)
    nz = joint > 0
    mi = float((joint[nz] * np.log(joint[nz] / np.outer(pa, pb)[nz])).sum())
    ha = -float((pa[pa > 0] * np.log(pa[pa > 0])).sum())
    hb = -float((pb[pb > 0] * np.log(pb[pb > 0])).sum())
    return 1.0 if ha + hb == 0 else float(2 * mi / (ha + hb))


def detect_communities(
    g: nx.DiGraph,
    resolution: float = 1.0,
    n_seeds: int = 50,
    seed: int = 0,
) -> dict[str, Any]:
    """Consensus Leiden communities on the positive part of ``g`` (design §7.3).

    Runs Leiden (``RBConfigurationVertexPartition``, directed, weighted) at a fixed
    ``resolution`` for ``n_seeds`` seeds, builds the node co-assignment matrix, and takes
    the consensus partition by Leiden on that (undirected, weighted) matrix.

    Returns dict with ``partition`` (node -> label, labels sorted by size), ``modularity``
    of the consensus on the positive graph, ``mean_pairwise_ARI`` across seed partitions,
    ``coassignment`` (DataFrame) and ``nodes``.
    """
    nodes = list(g.nodes())
    h = _positive_igraph(g, nodes)
    n = len(nodes)
    parts = [np.array(_leiden(h, resolution, seed + s)) for s in range(n_seeds)]
    co = np.mean([(p[:, None] == p[None, :]) for p in parts], axis=0)
    aris = [
        adjusted_rand_index(parts[i], parts[j])
        for i, j in itertools.combinations(range(n_seeds), 2)
    ]
    c = ig.Graph.Weighted_Adjacency(co.tolist(), mode="undirected", attr="weight", loops=False)
    consensus = _leiden(c, 1.0, seed) if n > 1 and c.ecount() else list(range(n))
    order = {lab: r for r, (lab, _) in enumerate(pd.Series(consensus).value_counts().items())}
    membership = [order[x] for x in consensus]
    return {
        "partition": dict(zip(nodes, membership, strict=True)),
        "modularity": _modularity(h, membership, resolution),
        "mean_pairwise_ARI": float(np.mean(aris)) if aris else 1.0,
        "coassignment": pd.DataFrame(co, index=nodes, columns=nodes),
        "nodes": nodes,
    }


def strength_preserving_null(
    g: nx.DiGraph, n: int = 100, seed: int = 0, resolution: float = 1.0, n_seeds: int = 1
) -> np.ndarray:
    """Modularity null from strength-preserving rewiring of W⁺ (design §7.3, null 2).

    Maslov-Sneppen swaps on directed positive edges: pick edges u->v and x->y and make
    them u->y, x->v, keeping the weights attached to their edges. In- and out-*degree* are
    preserved exactly; strengths only approximately. Each replicate is partitioned with
    Leiden (best of ``n_seeds``) and its modularity recorded. Returns an array of length n.
    """
    nodes = list(g.nodes())
    base = _positive_igraph(g, nodes)
    src = np.array([e.source for e in base.es])
    dst = np.array([e.target for e in base.es])
    w = np.array(base.es["weight"]) if base.ecount() else np.array([])
    rng = np.random.default_rng(seed)
    m = len(src)
    out = np.empty(n)
    for r in range(n):
        s, d = src.copy(), dst.copy()
        existing = set(zip(s.tolist(), d.tolist(), strict=True))
        for _ in range(10 * m):
            if m < 2:
                break
            i, j = rng.integers(m, size=2)
            if i == j or s[i] == s[j] or d[i] == d[j]:
                continue
            a, b = (s[i], d[j]), (s[j], d[i])
            if a[0] == a[1] or b[0] == b[1] or a in existing or b in existing:
                continue
            existing -= {(s[i], d[i]), (s[j], d[j])}
            existing |= {a, b}
            d[i], d[j] = d[j], d[i]
        h = ig.Graph(
            n=len(nodes), edges=list(zip(s.tolist(), d.tolist(), strict=True)), directed=True
        )
        h.es["weight"] = w.tolist()
        out[r] = max(
            _modularity(h, _leiden(h, resolution, int(rng.integers(2**31))), resolution)
            for _ in range(n_seeds)
        )
    return out


def nmi_permutation_test(
    partition: Mapping[str, int] | Sequence,
    labels: Mapping[str, str] | Sequence,
    n_perm: int = 1000,
    seed: int | None = 0,
) -> dict[str, Any]:
    """NMI between a partition and external labels (e.g. UN-M49) with a label-permutation p.

    Mappings are aligned on their common keys; sequences must have equal length.
    """
    if isinstance(partition, Mapping) and isinstance(labels, Mapping):
        keys = [k for k in partition if k in labels]
        a = [partition[k] for k in keys]
        b = [labels[k] for k in keys]
    else:
        a, b = list(partition), list(labels)  # type: ignore[arg-type]
    obs = normalized_mutual_info(a, b)
    rng = np.random.default_rng(seed)
    barr = np.array(b, dtype=object)
    null = np.array([normalized_mutual_info(a, rng.permutation(barr)) for _ in range(n_perm)])
    p = float((1 + np.sum(null >= obs)) / (1 + n_perm))
    return {"nmi": obs, "p_value": p, "null": null, "n_perm": n_perm, "seed": seed}


def concentration_table(
    W: pd.DataFrame | np.ndarray, nodes: Sequence[str] | None = None
) -> pd.DataFrame:
    """Concentration of excess points per country (design §7.4).

    Because b is centred, strengths of W⁺ measure how *concentrated* a country's positive
    affinities are, not how much favouritism it gives or receives. Columns:
    ``out_strength_pos`` (row sums of W⁺), ``in_strength_pos`` (column sums of W⁺),
    ``row_sd`` and ``col_sd`` (SD of the signed row/column, NaN ignored, diagonal excluded).
    """
    if isinstance(W, pd.DataFrame):
        names, arr = list(W.index), W.to_numpy(dtype=float).copy()
    else:
        arr = np.asarray(W, dtype=float).copy()
        names = list(nodes) if nodes is not None else list(range(arr.shape[0]))
    np.fill_diagonal(arr, np.nan)
    pos = np.where(np.isfinite(arr) & (arr > 0), arr, 0.0)
    return pd.DataFrame(
        {
            "out_strength_pos": pos.sum(1),
            "in_strength_pos": pos.sum(0),
            "row_sd": np.nanstd(arr, axis=1, ddof=1),
            "col_sd": np.nanstd(arr, axis=0, ddof=1),
        },
        index=pd.Index(names, name="country"),
    )


def backbone_credible(
    dyad_table: pd.DataFrame,
    lfsr_max: float = 0.05,
    delta_min: float = 2.0,
    lfsr_col: str = "lfsr",
    delta_col: str = "delta",
    voter_col: str = "voter",
    receiver_col: str = "receiver",
) -> nx.DiGraph:
    """Backbone of credibly positive edges: ``lfsr < lfsr_max`` and ``delta >= delta_min``.

    Edge weight is ``delta`` (points); other dyad columns are copied onto the edge.
    """
    keep = dyad_table[(dyad_table[lfsr_col] < lfsr_max) & (dyad_table[delta_col] >= delta_min)]
    keep = keep[keep[voter_col] != keep[receiver_col]]
    g = nx.DiGraph()
    g.add_nodes_from(sorted(set(dyad_table[voter_col]) | set(dyad_table[receiver_col])))
    for rec in keep.to_dict(orient="records"):
        attrs = {str(k): v for k, v in rec.items() if k not in {voter_col, receiver_col}}
        g.add_edge(rec[voter_col], rec[receiver_col], weight=float(rec[delta_col]), **attrs)
    return g
