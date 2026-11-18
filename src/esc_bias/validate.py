"""Data contract (pandera schema) and ballot-integrity checks for the tidy vote table.

Every check returns failures as rows instead of raising, and :func:`run_all_checks`
concatenates them into one tidy **report** with columns::

    check, severity, passed, year, round, vote_type, voter, receiver, detail

A passing check contributes one row with ``passed=True`` (so the report also documents
what was checked); a failing check contributes one row per failing record. Integrity
problems in real data are therefore *reported*, never hidden and never fatal; use
``esc-bias validate --strict`` to turn errors into a non-zero exit code.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

import pandas as pd
import pandera.pandas as pa

from esc_bias.io import JURY_METHODS, KEY_COLUMNS, ROUND_ORDER, VOTE_TYPE_ORDER

REPORT_COLUMNS: tuple[str, ...] = (
    "check",
    "severity",
    "passed",
    "year",
    "round",
    "vote_type",
    "voter",
    "receiver",
    "detail",
)
BALLOT_KEYS: list[str] = ["year", "round", "vote_type", "voter"]
DEFAULT_BALLOT: tuple[int, ...] = (12, 10, 8, 7, 6, 5, 4, 3, 2, 1)
SINGLE_CHANNEL_POINTS = (0, *DEFAULT_BALLOT)


# --------------------------------------------------------------------------- schema
def tidy_schema() -> pa.DataFrameSchema:
    """The data contract for the tidy vote table (``data/processed/votes.parquet``)."""
    code = pa.Check.str_matches(r"^[A-Z]{2,3}$")
    return pa.DataFrameSchema(
        {
            "year": pa.Column(int, pa.Check.in_range(1956, 2100)),
            "round": pa.Column(str, pa.Check.isin(ROUND_ORDER)),
            "vote_type": pa.Column(str, pa.Check.isin(VOTE_TYPE_ORDER)),
            "voter": pa.Column(str, code),
            "receiver": pa.Column(str, code),
            "points": pa.Column(int, pa.Check.in_range(0, 24)),
            "receiver_place": pa.Column("Int64", pa.Check.ge(1), nullable=True),
            "receiver_running": pa.Column("Int64", pa.Check.ge(1), nullable=True),
            "vote_type_source": pa.Column(str, pa.Check.isin(["jury", "public", "tele", "total"])),
            "voter_is_country": pa.Column(bool),
            "voter_performs_in_round": pa.Column(bool),
            "jury_method": pa.Column(str, pa.Check.isin(JURY_METHODS), nullable=True),
            # added by anomalies.apply_register; optional so raw builds also validate
            "is_flagged": pa.Column(bool, required=False),
            "exclude": pa.Column(bool, required=False),
            "sensitivity": pa.Column(bool, required=False),
            "anomaly_ids": pa.Column(str, required=False),
        },
        checks=[
            pa.Check(
                lambda df: (
                    (df["vote_type"] == "combined") | df["points"].isin(SINGLE_CHANNEL_POINTS)
                ),
                name="single_channel_points_in_ballot_scale",
                error="jury/televote points must be one of 0,1-8,10,12",
            )
        ],
        strict=False,
        coerce=False,
    )


# --------------------------------------------------------------------------- helpers
def _rows(failures: pd.DataFrame, detail: str | pd.Series | None = None) -> pd.DataFrame:
    """Normalise a failures frame to the report's key columns + ``detail``."""
    out = pd.DataFrame(index=failures.index)
    for col in ("year", "round", "vote_type", "voter", "receiver"):
        out[col] = failures.get(col, pd.NA)
    if detail is not None:
        out["detail"] = detail
    elif "detail" in failures:
        out["detail"] = failures["detail"]
    else:
        out["detail"] = ""
    return out.reset_index(drop=True)


def _result(check: str, severity: str, failures: pd.DataFrame, ok_detail: str = "") -> pd.DataFrame:
    """Turn a failures frame into report rows (one pass row if there are none)."""
    if failures.empty:
        row: dict[str, Any] = dict.fromkeys(REPORT_COLUMNS, pd.NA)
        row.update(check=check, severity=severity, passed=True, detail=ok_detail)
        return pd.DataFrame([row], columns=list(REPORT_COLUMNS))
    out = failures.assign(check=check, severity=severity, passed=False)
    return out[list(REPORT_COLUMNS)]


