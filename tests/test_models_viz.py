"""Model frame selection, stubs, and figure helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from esc_bias.anomalies import apply_register, load_register
from esc_bias.config import PROJECT_ROOT
from esc_bias.io import build_tidy
from esc_bias.models import fit_crossed_effects, fit_rank_ordered_logit, model_frame
from esc_bias.viz import VOTE_TYPE_COLORS, save_figure, set_style, symmetric_limits


@pytest.fixture
def flagged(fake_root: Path):
    votes = build_tidy(fake_root, (2019, 2020, 2023)).votes
    return apply_register(votes, load_register(PROJECT_ROOT / "config" / "anomaly_register.csv"))


def test_model_frame_filters(flagged) -> None:
    primary = model_frame(flagged, "televote")
    assert "WLD" not in set(primary.voter.astype(str))  # A14 exclude
    sens = model_frame(flagged, "televote", sensitivity_run=True)
    assert len(sens) <= len(primary)
    finals = model_frame(flagged, "televote", rounds=("final",))
    assert set(finals["round"].astype(str)) == {"final"}
    assert str(primary["dyad"].iloc[0]).count(">") == 1


def test_model_frame_requires_register(fake_root: Path) -> None:
    with pytest.raises(KeyError, match="apply_register"):
        model_frame(build_tidy(fake_root, (2019,)).votes, "jury")


def test_fitting_functions_are_stubs(flagged) -> None:
    for fit in (fit_crossed_effects, fit_rank_ordered_logit):
        with pytest.raises(NotImplementedError):
            fit(model_frame(flagged, "jury"))


def test_save_figure_and_style(tmp_path: Path) -> None:
    set_style()
    fig, ax = plt.subplots()
    ax.bar(list(VOTE_TYPE_COLORS), [1, 2, 3], color=list(VOTE_TYPE_COLORS.values()))
    paths = save_figure(fig, "fig00_test", tmp_path)
    assert [p.suffix for p in paths] == [".png", ".pdf"]
    assert all(p.stat().st_size > 0 for p in paths)
    assert symmetric_limits([-1.0, 3.0]) == (-3.0, 3.0)
