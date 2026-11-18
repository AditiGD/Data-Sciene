"""Data contract and ballot-integrity checks."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from esc_bias.io import build_tidy
from esc_bias.validate import (
    REPORT_COLUMNS,
    has_errors,
    run_all_checks,
    summarise,
    summary_markdown,
)

FAKE_BALLOT = (3, 2, 1)  # the fake contest (see conftest.py) uses 3-2-1 ballots

YEARS = (2019, 2020, 2023)


def report_for(root: Path, votes: pd.DataFrame | None = None) -> pd.DataFrame:
    b = build_tidy(root, YEARS)
    return run_all_checks(
        b.votes if votes is None else votes,
        b.receiver_totals,
        b.countries,
        b.rounds,
        ballot_points=FAKE_BALLOT,
    )


def failures(report: pd.DataFrame, check: str) -> pd.DataFrame:
    return report[(report["check"] == check) & ~report["passed"]]


def test_clean_data_passes_all_error_checks(fake_root: Path) -> None:
    report = report_for(fake_root)
    assert tuple(report.columns) == REPORT_COLUMNS
    assert not has_errors(report)
    # 2020 (3 cancelled rounds) and two missing semifinal2 files are warnings, not errors
    assert len(failures(report, "round_coverage")) == 5


def test_detects_corrupted_ballot(fake_root: Path, edit_round) -> None:
    def corrupt(d):
        jury = d["performances"][1]["scores"][2]  # BB's jury score
        voter = next(v for v, p in jury["votes"].items() if p == 1)
        jury["votes"][voter] = 2  # voter now gives 2 twice and 1 never

    edit_round(2019, "final", corrupt)
    report = report_for(fake_root)
    bad = failures(report, "ballot_points_set")
    assert len(bad) == 1
    assert bad.iloc[0][["year", "round", "vote_type"]].tolist() == [2019, "final", "jury"]
    # the raw points field and the combined total no longer agree either
    assert not failures(report, "receiver_totals_match_raw").empty
    assert not failures(report, "jury_plus_televote_equals_combined").empty
    assert has_errors(report)


def test_detects_self_vote(fake_root: Path, edit_round) -> None:
    edit_round(2019, "final", lambda d: d["performances"][0]["scores"][2]["votes"].update(AA=0))
    bad = failures(report_for(fake_root), "no_self_votes")
    assert bad[["voter", "receiver"]].to_numpy().tolist() == [["AA", "AA"]]


def test_detects_unknown_code_and_jury_wld(fake_root: Path) -> None:
    b = build_tidy(fake_root, YEARS)
    votes = b.votes.copy()
    votes.loc[votes.index[0], "voter"] = "ZZ"
    wld_jury = votes[votes.voter == "WLD"].head(1).assign(vote_type="jury")
    votes = pd.concat([votes, wld_jury], ignore_index=True)
    details = failures(report_for(fake_root, votes), "known_codes")["detail"].tolist()
    assert any("unknown voter code ZZ" in d for d in details)
    assert any("non-country voter WLD in a jury vote" in d for d in details)


def test_detects_duplicate_keys_and_schema(fake_root: Path) -> None:
    b = build_tidy(fake_root, YEARS)
    votes = pd.concat([b.votes, b.votes.head(1)], ignore_index=True)
    votes.loc[votes.index[1], "points"] = 9  # not on the single-channel scale
    report = report_for(fake_root, votes)
    assert len(failures(report, "unique_keys")) == 1
    assert not failures(report, "schema").empty


def test_detects_missing_explicit_zero(fake_root: Path) -> None:
    b = build_tidy(fake_root, YEARS)
    zero = b.votes[(b.votes.points == 0) & (b.votes.vote_type == "jury")].index[0]
    bad = failures(report_for(fake_root, b.votes.drop(index=zero)), "complete_ballots")
    assert len(bad) == 1


def test_identical_channels_warning(fake_root: Path) -> None:
    b = build_tidy(fake_root, YEARS)
    votes = b.votes.copy()
    key = (votes.year == 2019) & (votes["round"] == "final") & (votes.voter == "FF")
    jury = votes[key & (votes.vote_type == "jury")].set_index("receiver")["points"]
    tele = key & (votes.vote_type == "televote")
    votes.loc[tele, "points"] = votes.loc[tele, "receiver"].map(jury).to_numpy()
    bad = failures(report_for(fake_root, votes), "identical_jury_televote_ballot")
    assert bad["voter"].tolist() == ["FF"]


def test_summary_is_deterministic_markdown(fake_root: Path) -> None:
    report = report_for(fake_root)
    s = summarise(report)
    assert set(s["status"]) <= {"pass", "FAIL"}
    md1 = summary_markdown(report, {"raw_sha256": "abc"})
    md2 = summary_markdown(report_for(fake_root), {"raw_sha256": "abc"})
    assert md1 == md2
    assert "| ballot_points_set | error | pass |" in md1


@pytest.mark.parametrize("check", ["ballot_points_set", "no_self_votes", "schema"])
def test_every_check_reports_a_pass_row(fake_root: Path, check: str) -> None:
    rows = report_for(fake_root).query("check == @check")
    assert rows["passed"].all() and len(rows) == 1