# --------------------------------------------------------------------------- checks
def check_schema(votes: pd.DataFrame) -> pd.DataFrame:
    """Validate against :func:`tidy_schema`; every failure case becomes a report row."""
    try:
        tidy_schema().validate(votes, lazy=True)
    except pa.errors.SchemaErrors as err:
        fc = err.failure_cases.reset_index(drop=True)
        keyed = []
        for _, f in fc.iterrows():
            idx = f.get("index")
            base = (
                votes.loc[idx, list(KEY_COLUMNS)].to_dict()
                if idx is not None and not pd.isna(idx) and idx in votes.index
                else {}
            )
            base["detail"] = f"{f.get('column')}: {f.get('check')} (value={f.get('failure_case')})"
            keyed.append(base)
        return _rows(pd.DataFrame(keyed))
    return _rows(votes.iloc[0:0])


def check_unique_keys(votes: pd.DataFrame) -> pd.DataFrame:
    """Each (year, round, vote_type, voter, receiver) appears at most once."""
    dup = votes[votes.duplicated(list(KEY_COLUMNS), keep=False)]
    return _rows(dup.drop_duplicates(list(KEY_COLUMNS)), "duplicate key")


def check_no_self_votes(votes: pd.DataFrame) -> pd.DataFrame:
    """No voter appears as its own receiver (a self row exists only if the raw data had one)."""
    bad = votes[votes["voter"] == votes["receiver"]]
    return _rows(bad, bad["points"].map(lambda p: f"self-vote with {p} points"))


def check_ballot_points_set(
    votes: pd.DataFrame, ballot_points: Iterable[int] = DEFAULT_BALLOT
) -> pd.DataFrame:
    """Each jury/televote ballot awards every value in ``ballot_points`` exactly once.

    ``combined`` is skipped: it is a sum of two ballots, not a ballot.
    """
    expected = sorted(ballot_points)
    single = votes[votes["vote_type"] != "combined"]
    got = single[single["points"] > 0].groupby(BALLOT_KEYS)["points"].agg(lambda s: sorted(s))
    # ballots with no positive points at all would be missing from `got`
    all_ballots = single.groupby(BALLOT_KEYS).size().index
    got = got.reindex(all_ballots)
    bad = got[got.map(lambda v: not isinstance(v, list) or v != expected)]
    if bad.empty:
        return _rows(single.iloc[0:0])
    df = bad.rename("got").reset_index()
    detail = df["got"].map(
        lambda v: f"awarded {v if isinstance(v, list) else []}, expected {expected}"
    )
    return _rows(df.assign(receiver=None), detail)


def check_complete_ballots(votes: pd.DataFrame) -> pd.DataFrame:
    """Every ballot has a row (explicit zero or points) for every performer except self."""
    performers: dict[Any, set[str]] = (
        votes.groupby(["year", "round", "vote_type"])["receiver"].agg(set).to_dict()
    )
    rows = []
    for (year, rnd, vt, voter), group in votes.groupby(BALLOT_KEYS):
        expected = performers[(year, rnd, vt)] - {voter}
        missing = expected - set(group["receiver"])
        if missing:
            rows.append(
                {
                    "year": year,
                    "round": rnd,
                    "vote_type": vt,
                    "voter": voter,
                    "detail": f"no row for receivers {sorted(missing)}",
                }
            )
    return _rows(pd.DataFrame(rows, columns=[*BALLOT_KEYS, "detail"]))


