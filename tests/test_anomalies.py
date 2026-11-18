"""Anomaly register loading and application."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from esc_bias.anomalies import (
    apply_register,
    candidates_from_report,
    load_register,
    register_coverage,
)
from esc_bias.config import PROJECT_ROOT
from esc_bias.io import build_tidy

HEADER = "anomaly_id,year,round,vote_type,voter,receiver,issue,handling,source_url,notes\n"


def write_register(tmp_path: Path, rows: str) -> Path:
    p = tmp_path / "reg.csv"
    p.write_text("# a comment line\n# another, with a comma\n" + HEADER + rows, encoding="utf-8")
    return p


def test_project_register_is_valid() -> None:
    reg = load_register(PROJECT_ROOT / "config" / "anomaly_register.csv")
    assert {"A06", "A12a", "A13a", "A14", "A15"} <= set(reg["anomaly_id"])
    assert len(reg) >= 26


def test_apply_register_on_fake_data(fake_root: Path) -> None:
    votes = build_tidy(fake_root, (2019, 2020, 2023)).votes
    reg = load_register(PROJECT_ROOT / "config" / "anomaly_register.csv")
    out = apply_register(votes, reg)
    wld = out.voter == "WLD"
    assert out.loc[wld, "exclude"].all() and not out.loc[~wld, "exclude"].any()
    semi23 = (out.year == 2023) & (out["round"] == "semifinal1")
    assert out.loc[semi23, "is_flagged"].all()
    assert out.loc[semi23 & ~wld, "anomaly_ids"].eq("A15").all()
    assert out.loc[semi23 & wld, "anomaly_ids"].eq("A14;A15").all()
    assert not out.loc[out.year == 2019, "is_flagged"].any()
    assert not out["sensitivity"].any()  # fake data has no 2016-17, DK, NL...
    assert len(out) == len(votes)
    cov = register_coverage(out, reg).set_index("anomaly_id")["n_rows"]
    assert cov["A09"] == 0  # 2020 has no rows, but the entry documents the gap


def test_lists_wildcards_and_handlings(tmp_path: Path) -> None:
    reg = load_register(
        write_register(
            tmp_path,
            "X1,2019;2021,final,jury,AA,*,a,exclude,,\nX2,*,*,*,*,BB,b,keep,,\n",
        )
    )
    votes = pd.DataFrame(
        {
            "year": [2019, 2021, 2022, 2019],
            "round": "final",
            "vote_type": ["jury", "jury", "jury", "televote"],
            "voter": ["AA", "AA", "AA", "AA"],
            "receiver": ["BB", "CC", "BB", "CC"],
        }
    )
    out = apply_register(votes, reg)
    assert out["exclude"].tolist() == [True, True, False, False]
    assert out["is_flagged"].tolist() == [True, True, False, False]  # keep does not flag
    assert out["anomaly_ids"].tolist() == ["X1", "X1", "", ""]  # keep entries not listed


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ("X1,2019,final,jury,AA,*,a,drop,,\n", "unknown handling"),
        ("X1,2019,final,jury,AA,*,a,flag,,\nX1,2019,final,jury,BB,*,a,flag,,\n", "duplicate"),
    ],
)
def test_invalid_register_rejected(tmp_path: Path, rows: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_register(write_register(tmp_path, rows))


def test_missing_columns_rejected(tmp_path: Path) -> None:
    p = tmp_path / "r.csv"
    p.write_text("anomaly_id,year\nX,2019\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        load_register(p)


def test_candidates_from_report() -> None:
    report = pd.DataFrame(
        {
            "check": ["ballot_points_set", "schema", "ballot_points_set"],
            "severity": "error",
            "passed": [False, False, True],
            "year": pd.array([2019, 2019, pd.NA], dtype="Int64"),
            "round": ["final", "final", pd.NA],
            "vote_type": ["jury", "jury", pd.NA],
            "voter": ["AA", "AA", pd.NA],
            "receiver": pd.NA,
            "detail": ["awarded [..]", "x", ""],
        }
    )
    cand = candidates_from_report(report)
    assert cand[["year", "voter", "issue", "handling"]].to_numpy().tolist() == [
        ["2019", "AA", "ballot_points_set", "flag"]
    ]
