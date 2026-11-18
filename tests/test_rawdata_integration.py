"""Integration tests on the real dataset (``ESC_DATA_ROOT`` must be set).

Run with::

    ESC_DATA_ROOT=/path/to/eurovision-dataset uv run pytest -m rawdata

Exact counts are asserted only when the clone is at the pinned commit in
``config/config.yaml``; on another commit those asserts are skipped, the integrity
checks still run.
"""

from __future__ import annotations

import pytest

from esc_bias.anomalies import apply_register, load_register
from esc_bias.config import load_config
from esc_bias.io import build_tidy
from esc_bias.validate import run_all_checks, summarise

pytestmark = pytest.mark.rawdata


@pytest.fixture(scope="module")
def real():
    cfg = load_config()
    build = build_tidy(
        cfg.raw_root,
        cfg.years,
        cfg.rounds,
        cfg.contest,
        cfg.televote_only_semis_from,
        cfg.non_country_voters,
        cfg.jury_exponential_from,
    )
    votes = apply_register(build.votes, load_register(cfg.anomaly_register))
    report = run_all_checks(votes, build.receiver_totals, build.countries, build.rounds)
    return cfg, build, votes, report


def test_all_error_level_checks_pass(real) -> None:
    *_, report = real
    s = summarise(report)
    failing = s[(s.severity == "error") & (s.status == "FAIL")]
    assert failing.empty, failing.to_string()


def test_round_manifest(real) -> None:
    _, build, _, _ = real
    status = build.rounds["status"].value_counts().to_dict()
    assert status == {"ok": 27, "cancelled": 3}


def test_vote_type_mapping_on_real_data(real) -> None:
    _, _, votes, _ = real
    semis_23 = votes[(votes.year >= 2023) & votes["round"].str.startswith("semifinal")]
    assert set(semis_23.vote_type) == {"televote"}
    assert set(semis_23.vote_type_source) == {"total"}
    wld = votes[votes.voter == "WLD"]
    assert set(wld.vote_type) == {"televote", "combined"}
    assert wld.year.min() == 2023


def test_voter_counts_2023_plus_finals(real) -> None:
    _, _, votes, _ = real
    f = votes[(votes.year >= 2023) & (votes["round"] == "final")]
    n = f.groupby(["year", "vote_type"]).voter.nunique().unstack()
    assert (n["jury"] == 37).all() and (n["televote"] == 38).all()


def test_pinned_commit_counts(real) -> None:
    cfg, build, votes, _ = real
    if build.provenance["raw_git_commit"] != cfg.expected_commit:
        pytest.skip("raw data is not at the pinned commit")
    assert len(votes) == 41_350
    assert votes.groupby("vote_type").size().to_dict() == {
        "combined": 13_235,
        "jury": 13_158,
        "televote": 14_957,
    }
    single = votes[votes.vote_type != "combined"]
    ballots = single.groupby("vote_type")[["year", "round", "voter"]].apply(
        lambda g: len(g.drop_duplicates())
    )
    assert ballots.to_dict() == {"jury": 605, "televote": 725}
    assert build.provenance["raw_sha256"] == (
        "1a444e54e8de5e693db9a2209f11f1bb30a8045ec622bceed0fc6a783eec46b1"
    )


def test_anomaly_register_on_real_data(real) -> None:
    cfg, build, votes, _ = real
    if build.provenance["raw_git_commit"] != cfg.expected_commit:
        pytest.skip("raw data is not at the pinned commit")

    def n(anomaly_id: str) -> int:
        return int(votes["anomaly_ids"].str.split(";").map(lambda ids: anomaly_id in ids).sum())

    assert n("A06") == 50  # BY 2019 final substitute jury: 25 jury + 25 combined cells
    assert n("A12a") == 249  # 2022 six substitute juries, SF2 + final, jury cells
    assert n("A14") == 247  # WLD televote + combined
    assert n("A15") == 1722  # 2023-25 televote-only semis
    assert set(
        votes.loc[votes.voter == "SM", "exclude"].groupby(votes.vote_type).all().items()
    ) == {
        ("combined", True),
        ("jury", False),
        ("televote", True),
    }
    # 1248 + 52 (A02: 2016 DK final jury + combined, 26 receivers; excluded since design v2.1)
    assert int(votes["exclude"].sum()) == 1300