def check_jury_plus_televote_equals_combined(votes: pd.DataFrame) -> pd.DataFrame:
    """In rounds that report a split, combined == jury + televote for every pair.

    A missing channel counts as 0 (e.g. ``WLD`` has a televote but no jury, so its
    combined points must equal its televote points).
    """
    keys = ["year", "round", "voter", "receiver"]
    wide = votes.pivot_table(index=keys, columns="vote_type", values="points", aggfunc="sum")
    wide = wide.reindex(columns=["jury", "televote", "combined"])  # missing channel -> NaN
    split_rounds = votes.loc[votes["vote_type"] == "jury", ["year", "round"]].drop_duplicates()
    wide = wide.reset_index().merge(split_rounds, on=["year", "round"])
    wide = wide[wide["combined"].notna()]
    expected = wide["jury"].fillna(0) + wide["televote"].fillna(0)
    bad = wide[expected != wide["combined"]].assign(vote_type="combined")
    detail = [
        f"jury={j} + televote={t} != combined={c}"
        for j, t, c in zip(bad["jury"], bad["televote"], bad["combined"], strict=True)
    ]
    return _rows(bad, pd.Series(detail, index=bad.index, dtype="str"))


def check_receiver_totals(votes: pd.DataFrame, receiver_totals: pd.DataFrame) -> pd.DataFrame:
    """Sum of points per (year, round, vote_type, receiver) equals the raw ``points`` field."""
    keys = ["year", "round", "vote_type", "receiver"]
    summed = votes.groupby(keys, as_index=False)["points"].sum()
    merged = summed.merge(receiver_totals, on=keys, how="outer", indicator=True)
    bad = merged[(merged["_merge"] != "both") | (merged["points"] != merged["raw_points"])]
    detail = [
        f"sum of votes={p}, raw points field={r} ({m})"
        for p, r, m in zip(bad["points"], bad["raw_points"], bad["_merge"], strict=True)
    ]
    return _rows(bad.assign(voter=None), pd.Series(detail, index=bad.index, dtype="str"))


def check_known_codes(
    votes: pd.DataFrame,
    countries: Mapping[str, str],
    non_country_voters: Iterable[str] = ("WLD",),
) -> pd.DataFrame:
    """Voters/receivers are in ``countries.json``.

    Non-country voters (``WLD``) are allowed only as televote voters (and in the combined
    total that contains that televote); never as jury voters or receivers.
    """
    non_country = set(non_country_voters)
    known = set(countries)
    rows = []
    voters = votes[["year", "round", "vote_type", "voter"]].drop_duplicates()
    for _, r in voters.iterrows():
        v = r["voter"]
        if v in non_country:
            if r["vote_type"] == "jury":
                rows.append({**r.to_dict(), "detail": f"non-country voter {v} in a jury vote"})
        elif v not in known:
            rows.append({**r.to_dict(), "detail": f"unknown voter code {v}"})
    receivers = votes[["year", "round", "vote_type", "receiver"]].drop_duplicates()
    for _, r in receivers.iterrows():
        if r["receiver"] not in known:
            rows.append({**r.to_dict(), "detail": f"unknown/non-country receiver {r['receiver']}"})
    return _rows(pd.DataFrame(rows, columns=[*KEY_COLUMNS, "detail"]))


def check_identical_channels(votes: pd.DataFrame) -> pd.DataFrame:
    """Warn when a voter's jury and televote ballots are identical in a round.

    Identical ballots are a data-derived signal that one channel was substituted by the
    other (e.g. a televote replaced by the jury result). Candidates for the register.
    """
    pos = votes[(votes["points"] > 0) & votes["vote_type"].isin(["jury", "televote"])]
    entry = pos["receiver"] + ":" + pos["points"].astype(str)
    ballots = pos.assign(entry=entry).pivot_table(
        index=["year", "round", "voter"],
        columns="vote_type",
        values="entry",
        aggfunc=lambda s: ";".join(sorted(s)),
    )
    if not {"jury", "televote"}.issubset(ballots.columns):
        return _rows(votes.iloc[0:0])
    same = ballots[ballots["jury"] == ballots["televote"]].reset_index()
    return _rows(same.assign(vote_type="jury;televote"), "jury ballot identical to televote")


def check_round_coverage(rounds: pd.DataFrame | None) -> pd.DataFrame:
    """Report requested rounds that are missing or cancelled (e.g. 2020)."""
    if rounds is None or rounds.empty:
        return _rows(pd.DataFrame(columns=["year", "round"]))
    bad = rounds[rounds["status"] != "ok"]
    return _rows(bad, bad["status"].map(lambda s: f"round {s}"))


