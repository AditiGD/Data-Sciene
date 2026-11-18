"""Consistent figure style. Plotting code lives in notebooks; style lives here.

Rules (see ``docs/05_engineering_standards.md`` §Figures):

* one fixed colour per vote type, everywhere (colour follows the entity, never its rank);
* diverging maps (bias) are blue <-> red around a neutral grey zero, symmetric limits;
* sequential maps (counts, magnitudes) are one hue, light -> dark;
* every saved figure goes through :func:`save_figure` (PNG + PDF, fixed DPI).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

#: Fixed categorical colours for the three vote types (validated CVD-safe as a set).
VOTE_TYPE_COLORS: dict[str, str] = {
    "jury": "#2a78d6",  # blue
    "televote": "#eb6834",  # orange
    "combined": "#1baf7a",  # aqua
}
INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781"}
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"

#: Diverging blue (negative) <-> grey (0) <-> red (positive), for bias heatmaps.
DIVERGING = LinearSegmentedColormap.from_list(
    "esc_diverging", ["#184f95", "#86b6ef", "#f0efec", "#f0a3a2", "#b42c2b"]
)
#: Sequential single-hue blue, for counts and magnitudes.
SEQUENTIAL = LinearSegmentedColormap.from_list(
    "esc_sequential", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
)


def set_style() -> None:
    """Apply the project's matplotlib defaults (call once at the top of a notebook)."""
    mpl.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "axes.edgecolor": "#c3c2b7",
            "axes.labelcolor": INK["secondary"],
            "axes.titlecolor": INK["primary"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "xtick.color": INK["muted"],
            "ytick.color": INK["muted"],
            "font.size": 10,
            "axes.titlesize": 11,
            "lines.linewidth": 2,
            "legend.frameon": False,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        }
    )


def symmetric_limits(values: object) -> tuple[float, float]:
    """``(-m, m)`` with ``m = max |value|`` so a diverging map is centred on zero."""
    arr = np.asarray(values, dtype=float)
    m = float(np.nanmax(np.abs(arr))) if np.isfinite(arr).any() else 1.0
    return -m, m


def save_figure(
    fig: Figure, name: str, out_dir: Path, formats: tuple[str, ...] = ("png", "pdf")
) -> list[Path]:
    """Save ``fig`` as ``out_dir/name.<fmt>`` for each format and close it.

    Use a stable, descriptive ``name`` (e.g. ``"fig03_jury_vs_televote_bias"``) so
    figures can be regenerated and referenced from the report.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    # No creation timestamps, so re-running the pipeline gives byte-identical PDFs.
    metadata = {
        "png": {"Software": "esc_bias"},
        "pdf": {"Creator": "esc_bias", "CreationDate": None},
    }
    paths = []
    for fmt in formats:
        path = out_dir / f"{name}.{fmt}"
        fig.savefig(path, metadata=metadata.get(fmt))
        paths.append(path)
    plt.close(fig)
    return paths
