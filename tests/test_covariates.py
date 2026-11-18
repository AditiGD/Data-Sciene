"""Dyad covariates from the reference tables."""

from __future__ import annotations

import numpy as np
import pandas as pd

from esc_bias.covariates import dyad_covariates, vif


def test_dyad_covariates_shape_and_symmetry() -> None:
    cov = dyad_covariates()
    n = 45
    assert len(cov) == n * (n - 1)
    assert cov.index.names == ["voter", "receiver"]
    swapped = cov.copy()
    swapped.index = swapped.index.swaplevel().set_names(["voter", "receiver"])
    pd.testing.assert_frame_equal(cov, swapped.reindex(cov.index))
    assert cov.loc[("GR", "CY"), "shared_language"] == 1.0
    assert cov.loc[("SE", "NO"), "nordic"] == 1.0 and cov.loc[("SE", "FR"), "nordic"] == 0.0
    assert cov.loc[("DK", "SE"), "border_maritime"] == 1.0
    assert cov.loc[("AL", "GR"), "border_land"] == 1.0
    assert abs(cov["log_distance"].mean()) < 1e-9


def test_subset_and_vif() -> None:
    cov = dyad_covariates(["AL", "GR", "ME", "IT"])
    assert len(cov) == 12
    v = vif(pd.DataFrame({"a": np.arange(10.0), "b": np.arange(10.0) ** 2, "c": [1, 0] * 5}))
    assert (v >= 1).all()
