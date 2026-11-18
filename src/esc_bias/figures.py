"""Build every report figure whose input CSVs exist (contract: see docs §8)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from esc_bias.viz import (
    DIVERGING,
    INK,
    VOTE_TYPE_COLORS,
    save_figure,
    set_style,
    symmetric_limits,
)

log = logging.getLogger(__name__)

PERIODS = ("2016-2019", "2021-2023", "2024-2025")
FORMATS = ("png", "svg")
ATTRIBUTES = Path("audit/reference_tables/country_attributes.csv")
COMMUNITY_COLORS = [
    "#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9",
    "#D55E00", "#F0E442", "#999999",
]  # fmt: skip
Frames = dict[str, pd.DataFrame]


def _read(results_dir: Path, name: str) -> pd.DataFrame | None:
    path = results_dir / name
    return pd.read_csv(path) if path.exists() else None


def _save(fig: plt.Figure, name: str, out_dir: Path) -> list[Path]:
    return save_figure(fig, name, out_dir, formats=FORMATS)


# --------------------------------------------------------------------- F1
def community_order(
    dyads: pd.DataFrame, communities: pd.DataFrame | None
) -> tuple[list[str], list[str]]:
    """Row (voters) and column (receivers) order: community, then mean affinity."""
    comm = (
        dict(zip(communities["country"], communities["community"], strict=False))
        if (communities is not None)
        else {}
    )

    def order(side: str, other: str) -> list[str]:
        mean = dyads.groupby(side)["delta"].mean()
        key = sorted(mean.index, key=lambda c: (comm.get(c, 10**6), -mean[c], c))
        return [str(c) for c in key]

    return order("voter", "receiver"), order("receiver", "voter")


def fig_heatmap(
    jury: pd.DataFrame,
    televote: pd.DataFrame,
    communities: pd.DataFrame | None,
    out_dir: Path,
) -> list[Path]:
    """F1: seriated voter x receiver affinity heatmaps, hatched where n_obs < 3."""
    set_style()
    both = pd.concat([jury, televote])
    rows, cols = community_order(both, communities)
    vmin, vmax = symmetric_limits(both["delta"])
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), sharey=True)
    im = None
    for ax, df, title in zip(axes, (jury, televote), ("Jury", "Televote"), strict=True):
        d = df.pivot_table(index="voter", columns="receiver", values="delta")
        n = df.pivot_table(index="voter", columns="receiver", values="n_obs")
        d, n = d.reindex(index=rows, columns=cols), n.reindex(index=rows, columns=cols)
        im = ax.imshow(
            np.ma.masked_invalid(d.to_numpy()), cmap=DIVERGING, vmin=vmin, vmax=vmax,
            aspect="auto", interpolation="nearest",
        )  # fmt: skip
        ax.grid(False)
        for i, j in zip(*np.where(n.to_numpy() < 3), strict=True):
            ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, hatch="///",
                                       edgecolor=INK["muted"], lw=0))  # fmt: skip
        ax.set_xticks(range(len(cols)), cols, rotation=90, fontsize=7)
        ax.set_yticks(range(len(rows)), rows, fontsize=7)
        total = int(np.nansum(n.to_numpy()))
        ax.set_title(f"{title} (total n = {total}; hatched = n_obs < 3)")
        ax.set_xlabel("Receiver")
    axes[0].set_ylabel("Voter")
    assert im is not None
    fig.colorbar(im, ax=axes, shrink=0.7, label="Affinity (excess points, 0 = neutral)")
    return _save(fig, "fig01_affinity_heatmap", out_dir)


# --------------------------------------------------------------------- F3
def fig_forest(
    combined: pd.DataFrame, out_dir: Path, top: int = 20, min_obs: int = 5
) -> list[Path]:
    """F3: top pairs by delta with intervals, n in labels, filled if lfsr < 0.05.

    Only pairs with at least ``min_obs`` ballots are ranked (plan review M2): pairs seen
    once or twice are otherwise lifted by the covariate prior rather than their own votes.
    """
    set_style()
    eligible = combined[combined["n_obs"] >= min_obs]
    d = eligible.nlargest(top, "delta").iloc[::-1].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7, 0.32 * len(d) + 1.5))
    y = np.arange(len(d))
    color = VOTE_TYPE_COLORS["combined"]
    ax.hlines(y, d["delta_lo"], d["delta_hi"], color=color, lw=1.5)
    for yi, row in zip(y, d.to_dict("records"), strict=True):
        sig = float(row["lfsr"]) < 0.05
        ax.plot(float(row["delta"]), yi, "o", color=color, mfc=color if sig else "white", ms=7)
    ax.axvline(0, color=INK["muted"], lw=1)
    ax.set_yticks(
        y, [f"{r['voter']}→{r['receiver']} (n={int(r['n_obs'])})" for r in d.to_dict("records")]
    )
    ax.set_xlabel("Affinity (excess points) with 90% interval")
    ax.set_title(f"Top {len(d)} pairs, combined (filled: lfsr < 0.05)")
    return _save(fig, "fig03_top_pairs_forest", out_dir)


# --------------------------------------------------------------------- F4
def fig_stability(stab: pd.DataFrame, out_dir: Path) -> list[Path]:
    """F4: Pearson r by split and vote type, with CI of (ceiling - drift) where given."""
    set_style()
    splits = list(dict.fromkeys(stab["split"]))
    types = list(dict.fromkeys(stab["vote_type"]))
    w = 0.8 / max(len(types), 1)
    fig, ax = plt.subplots(figsize=(7, 4))
    for k, vt in enumerate(types):
        for i, sp in enumerate(splits):
            r = stab[(stab["vote_type"] == vt) & (stab["split"] == sp)]
            if r.empty:
                continue
            r0 = r.iloc[0]
            x = i + (k - (len(types) - 1) / 2) * w
            ax.bar(x, r0["pearson"], w * 0.9, color=VOTE_TYPE_COLORS.get(vt, "#999999"),
                   label=vt if i == 0 else None)  # fmt: skip
            ax.text(x, max(r0["pearson"], 0) + 0.02, f"n={int(r0['n_pairs'])}",
                    ha="center", fontsize=7)  # fmt: skip
            if np.isfinite(r0["diff_lo"]) and np.isfinite(r0["diff_hi"]):
                ax.annotate(f"ceiling-drift\n[{r0['diff_lo']:.2f}, {r0['diff_hi']:.2f}]",
                            (x, r0["pearson"] / 2), ha="center", fontsize=6,
                            color="white")  # fmt: skip
    ax.set_xticks(range(len(splits)), splits)
    ax.set_ylabel("Pearson r between halves")
    ax.set_title("Stability of pair affinities")
    ax.legend()
    return _save(fig, "fig04_stability", out_dir)


# --------------------------------------------------------------------- F5
def fig_jury_vs_televote(gap: pd.DataFrame, out_dir: Path, top: int = 25) -> list[Path]:
    """F5: dumbbell for top-|gap| pairs plus scatter of all pairs annotated with r."""
    set_style()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 7), gridspec_kw={"width_ratios": [1, 1]})
    d = gap.reindex(gap["gap"].abs().sort_values(ascending=False).index).head(top)
    d = d.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(d))
    a1.hlines(y, d["delta_jury"], d["delta_televote"], color=INK["muted"], lw=1.5)
    a1.errorbar((d["delta_jury"] + d["delta_televote"]) / 2, y, xerr=None, fmt="none")
    a1.scatter(d["delta_jury"], y, color=VOTE_TYPE_COLORS["jury"], label="Jury", zorder=3)
    a1.scatter(d["delta_televote"], y, color=VOTE_TYPE_COLORS["televote"], label="Televote",
               zorder=3)  # fmt: skip
    a1.axvline(0, color=INK["muted"], lw=1)
    labs = [
        f"{r['voter']}→{r['receiver']} (nJ={int(r['n_jury'])}, nT={int(r['n_televote'])})"
        for r in d.to_dict("records")
    ]
    a1.set_yticks(y, labs, fontsize=8)
    a1.set_xlabel("Affinity (excess points)")
    a1.set_title(f"Top {len(d)} pairs by |gap|")
    a1.legend()
    ok = gap[["delta_jury", "delta_televote"]].dropna()
    a2.scatter(ok["delta_jury"], ok["delta_televote"], s=14, alpha=0.6,
               color=VOTE_TYPE_COLORS["combined"])  # fmt: skip
    lim = symmetric_limits(ok.to_numpy()) if len(ok) else (-1.0, 1.0)
    a2.plot(lim, lim, color=INK["muted"], lw=1, ls="--")
    r = float(np.corrcoef(ok["delta_jury"], ok["delta_televote"])[0, 1]) if len(ok) > 2 else np.nan
    a2.text(0.04, 0.95, f"r = {r:.2f}, n = {len(ok)} pairs", transform=a2.transAxes, va="top")
    a2.set_xlabel("Jury affinity")
    a2.set_ylabel("Televote affinity")
    a2.set_title("All pairs (dashed: equality)")
    return _save(fig, "fig05_jury_vs_televote", out_dir)


# --------------------------------------------------------------------- F6
def fig_beta(beta: pd.DataFrame, out_dir: Path) -> list[Path]:
    """F6: covariate coefficients, jury vs televote, with intervals."""
    set_style()
    covs = list(dict.fromkeys(beta["covariate"]))
    fig, ax = plt.subplots(figsize=(7, 0.7 * len(covs) + 1.5))
    for off, vt in zip((-0.15, 0.15), ("jury", "televote"), strict=True):
        s = beta[beta["vote_type"] == vt].set_index("covariate").reindex(covs)
        if {"beta_points", "lo_points", "hi_points"} <= set(s.columns):
            s = s.assign(beta=s["beta_points"], lo=s["lo_points"], hi=s["hi_points"])
        y = np.arange(len(covs)) + off
        xerr = np.vstack([s["beta"] - s["lo"], s["hi"] - s["beta"]])
        ax.errorbar(s["beta"], y, xerr=xerr, fmt="o", color=VOTE_TYPE_COLORS[vt], label=vt,
                    capsize=3)  # fmt: skip
    ax.axvline(0, color=INK["muted"], lw=1)
    ax.set_yticks(range(len(covs)), covs)
    ax.invert_yaxis()
    ax.set_xlabel("Effect in excess points (reference ballot), 90% interval (±1.645 bootstrap SD)")
    ax.set_title("Covariate effects on affinity")
    ax.legend()
    return _save(fig, "fig06_covariate_effects", out_dir)


# --------------------------------------------------------------------- F7
def geo_positions(attrs: pd.DataFrame, nodes: list[str]) -> dict[str, np.ndarray]:
    """Equirectangular capital positions scaled to roughly unit size."""
    a = attrs.set_index("code").reindex(nodes)
    lat0 = np.deg2rad(np.nanmean(a["capital_lat"]))
    xy = np.column_stack([a["capital_lon"] * np.cos(lat0), a["capital_lat"]]).astype(float)
    xy = np.where(np.isfinite(xy), xy, np.nanmean(xy, axis=0))
    med = np.median(xy, axis=0)
    mad = np.median(np.abs(xy - med), axis=0) + 1e-9
    xy = np.clip((xy - med) / (1.4826 * mad), -2.5, 2.5)  # robust scale; outliers to the rim
    return {n: xy[i] for i, n in enumerate(nodes)}


def anchored_layout(
    edges: pd.DataFrame, geo: dict[str, np.ndarray], alpha: float = 0.75
) -> dict[str, np.ndarray]:
    """Blend geography with a spring layout (alpha*geo), then de-overlap nodes."""
    g = nx.Graph()
    g.add_nodes_from(geo)
    g.add_weighted_edges_from(
        (r["voter"], r["receiver"], max(float(r["delta"]), 1e-3)) for r in edges.to_dict("records")
    )
    spring = nx.spring_layout(g, pos={k: v.copy() for k, v in geo.items()}, weight="weight",
                              iterations=30, seed=0)  # fmt: skip
    s = np.array([spring[n] for n in geo])
    s = (s - s.mean(axis=0)) / (s.std() or 1.0)
    gg = np.array([geo[n] for n in geo])
    pos = alpha * gg + (1 - alpha) * s
    min_d = 0.9 * (np.ptp(pos) + 1e-9) / max(np.sqrt(len(pos)), 1)
    for _ in range(300):
        diff = pos[:, None, :] - pos[None, :, :]
        dist = np.linalg.norm(diff, axis=2) + np.eye(len(pos))
        push = np.where((dist < min_d)[..., None] & ~np.eye(len(pos), dtype=bool)[..., None],
                        diff / dist[..., None] * (min_d - dist)[..., None] / 2, 0.0)  # fmt: skip
        pos = pos + push.sum(axis=1)
    return {n: pos[i] for i, n in enumerate(geo)}


def fig_backbone(
    edges: dict[str, pd.DataFrame],
    communities: pd.DataFrame,
    attrs: pd.DataFrame,
    out_dir: Path,
    top_k: int = 30,
) -> list[Path]:
    """F7: per-period (columns) and vote-type (rows) backbone, shared node positions."""
    set_style()
    periods = [p for p in PERIODS if p in edges]
    allp = pd.concat(edges.values())
    nodes = sorted(set(allp["voter"]) | set(allp["receiver"]) | set(communities["country"]))
    kept = allp[allp["delta"] > 0]
    union = (
        kept.sort_values("delta", ascending=False)
        .groupby("vote_type", group_keys=False)
        .head(3 * top_k)
    )
    pos = anchored_layout(union, geo_positions(attrs, nodes))
    comm = dict(zip(communities["country"], communities["community"], strict=False))
    ids = sorted(set(comm.values()))
    col = {c: COMMUNITY_COLORS[i % len(COMMUNITY_COLORS)] for i, c in enumerate(ids)}
    vtypes = list(dict.fromkeys(allp["vote_type"]))
    size = (5 * len(periods), 4.6 * len(vtypes))
    fig, axes = plt.subplots(len(vtypes), len(periods), figsize=size,
                             squeeze=False)  # fmt: skip
    dmax = float(kept["delta"].max()) if len(kept) else 1.0
    for i, vt in enumerate(vtypes):
        for j, p in enumerate(periods):
            ax = axes[i, j]
            e = edges[p]
            e = e[(e["vote_type"] == vt) & (e["delta"] > 0)].nlargest(top_k, "delta")
            g = nx.DiGraph()
            g.add_nodes_from(nodes)
            nx.draw_networkx_edges(
                g, pos, ax=ax, edgelist=list(zip(e["voter"], e["receiver"], strict=True)),
                width=[0.6 + 3.5 * d / dmax for d in e["delta"]], edge_color=INK["primary"],
                alpha=0.55, arrows=True, arrowsize=8, node_size=300,
                connectionstyle="arc3,rad=0.15",
            )  # fmt: skip
            nx.draw_networkx_nodes(g, pos, ax=ax, node_size=260,
                                   node_color=[col.get(comm.get(n), "#cccccc") for n in nodes],
                                   edgecolors="white")  # fmt: skip
            nx.draw_networkx_labels(g, pos, ax=ax, font_size=7)
            ax.set_title(f"{p}, {vt}")
            ax.set_axis_off()
    fig.legend(handles=[Patch(color=col[c], label=f"community {c}") for c in ids],
               loc="lower center", ncol=len(ids))  # fmt: skip
    fig.suptitle(
        f"Strongest {top_k} affinities per panel (edge width ∝ excess points); "
        "geography-anchored layout, fixed across panels; distant capitals placed at the rim"
    )
    return _save(fig, "fig07_dynamic_backbone", out_dir)


# ------------------------------------------------------------------- main
def main(
    results_dir: str | Path = "reports/results", out_dir: str | Path = "reports/figures"
) -> list[Path]:
    """Build every figure whose inputs exist; log and skip the rest."""
    res, out = Path(results_dir), Path(out_dir)
    written: list[Path] = []

    def run(name: str, needs: list[str], build: Callable[[Frames], list[Path]]) -> None:
        frames: Frames = {}
        for f in needs:
            df = _read(res, f)
            if df is None:
                log.info("skipping %s: missing %s", name, f)
                return
            frames[f] = df
        written.extend(build(frames))

    comm_df = _read(res, "communities.csv")
    run("F1", ["rq1_dyads_jury.csv", "rq1_dyads_televote.csv"],
        lambda f: fig_heatmap(f["rq1_dyads_jury.csv"], f["rq1_dyads_televote.csv"], comm_df,
                              out))  # fmt: skip
    run("F3", ["rq1_dyads_combined.csv"],
        lambda f: fig_forest(f["rq1_dyads_combined.csv"], out))  # fmt: skip
    run("F4", ["rq2_stability.csv"], lambda f: fig_stability(f["rq2_stability.csv"], out))
    run("F5", ["rq3_gap.csv"], lambda f: fig_jury_vs_televote(f["rq3_gap.csv"], out))
    run("F6", ["rq1_beta.csv"], lambda f: fig_beta(f["rq1_beta.csv"], out))
    attrs = pd.read_csv(ATTRIBUTES) if ATTRIBUTES.exists() else None
    if attrs is None:
        log.info("skipping F7: missing %s", ATTRIBUTES)
    else:
        run("F7", ["communities.csv", *[f"network_edges_{p}.csv" for p in PERIODS]],
            lambda f: fig_backbone(
                {p: f[f"network_edges_{p}.csv"] for p in PERIODS}, f["communities.csv"], attrs,
                out))  # fmt: skip
    return written


if __name__ == "__main__":
    main()
