"""Command-line entry points.

    esc-bias build-data [--config PATH] [--data-root PATH] [--include-holdout]
    esc-bias validate   [--config PATH] [--strict]

``build-data`` reads the raw dataset and writes to ``data/processed/``:

* ``votes.parquet``           tidy vote table (+ anomaly columns), provenance embedded
* ``receiver_totals.parquet`` the raw ``points`` field per receiver (for validation)
* ``rounds.parquet``          manifest of requested rounds and their status
* ``countries.parquet``       code -> name lookup
* ``metadata.json``           provenance: raw path, raw git commit, SHA-256, code version

``validate`` reads those files and writes ``reports/validation_report.csv`` (one row
per check or failing record), ``reports/validation_summary.md`` and, if any ballot
fails, ``reports/anomaly_candidates.csv``. Failing checks are reported, not fatal,
unless ``--strict`` is given.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from esc_bias import __version__
from esc_bias.anomalies import (
    apply_register,
    candidates_from_report,
    load_register,
    register_coverage,
)
from esc_bias.config import PROJECT_ROOT, Config, load_config
from esc_bias.io import build_tidy, git_commit, read_parquet_metadata, write_parquet
from esc_bias.validate import has_errors, run_all_checks, summarise, summary_markdown

log = logging.getLogger("esc_bias")

VOTES_FILE = "votes.parquet"
TOTALS_FILE = "receiver_totals.parquet"
ROUNDS_FILE = "rounds.parquet"
COUNTRIES_FILE = "countries.parquet"
METADATA_FILE = "metadata.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cmd_build_data(cfg: Config, include_holdout: bool = False) -> dict[str, Any]:
    """Build the processed tables from the raw dataset; return the metadata written."""
    years = sorted(set(cfg.years) | (set(cfg.holdout_years) if include_holdout else set()))
    log.info("reading raw data from %s (years %s-%s)", cfg.raw_root, years[0], years[-1])
    build = build_tidy(
        cfg.raw_root,
        years,
        cfg.rounds,
        cfg.contest,
        cfg.televote_only_semis_from,
        cfg.non_country_voters,
        cfg.jury_exponential_from,
    )
    commit = build.provenance["raw_git_commit"]
    if cfg.expected_commit and commit != cfg.expected_commit:
        log.warning(
            "raw data commit %s differs from expected_commit %s in %s",
            commit,
            cfg.expected_commit,
            cfg.config_path,
        )
    register = load_register(cfg.anomaly_register)
    votes = apply_register(build.votes, register)
    coverage = register_coverage(votes, register)

    metadata: dict[str, Any] = {
        **build.provenance,
        "raw_source_url": cfg.source_url,
        "expected_commit": cfg.expected_commit,
        "commit_matches_expected": commit == cfg.expected_commit,
        "anomaly_register": str(cfg.anomaly_register.relative_to(PROJECT_ROOT))
        if cfg.anomaly_register.is_relative_to(PROJECT_ROOT)
        else str(cfg.anomaly_register),
        "anomaly_register_sha256": _sha256(cfg.anomaly_register),
        "anomaly_register_coverage": coverage.to_dict(orient="records"),
        "code_version": __version__,
        "code_git_commit": git_commit(PROJECT_ROOT),
        "n_rows": len(votes),
    }
    out = cfg.processed_dir
    write_parquet(votes, out / VOTES_FILE, metadata)
    write_parquet(build.receiver_totals, out / TOTALS_FILE, metadata)
    write_parquet(build.rounds, out / ROUNDS_FILE, metadata)
    countries = pd.DataFrame(sorted(build.countries.items()), columns=["code", "name"])
    write_parquet(countries, out / COUNTRIES_FILE, metadata)
    (out / METADATA_FILE).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    log.info("wrote %d rows to %s", len(votes), out / VOTES_FILE)
    return metadata


def row_counts(votes: pd.DataFrame) -> pd.DataFrame:
    """Rows and voter counts per (year, round) and vote type, for the summary."""
    g = votes.groupby(["year", "round", "vote_type"])
    counts = pd.DataFrame(
        {"n_voters": g["voter"].nunique(), "n_receivers": g["receiver"].nunique(), "rows": g.size()}
    ).reset_index()
    wide = counts.pivot_table(
        index=["year", "round"], columns="vote_type", values="n_voters", aggfunc="first"
    )
    wide = wide.reindex(columns=[c for c in ("jury", "televote", "combined") if c in wide.columns])
    wide.columns = [f"voters_{c}" for c in wide.columns]
    per_round = counts.groupby(["year", "round"]).agg(
        performers=("n_receivers", "max"), rows=("rows", "sum")
    )
    table = per_round.join(wide).reset_index()
    return table.astype({c: "Int64" for c in table.columns if c.startswith("voters_")})


def cmd_validate(cfg: Config) -> pd.DataFrame:
    """Validate the processed tables and write the reports; return the report."""
    proc = cfg.processed_dir
    if not (proc / VOTES_FILE).is_file():
        raise FileNotFoundError(f"{proc / VOTES_FILE} not found: run `esc-bias build-data` first")
    votes = pd.read_parquet(proc / VOTES_FILE)
    totals = pd.read_parquet(proc / TOTALS_FILE)
    rounds = pd.read_parquet(proc / ROUNDS_FILE)
    countries_df = pd.read_parquet(proc / COUNTRIES_FILE)
    countries = dict(zip(countries_df["code"], countries_df["name"], strict=True))
    meta = read_parquet_metadata(proc / VOTES_FILE)

    report = run_all_checks(
        votes, totals, countries, rounds, cfg.ballot_points, cfg.non_country_voters
    )
    reports = cfg.reports_dir
    reports.mkdir(parents=True, exist_ok=True)
    report.to_csv(reports / "validation_report.csv", index=False)
    provenance = {
        k: meta.get(k)
        for k in ("raw_source_url", "raw_git_commit", "raw_sha256", "years", "n_rows")
    }
    md = summary_markdown(report, provenance, row_counts(votes))
    (reports / "validation_summary.md").write_text(md, encoding="utf-8")

    candidates = candidates_from_report(report)
    cand_path = reports / "anomaly_candidates.csv"
    if not candidates.empty:
        candidates.to_csv(cand_path, index=False)
        log.warning("%d anomaly candidates written to %s", len(candidates), cand_path)
    elif cand_path.exists():
        cand_path.unlink()

    for row in summarise(report).itertuples(index=False):
        log.info("%-36s %-7s %-4s %d", row.check, row.severity, row.status, row.n_failures)
    return report


def build_parser() -> argparse.ArgumentParser:
    """Argument parser for ``esc-bias``."""
    parser = argparse.ArgumentParser(prog="esc-bias", description=__doc__.split("\n")[0])
    parser.add_argument("--config", type=Path, default=None, help="config YAML")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build-data", help="raw JSON -> data/processed/*.parquet")
    b.add_argument("--data-root", type=Path, default=None, help="overrides ESC_DATA_ROOT")
    b.add_argument("--include-holdout", action="store_true", help="also build holdout_years")
    v = sub.add_parser("validate", help="data contract + ballot integrity -> reports/")
    v.add_argument("--strict", action="store_true", help="exit 1 if an error-level check fails")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    env = None
    if getattr(args, "data_root", None) is not None:
        env = {"ESC_DATA_ROOT": str(args.data_root)}
    cfg = load_config(args.config, env=env)
    if args.command == "build-data":
        cmd_build_data(cfg, include_holdout=args.include_holdout)
        return 0
    report = cmd_validate(cfg)
    if args.strict and has_errors(report):
        log.error("error-level checks failed (see %s)", cfg.reports_dir)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
