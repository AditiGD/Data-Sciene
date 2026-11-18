"""Dyad-level covariates built only from the two curated reference tables.

Sources (both under ``audit/reference_tables/``):

* ``contiguity_curated.csv``: unordered country pairs with ``contig_type``. ``land``
  rows give ``border_land``; ``sea_*`` rows (COW-style water distance classes) give
  ``border_maritime``. GeoNames land neighbours; sea classes curated by hand.
* ``country_attributes.csv``: UN M49 sub-region (``same_m49_region``), GeoNames
  language lists (``shared_language``: any language code in common, region suffix
  such as ``en-GB`` dropped), bloc flags ``ex_ussr``, ``ex_yugoslavia`` and ``nordic``
  (1 when both countries are in the bloc), and capital coordinates (``log_distance``:
  natural log of the haversine capital-to-capital distance in km, centred at its mean
  over the off-diagonal ordered pairs).

Reykjavik's coordinates are absent from the CSV and are filled from a fixed constant.

The table is indexed by ``(voter, receiver)`` over all ordered pairs of distinct
countries; every covariate is symmetric in the pair.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "audit" / "reference_tables"
EARTH_RADIUS_KM = 6371.0088
# Capital coordinates missing from country_attributes.csv (GeoNames gap): the only
# non-CSV values used, filled so that log_distance is defined for every country.
_CAPITAL_FALLBACK = {"IS": (64.1466, -21.9426)}  # Reykjavik


def _languages(cell: object) -> set[str]:
    if not isinstance(cell, str):
        return set()
    return {p.strip().split("-")[0].lower() for p in cell.split(",") if p.strip()}


def dyad_covariates(countries: list[str] | None = None) -> pd.DataFrame:
    """Ordered-pair covariate table (voter, receiver) from the reference CSVs.

    Args:
        countries: subset/order of country codes; default all rows of the attributes file.

    Returns:
        DataFrame with columns ``border_land``, ``border_maritime``, ``same_m49_region``,
        ``shared_language``, ``ex_ussr``, ``ex_yugoslavia``, ``nordic`` (0/1 floats) and
        ``log_distance`` (centred).
    """
    attrs = pd.read_csv(REFERENCE_DIR / "country_attributes.csv").set_index("code")
    contig = pd.read_csv(REFERENCE_DIR / "contiguity_curated.csv")
    codes = list(attrs.index) if countries is None else list(countries)
    missing = set(codes) - set(attrs.index)
    if missing:
        raise KeyError(f"countries not in country_attributes.csv: {sorted(missing)}")
    attrs = attrs.loc[codes].copy()
    for code, (la, lo) in _CAPITAL_FALLBACK.items():
        if code in attrs.index and pd.isna(attrs.loc[code, ["capital_lat"]]).any():
            attrs.loc[code, ["capital_lat", "capital_lon"]] = (la, lo)
    n = len(codes)
    pos = {c: i for i, c in enumerate(codes)}

    def pair_matrix(mask: pd.Series) -> np.ndarray:
        m = np.zeros((n, n))
        for a, b in contig.loc[mask, ["a", "b"]].itertuples(index=False):
            if a in pos and b in pos:
                m[pos[a], pos[b]] = m[pos[b], pos[a]] = 1.0
        return m

    mats: dict[str, np.ndarray] = {
        "border_land": pair_matrix(contig["contig_type"] == "land"),
        "border_maritime": pair_matrix(contig["contig_type"].str.startswith("sea_")),
    }
    region = attrs["un_m49_subregion"].to_numpy()
    mats["same_m49_region"] = (region[:, None] == region[None, :]).astype(float)
    langs = [_languages(x) for x in attrs["geonames_languages"]]
    mats["shared_language"] = np.array(
        [[float(bool(a & b)) for b in langs] for a in langs], dtype=float
    )
    for bloc in ("ex_ussr", "ex_yugoslavia", "nordic"):
        f = attrs[bloc].astype(bool).to_numpy().astype(float)
        mats[bloc] = np.outer(f, f)
    lat = np.radians(attrs["capital_lat"].to_numpy(float))
    lon = np.radians(attrs["capital_lon"].to_numpy(float))
    h = (
        np.sin((lat[:, None] - lat[None, :]) / 2) ** 2
        + np.cos(lat)[:, None]
        * np.cos(lat)[None, :]
        * np.sin((lon[:, None] - lon[None, :]) / 2) ** 2
    )
    dist = 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(h, 0, 1)))
    off = ~np.eye(n, dtype=bool)
    with np.errstate(divide="ignore"):
        logd = np.log(np.where(off, dist, 1.0))
    logd = logd - logd[off].mean()
    mats["log_distance"] = logd

    vi, ri = np.where(off)
    index = pd.MultiIndex.from_arrays(
        [np.array(codes)[vi], np.array(codes)[ri]], names=["voter", "receiver"]
    )
    return pd.DataFrame({k: v[vi, ri] for k, v in mats.items()}, index=index)


def vif(df: pd.DataFrame) -> pd.Series:
    """Variance inflation factor of each column (1 / (1 - R²) regressing it on the others).

    Constant columns get NaN; perfectly collinear columns get ``inf``.
    """
    x = df.to_numpy(dtype=float)
    out: dict[str, float] = {}
    for j, col in enumerate(df.columns):
        y = x[:, j]
        if np.ptp(y) == 0:
            out[col] = float("nan")
            continue
        others = np.column_stack([np.ones(len(y)), np.delete(x, j, axis=1)])
        beta, *_ = np.linalg.lstsq(others, y, rcond=None)
        resid = y - others @ beta
        r2 = 1.0 - resid @ resid / ((y - y.mean()) @ (y - y.mean()))
        out[col] = float("inf") if r2 >= 1 - 1e-12 else float(1.0 / (1.0 - r2))
    return pd.Series(out, name="vif")
