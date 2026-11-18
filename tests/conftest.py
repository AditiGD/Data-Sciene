"""Shared fixtures: a tiny synthetic raw dataset in the real EurovisionAPI layout.

The fake contest uses 3-2-1 ballots (instead of 12-10-8...1) so that a handful of
countries suffices. Votes are written *sparsely* (zeros omitted) so the tests prove
that :mod:`esc_bias.io` creates the explicit zeros itself.

Fake dataset
------------
countries: AA BB CC DD EE FF (WLD is a voter but, as in the real data, not a country)

2019 final       performers AA BB CC DD EE ; jury/public voters AA..FF ; total = jury+public
2019 semifinal1  performers AA BB CC DD    ; jury/public voters AA..EE
2020 all rounds  performances: null (cancelled)
2023 final       performers AA BB CC DD EE ; jury AA..FF ; public AA..FF + WLD
2023 semifinal1  performers BB CC DD EE    ; only `total` (televote-only), voters BB..FF + WLD
2019 semifinal2, 2023 semifinal2  file missing
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("MPLBACKEND", "Agg")

FAKE_BALLOT = (3, 2, 1)
COUNTRIES = {c: f"Country {c}" for c in ("AA", "BB", "CC", "DD", "EE", "FF")}
ALL = ["AA", "BB", "CC", "DD", "EE", "FF"]

# (year, round) -> performers, {score name: voters}; None = cancelled
ROUNDS: dict[tuple[int, str], tuple[list[str], dict[str, list[str]]] | None] = {
    (2019, "final"): (ALL[:5], {"jury": ALL, "public": ALL}),
    (2019, "semifinal1"): (ALL[:4], {"jury": ALL[:5], "public": ALL[:5]}),
    (2020, "final"): None,
    (2020, "semifinal1"): None,
    (2020, "semifinal2"): None,
    (2023, "final"): (ALL[:5], {"jury": ALL, "public": [*ALL, "WLD"]}),
    (2023, "semifinal1"): (ALL[1:5], {"televote_only": [*ALL[1:], "WLD"]}),
}


def fake_ballot(voter: str, channel: str, performers: list[str]) -> dict[str, int]:
    """Deterministic 3-2-1 ballot of ``voter`` over the performers (never itself)."""
    eligible = [p for p in performers if p != voter]
    salt = {"jury": 5, "public": 2, "televote_only": 3}[channel]
    ranked = sorted(eligible, key=lambda r: ((ord(r[0]) * 3 + ord(voter[0]) * salt) % 11, r))
    if channel == "public":
        ranked = ranked[::-1]  # make jury and televote ballots differ
    return dict(zip(ranked, FAKE_BALLOT, strict=False))


def round_json(
    performers: list[str], channels: dict[str, list[str]], ids: dict[str, int]
) -> dict[str, Any]:
    """Raw round JSON in the dataset's schema (sparse votes: zeros omitted)."""
    received: dict[str, dict[str, dict[str, int]]] = {p: {} for p in performers}
    for channel, voters in channels.items():
        for v in voters:
            for r, pts in fake_ballot(v, channel, performers).items():
                received[r].setdefault(channel, {})[v] = pts
    perfs = []
    for i, p in enumerate(performers):
        scores = []
        if "televote_only" in channels:
            votes = received[p].get("televote_only", {})
            scores.append({"name": "total", "points": sum(votes.values()), "votes": votes})
        else:
            jury, public = received[p].get("jury", {}), received[p].get("public", {})
            total = {v: jury.get(v, 0) + public.get(v, 0) for v in set(jury) | set(public)}
            for name, votes in (("total", total), ("public", public), ("jury", jury)):
                scores.append({"name": name, "points": sum(votes.values()), "votes": votes})
        perfs.append({"contestantId": ids[p], "running": i + 1, "place": None, "scores": scores})
    # places by total points
    order = sorted(perfs, key=lambda q: -q["scores"][0]["points"])
    for place, q in enumerate(order, start=1):
        q["place"] = place
    return {"date": "2000-01-01", "time": "20:00:00", "disqualifieds": None, "performances": perfs}


