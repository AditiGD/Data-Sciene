"""End-to-end CLI run on the fake dataset."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from esc_bias.cli import main
from esc_bias.config import load_config
from esc_bias.io import read_parquet_metadata


def test_build_and_validate(fake_config: Path, fake_root: Path) -> None:
    assert main(["--config", str(fake_config), "build-data"]) == 0
    cfg = load_config(fake_config, env={})
    votes = pd.read_parquet(cfg.processed_dir / "votes.parquet")
    assert {"is_flagged", "exclude", "sensitivity", "anomaly_ids"} <= set(votes.columns)
    meta = json.loads((cfg.processed_dir / "metadata.json").read_text())
    assert meta["raw_root"] == str(fake_root)
    assert meta["n_rows"] == len(votes)
    embedded = read_parquet_metadata(cfg.processed_dir / "votes.parquet")
    assert embedded["raw_sha256"] == meta["raw_sha256"]

    assert main(["--config", str(fake_config), "validate", "--strict"]) == 0
    report = pd.read_csv(cfg.reports_dir / "validation_report.csv")
    assert report.loc[report.severity == "error", "passed"].all()
    summary = (cfg.reports_dir / "validation_summary.md").read_text()
    assert "0 failing error-level checks" in summary
    assert not (cfg.reports_dir / "anomaly_candidates.csv").exists()


def test_strict_validate_fails_on_corrupt_ballot(fake_config: Path, edit_round) -> None:
    def corrupt(d):
        d["performances"][0]["scores"][2]["votes"]["FF"] = 7

    edit_round(2019, "final", corrupt)
    assert main(["--config", str(fake_config), "build-data"]) == 0  # never crashes
    assert main(["--config", str(fake_config), "validate"]) == 0  # reports only
    assert main(["--config", str(fake_config), "validate", "--strict"]) == 1
    cfg = load_config(fake_config, env={})
    cand = pd.read_csv(cfg.reports_dir / "anomaly_candidates.csv")
    assert "FF" in set(cand["voter"])


def test_data_root_flag_overrides_config(
    fake_config: Path, fake_root: Path, tmp_path: Path
) -> None:
    other = tmp_path / "copy"
    shutil.copytree(fake_root, other)
    assert main(["--config", str(fake_config), "build-data", "--data-root", str(other)]) == 0
    cfg = load_config(fake_config, env={})
    meta = json.loads((cfg.processed_dir / "metadata.json").read_text())
    assert meta["raw_root"] == str(other)
