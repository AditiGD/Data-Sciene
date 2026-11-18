"""Raw JSON -> tidy table."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from esc_bias.io import (
    KEY_COLUMNS,
    TIDY_COLUMNS,
    build_tidy,
    git_commit,
    map_vote_type,
    read_json,
    read_parquet_metadata,
    write_parquet,
)

YEARS = (2019, 2020, 2023)


@pytest.fixture
def build(fake_root: Path):
    return build_tidy(fake_root, YEARS)


def test_columns_and_unique_keys(build) -> None:
    assert tuple(build.votes.columns) == TIDY_COLUMNS
    assert not build.votes.duplicated(list(KEY_COLUMNS)).any()


def test_explicit_zeros_for_every_eligible_pair(build) -> None:
    v = build.votes
    jury = v[(v.year == 2019) & (v["round"] == "final") & (v.vote_type == "jury")]
    # 6 voters x 5 performers - 5 self pairs
    assert len(jury) == 6 * 5 - 5
    per_ballot = jury.groupby("voter")["points"].agg(lambda s: sorted(s, reverse=True))
    assert per_ballot["FF"] == [3, 2, 1, 0, 0]  # FF does not perform: 5 receivers
    assert per_ballot["AA"] == [3, 2, 1, 0]  # AA performs: 4 receivers
    assert (v["voter"] != v["receiver"]).all()


def test_voter_performs_and_jury_method(build) -> None:
    v = build.votes
    sf = v[(v.year == 2019) & (v["round"] == "semifinal1")]
    assert not sf.loc[sf.voter == "EE", "voter_performs_in_round"].any()  # votes, no song
    assert sf.loc[sf.voter == "AA", "voter_performs_in_round"].all()
    assert set(v.loc[v.year == 2019, "jury_method"].dropna()) == {"exponential_weight"}
    assert v.loc[v.vote_type == "televote", "jury_method"].isna().all()
    assert v.loc[(v.year == 2019) & (v.vote_type == "combined"), "jury_method"].notna().all()


def test_absent_receiver_has_no_rows(build) -> None:
    v = build.votes
    final = v[(v.year == 2019) & (v["round"] == "final")]
    assert "FF" not in set(final.receiver)  # FF votes but does not perform: missing, not 0


def test_vote_type_mapping(build) -> None:
    v = build.votes
    final = v[(v.year == 2019) & (v["round"] == "final")]
    assert set(zip(final.vote_type, final.vote_type_source, strict=True)) == {
        ("jury", "jury"),
        ("televote", "public"),
        ("combined", "total"),
    }


def test_2023_semifinal_total_is_televote(build) -> None:
    sf = build.votes[(build.votes.year == 2023) & (build.votes["round"] == "semifinal1")]
    assert set(sf.vote_type) == {"televote"}
    assert set(sf.vote_type_source) == {"total"}
    assert "WLD" in set(sf.voter)


def test_wld_is_not_a_country(build) -> None:
    v = build.votes
    assert not v.loc[v.voter == "WLD", "voter_is_country"].any()
    assert v.loc[v.voter != "WLD", "voter_is_country"].all()
    assert set(v.loc[v.voter == "WLD", "vote_type"]) == {"televote", "combined"}


def test_cancelled_and_missing_rounds_are_recorded_not_fatal(build) -> None:
    assert 2020 not in set(build.votes.year)
    status = build.rounds.set_index(["year", "round"])["status"]
    assert (status.loc[2020] == "cancelled").all()
    assert status.loc[(2023, "semifinal2")] == "missing"
    assert status.loc[(2019, "final")] == "ok"


def test_receiver_totals_and_place(build) -> None:
    t = build.receiver_totals
    assert set(t.columns) == {"year", "round", "vote_type", "receiver", "raw_points"}
    assert build.votes["receiver_place"].notna().all()


def test_provenance_without_git(build) -> None:
    assert build.provenance["raw_git_commit"] is None
    assert len(build.provenance["raw_sha256"]) == 64


def test_fingerprint_changes_with_content(fake_root: Path, edit_round) -> None:
    before = build_tidy(fake_root, YEARS).provenance["raw_sha256"]
    edit_round(2019, "final", lambda d: d.update(date="1999-01-01"))
    assert build_tidy(fake_root, YEARS).provenance["raw_sha256"] != before


def test_map_vote_type_rules() -> None:
    assert map_vote_type("total", {"total"}, 2023, "semifinal1") == "televote"
    assert map_vote_type("total", {"total"}, 2023, "final") == "combined"
    assert map_vote_type("total", {"total"}, 2015, "semifinal1") == "combined"
    assert map_vote_type("total", {"total", "jury", "public"}, 2026, "semifinal1") == "combined"
    assert map_vote_type("tele", {"tele"}, 2016, "final") == "televote"
    with pytest.raises(ValueError, match="unknown score name"):
        map_vote_type("sms", {"sms"}, 2016, "final")


def test_duplicate_json_keys_rejected(tmp_path: Path) -> None:
    f = tmp_path / "x.json"
    f.write_text('{"AA": 1, "AA": 2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON keys"):
        read_json(f)


def test_raw_self_vote_is_kept_for_validation(fake_root: Path, edit_round) -> None:
    def add_self_vote(d):
        p = d["performances"][0]  # contestant 0 = AA
        p["scores"][2]["votes"]["AA"] = 5  # jury

    edit_round(2019, "final", add_self_vote)
    v = build_tidy(fake_root, YEARS).votes
    assert ((v.voter == "AA") & (v.receiver == "AA") & (v.vote_type == "jury")).sum() == 1


def test_git_commit_reads_refs(tmp_path: Path) -> None:
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n")
    (git / "refs" / "heads" / "main").write_text("abc123\n")
    assert git_commit(tmp_path) == "abc123"
    (git / "refs" / "heads" / "main").unlink()
    (git / "packed-refs").write_text("# pack-refs\ndef456 refs/heads/main\n")
    assert git_commit(tmp_path) == "def456"
    (git / "HEAD").write_text("fff999\n")
    assert git_commit(tmp_path) == "fff999"


def test_parquet_roundtrip_keeps_metadata_and_dtypes(build, tmp_path: Path) -> None:
    path = write_parquet(build.votes, tmp_path / "v.parquet", {"raw_sha256": "x"})
    back = pd.read_parquet(path)
    assert read_parquet_metadata(path) == {"raw_sha256": "x"}
    assert str(back["receiver_place"].dtype) == "Int64"
    pd.testing.assert_frame_equal(back, build.votes, check_dtype=False)


def test_not_a_dataset(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="ESC_DATA_ROOT"):
        build_tidy(tmp_path, YEARS)