def write_fake_dataset(root: Path) -> Path:
    """Write the fake dataset under ``root`` and return ``root``."""
    data = root / "data"
    (data / "senior").mkdir(parents=True)
    (data / "countries.json").write_text(json.dumps(COUNTRIES), encoding="utf-8")
    for year in sorted({y for y, _ in ROUNDS}):
        ydir = data / "senior" / str(year)
        (ydir / "rounds").mkdir(parents=True)
        performers = sorted({p for (y, _), v in ROUNDS.items() if y == year and v for p in v[0]})
        if not performers:
            performers = ALL[:3]
        ids = {p: i for i, p in enumerate(performers)}
        for p, i in ids.items():
            cdir = ydir / "contestants" / f"{i}_{p.lower()}"
            cdir.mkdir(parents=True)
            (cdir / "contestant.json").write_text(
                json.dumps({"id": i, "country": p}), encoding="utf-8"
            )
        for (y, rnd), spec in ROUNDS.items():
            if y != year:
                continue
            payload = (
                {
                    "date": "2020-05-16",
                    "time": "19:00:00",
                    "disqualifieds": None,
                    "performances": None,
                }
                if spec is None
                else round_json(spec[0], spec[1], ids)
            )
            (ydir / "rounds" / f"{rnd}.json").write_text(
                json.dumps(payload, indent=1), encoding="utf-8"
            )
    return root


@pytest.fixture
def fake_root(tmp_path: Path) -> Path:
    """Path to a freshly written fake raw dataset."""
    return write_fake_dataset(tmp_path / "raw")


@pytest.fixture
def edit_round(fake_root: Path) -> Callable[[int, str, Callable[[dict[str, Any]], None]], None]:
    """Apply an in-place edit to one round JSON of the fake dataset (for corruption tests)."""

    def _edit(year: int, rnd: str, fn: Callable[[dict[str, Any]], None]) -> None:
        path = fake_root / "data" / "senior" / str(year) / "rounds" / f"{rnd}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        fn(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    return _edit


@pytest.fixture
def fake_config(tmp_path: Path, fake_root: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A config YAML pointing at the fake dataset, with outputs under ``tmp_path``.

    ``ESC_DATA_ROOT`` is unset so that a real-data setting cannot leak into these tests.
    """
    monkeypatch.delenv("ESC_DATA_ROOT", raising=False)
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    src_register = Path(__file__).resolve().parents[1] / "config" / "anomaly_register.csv"
    (repo / "config" / "anomaly_register.csv").write_text(
        src_register.read_text(encoding="utf-8"), encoding="utf-8"
    )
    cfg = repo / "config" / "config.yaml"
    cfg.write_text(
        f"""
data: {{raw_root: {fake_root}, contest: senior, expected_commit: null}}
scope: {{years: [2019, 2020, 2023], rounds: [final, semifinal1, semifinal2]}}
rules: {{televote_only_semis_from: 2023, non_country_voters: [WLD], ballot_points: [3, 2, 1]}}
seeds: {{global: 1, n_permutations: 99}}
paths: {{processed: data/processed, reports: reports, figures: reports/figures,
         interim: data/interim, anomaly_register: config/anomaly_register.csv}}
""",
        encoding="utf-8",
    )
    yield cfg


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip ``@pytest.mark.rawdata`` tests unless ESC_DATA_ROOT points at the dataset."""
    root = os.environ.get("ESC_DATA_ROOT")
    if root and (Path(root) / "data" / "countries.json").is_file():
        return
    skip = pytest.mark.skip(reason="set ESC_DATA_ROOT to the raw dataset clone to run")
    for item in items:
        if "rawdata" in item.keywords:
            item.add_marker(skip)
