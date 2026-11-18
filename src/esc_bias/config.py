"""Load the project configuration (``config/config.yaml``) with environment overrides.

Usage::

    from esc_bias.config import load_config
    cfg = load_config()          # finds config/config.yaml from the repo root
    cfg.raw_root                 # Path, honours $ESC_DATA_ROOT

Only ``ESC_DATA_ROOT`` is read from the environment; everything else lives in the
YAML file so that a run is fully described by (config file, data commit, code commit).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ENV_DATA_ROOT = "ESC_DATA_ROOT"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


@dataclass(frozen=True)
class Config:
    """Resolved pipeline settings. All paths are absolute."""

    raw_root: Path
    contest: str
    expected_commit: str | None
    source_url: str | None
    upstream_url: str | None
    years: tuple[int, ...]
    holdout_years: tuple[int, ...]
    rounds: tuple[str, ...]
    vote_types: tuple[str, ...]
    televote_only_semis_from: int
    non_country_voters: tuple[str, ...]
    ballot_points: tuple[int, ...]
    jury_exponential_from: int
    seed: int
    n_permutations: int
    interim_dir: Path
    processed_dir: Path
    reports_dir: Path
    figures_dir: Path
    anomaly_register: Path
    config_path: Path
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)


def _resolve(path: str | os.PathLike[str], base: Path) -> Path:
    """Return ``path`` as an absolute path, relative paths being taken from ``base``."""
    p = Path(path).expanduser()
    return p if p.is_absolute() else (base / p).resolve()


def load_config(
    path: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> Config:
    """Read the YAML config and apply environment overrides.

    Args:
        path: YAML file; defaults to ``<repo>/config/config.yaml``.
        env: environment mapping (defaults to ``os.environ``); injectable for tests.

    Returns:
        A frozen :class:`Config` with absolute paths.
    """
    env = os.environ if env is None else env
    config_path = Path(path).resolve() if path is not None else DEFAULT_CONFIG_PATH
    with config_path.open(encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    base = config_path.parent.parent  # repo root = parent of config/
    data, scope, rules = raw.get("data", {}), raw.get("scope", {}), raw.get("rules", {})
    seeds, paths = raw.get("seeds", {}), raw.get("paths", {})

    raw_root = env.get(ENV_DATA_ROOT) or data.get("raw_root", "data/raw/eurovision-dataset")
    return Config(
        raw_root=_resolve(raw_root, base),
        contest=str(data.get("contest", "senior")),
        expected_commit=data.get("expected_commit"),
        source_url=data.get("source_url"),
        upstream_url=data.get("upstream_url"),
        years=tuple(int(y) for y in scope.get("years", range(2016, 2026))),
        holdout_years=tuple(int(y) for y in scope.get("holdout_years", ())),
        rounds=tuple(scope.get("rounds", ("final", "semifinal1", "semifinal2"))),
        vote_types=tuple(scope.get("vote_types", ("jury", "televote", "combined"))),
        televote_only_semis_from=int(rules.get("televote_only_semis_from", 2023)),
        non_country_voters=tuple(rules.get("non_country_voters", ("WLD",))),
        ballot_points=tuple(
            int(p) for p in rules.get("ballot_points", (12, 10, 8, 7, 6, 5, 4, 3, 2, 1))
        ),
        jury_exponential_from=int(rules.get("jury_exponential_from", 2018)),
        seed=int(seeds.get("global", 0)),
        n_permutations=int(seeds.get("n_permutations", 1000)),
        interim_dir=_resolve(paths.get("interim", "data/interim"), base),
        processed_dir=_resolve(paths.get("processed", "data/processed"), base),
        reports_dir=_resolve(paths.get("reports", "reports"), base),
        figures_dir=_resolve(paths.get("figures", "reports/figures"), base),
        anomaly_register=_resolve(
            paths.get("anomaly_register", "config/anomaly_register.csv"), base
        ),
        config_path=config_path,
        raw=raw,
    )
