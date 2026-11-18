"""Configuration loading."""

from __future__ import annotations

from pathlib import Path

from esc_bias.config import DEFAULT_CONFIG_PATH, PROJECT_ROOT, load_config


def test_default_config_loads() -> None:
    cfg = load_config(env={})
    assert cfg.config_path == DEFAULT_CONFIG_PATH
    assert cfg.years[0] == 2016 and cfg.years[-1] == 2025
    assert cfg.rounds == ("final", "semifinal1", "semifinal2")
    assert cfg.ballot_points == (12, 10, 8, 7, 6, 5, 4, 3, 2, 1)
    assert cfg.raw_root == PROJECT_ROOT / "data" / "raw" / "eurovision-dataset"
    assert cfg.processed_dir == PROJECT_ROOT / "data" / "processed"
    assert cfg.expected_commit == "1f39f6b238b94f2806694a08607998258ed8a41e"
    assert cfg.source_url == "https://github.com/Graph-Drawing-Contest/eurovision-dataset"


def test_env_overrides_data_root(tmp_path: Path) -> None:
    cfg = load_config(env={"ESC_DATA_ROOT": str(tmp_path)})
    assert cfg.raw_root == tmp_path


def test_relative_paths_resolve_against_config_repo(fake_config: Path) -> None:
    cfg = load_config(fake_config, env={})
    repo = fake_config.parent.parent
    assert cfg.processed_dir == repo / "data" / "processed"
    assert cfg.ballot_points == (3, 2, 1)
    assert cfg.expected_commit is None
