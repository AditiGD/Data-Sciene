"""Anomaly register: a versioned CSV of known data issues and how each is handled.

The register (``config/anomaly_register.csv``) is the single place where we decide that
a vote is not a genuine voter -> receiver preference (substitute jury, non-country voter,
cancelled contest, ...). :func:`apply_register` turns it into boolean columns on the tidy
table so that every analysis filters the same way (handling legend of the data audit)::

    primary     = votes[~votes.exclude]                       # pair-level analyses
    sensitivity = votes[~votes.exclude & ~votes.sensitivity]  # pre-specified robustness run
"""

from __future__ import annotations

import io as _io
from pathlib import Path

import pandas as pd

REGISTER_COLUMNS: tuple[str, ...] = (
    "anomaly_id",
    "year",
    "round",
    "vote_type",
    "voter",
    "receiver",
    "issue",
    "handling",
    "source_url",
    "notes",
)
MATCH_COLUMNS: tuple[str, ...] = ("year", "round", "vote_type", "voter", "receiver")
HANDLINGS: frozenset[str] = frozenset({"keep", "flag", "exclude", "sensitivity"})
WILDCARD = "*"


def load_register(path: Path) -> pd.DataFrame:
    """Read the register CSV, skipping ``#`` comment lines, and check its contents.

    Raises:
        ValueError: missing columns, unknown ``handling`` or duplicate ``anomaly_id``.
    """
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    body = "\n".join(line for line in lines if not line.lstrip().startswith("#"))
    reg = pd.read_csv(_io.StringIO(body), dtype=str, keep_default_na=False)
    missing = set(REGISTER_COLUMNS) - set(reg.columns)
    if missing:
        raise ValueError(f"anomaly register {path} is missing columns {sorted(missing)}")
    bad = sorted(set(reg["handling"]) - HANDLINGS)
    if bad:
        raise ValueError(f"unknown handling values {bad}; allowed: {sorted(HANDLINGS)}")
    dupes = reg["anomaly_id"][reg["anomaly_id"].duplicated()].tolist()
    if dupes:
        raise ValueError(f"duplicate anomaly_id {dupes}")
    for col in MATCH_COLUMNS:
        reg[col] = reg[col].str.strip().replace("", WILDCARD)
    return reg[list(REGISTER_COLUMNS)]


def _match(series: pd.Series, pattern: str) -> pd.Series:
    """Boolean mask: ``*`` matches all, ``a;b`` matches any listed value."""
    if pattern == WILDCARD:
        return pd.Series(True, index=series.index)
    allowed = {p.strip() for p in pattern.split(";")}
    return series.astype(str).isin(allowed)


def matching_rows(votes: pd.DataFrame, entry: pd.Series) -> pd.Series:
    """Boolean mask of the tidy-table rows that one register entry applies to."""
    mask = pd.Series(True, index=votes.index)
    for col in MATCH_COLUMNS:
        mask &= _match(votes[col], str(entry[col]))
    return mask


def apply_register(votes: pd.DataFrame, register: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``votes`` with anomaly columns added.

    Added columns:
        ``is_flagged``  any non-``keep`` entry matches the row
        ``exclude``     an ``exclude`` entry matches
        ``sensitivity`` a ``sensitivity`` entry matches
        ``anomaly_ids`` ``;``-joined ids of matching non-``keep`` entries (``""`` if none)
    """
    out = votes.copy()
    out["is_flagged"] = False
    out["exclude"] = False
    out["sensitivity"] = False
    ids: list[list[str]] = [[] for _ in range(len(out))]
    for _, entry in register.iterrows():
        mask = matching_rows(out, entry)
        if not mask.any() or entry["handling"] == "keep":
            continue
        for pos in mask.to_numpy().nonzero()[0]:
            ids[pos].append(str(entry["anomaly_id"]))
        out.loc[mask, "is_flagged"] = True
        if entry["handling"] == "exclude":
            out.loc[mask, "exclude"] = True
        if entry["handling"] == "sensitivity":
            out.loc[mask, "sensitivity"] = True
    out["anomaly_ids"] = pd.Series([";".join(i) for i in ids], index=out.index, dtype="str")
    return out


def register_coverage(votes: pd.DataFrame, register: pd.DataFrame) -> pd.DataFrame:
    """Number of tidy rows each register entry matches (0 is fine for e.g. 2020)."""
    counts = [int(matching_rows(votes, e).sum()) for _, e in register.iterrows()]
    return register[["anomaly_id", "issue", "handling"]].assign(n_rows=counts)


def candidates_from_report(report: pd.DataFrame) -> pd.DataFrame:
    """Turn failed ballot-level checks of a validation report into draft register rows.

    The drafts have ``handling = flag`` and an empty ``source_url``; a human decides the
    final handling and adds evidence before copying them into the register.
    """
    ballot_checks = {"ballot_points_set", "no_self_votes", "jury_plus_televote_equals_combined"}
    failed = report[(~report["passed"]) & report["check"].isin(ballot_checks)]
    if failed.empty:
        return pd.DataFrame(columns=list(REGISTER_COLUMNS))
    keys = failed[["year", "round", "vote_type", "voter", "check", "detail"]].drop_duplicates(
        ["year", "round", "vote_type", "voter", "check"]
    )
    return pd.DataFrame(
        {
            "anomaly_id": [f"CAND{i + 1:03d}" for i in range(len(keys))],
            "year": keys["year"].astype("Int64").astype(str).to_numpy(),
            "round": keys["round"].to_numpy(),
            "vote_type": keys["vote_type"].fillna(WILDCARD).to_numpy(),
            "voter": keys["voter"].fillna(WILDCARD).to_numpy(),
            "receiver": WILDCARD,
            "issue": keys["check"].to_numpy(),
            "handling": "flag",
            "source_url": "",
            "notes": keys["detail"].to_numpy(),
        }
    )