# --------------------------------------------------------------------------- runner
def run_all_checks(
    votes: pd.DataFrame,
    receiver_totals: pd.DataFrame | None = None,
    countries: Mapping[str, str] | None = None,
    rounds: pd.DataFrame | None = None,
    ballot_points: Iterable[int] = DEFAULT_BALLOT,
    non_country_voters: Iterable[str] = ("WLD",),
) -> pd.DataFrame:
    """Run every check and return the tidy report (see module docstring)."""
    ballot_points = tuple(ballot_points)
    non_country_voters = tuple(non_country_voters)
    checks: list[tuple[str, str, Callable[[], pd.DataFrame]]] = [
        ("schema", "error", lambda: check_schema(votes)),
        ("unique_keys", "error", lambda: check_unique_keys(votes)),
        ("no_self_votes", "error", lambda: check_no_self_votes(votes)),
        ("ballot_points_set", "error", lambda: check_ballot_points_set(votes, ballot_points)),
        ("complete_ballots", "error", lambda: check_complete_ballots(votes)),
        (
            "jury_plus_televote_equals_combined",
            "error",
            lambda: check_jury_plus_televote_equals_combined(votes),
        ),
        ("identical_jury_televote_ballot", "warning", lambda: check_identical_channels(votes)),
        ("round_coverage", "warning", lambda: check_round_coverage(rounds)),
    ]
    if receiver_totals is not None:
        checks.append(
            (
                "receiver_totals_match_raw",
                "error",
                lambda: check_receiver_totals(votes, receiver_totals),
            )
        )
    if countries is not None:
        checks.append(
            (
                "known_codes",
                "error",
                lambda: check_known_codes(votes, countries, non_country_voters),
            )
        )
    parts = [_result(name, sev, fn()) for name, sev, fn in checks]
    report = pd.concat(parts, ignore_index=True)
    report["year"] = report["year"].astype("Int64")
    return report


def summarise(report: pd.DataFrame) -> pd.DataFrame:
    """One row per check: severity, status, number of failures and a first example."""
    rows: list[dict[str, Any]] = []
    for name, g in report.groupby("check", sort=False):
        fails = g[~g["passed"]]
        example = ""
        if not fails.empty:
            f = fails.iloc[0]
            keys = [str(f[c]) for c in ("year", "round", "vote_type", "voter", "receiver")]
            example = (
                " ".join(k for k in keys if k not in ("<NA>", "nan", "None")) + f": {f['detail']}"
            )
        rows.append(
            {
                "check": name,
                "severity": g["severity"].iloc[0],
                "status": "pass" if fails.empty else "FAIL",
                "n_failures": len(fails),
                "example": example,
            }
        )
    return pd.DataFrame(rows)


def has_errors(report: pd.DataFrame) -> bool:
    """True if any ``error``-severity check failed."""
    return bool(((report["severity"] == "error") & ~report["passed"]).any())


def summary_markdown(
    report: pd.DataFrame,
    provenance: Mapping[str, Any] | None = None,
    counts: pd.DataFrame | None = None,
) -> str:
    """Render a short, deterministic markdown summary (no timestamps, so it diffs cleanly)."""
    lines = ["# Validation summary", ""]
    if provenance:
        lines += ["## Provenance", ""]
        lines += [f"- **{k}**: `{v}`" for k, v in provenance.items()]
        lines.append("")
    if counts is not None:
        lines += ["## Row counts", "", _md_table(counts), ""]
    summary = summarise(report)
    n_err = int(((summary["severity"] == "error") & (summary["status"] == "FAIL")).sum())
    lines += [
        "## Checks",
        "",
        f"{len(summary)} checks, {n_err} failing error-level checks.",
        "",
        _md_table(summary),
        "",
        "Full per-record results: `validation_report.csv`.",
        "",
    ]
    return "\n".join(lines)


def _md_table(df: pd.DataFrame) -> str:
    """Minimal markdown table (avoids an optional ``tabulate`` dependency)."""
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        cells = [str(v).replace("|", "\\|") for v in row]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)
