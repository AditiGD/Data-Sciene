"""Raw Eurovision dataset JSON -> one tidy long table of votes.

Source: the course dataset (Graph-Drawing-Contest/eurovision-dataset, a fork of
EurovisionAPI/dataset with the same schema).

Raw layout (see the dataset README)::

    <raw_root>/data/countries.json
    <raw_root>/data/<contest>/<year>/contestants/<NN>_<cc>/contestant.json   (id, country)
    <raw_root>/data/<contest>/<year>/rounds/{final,semifinal1,semifinal2}.json

Output: one row per (year, round, vote_type, voter, receiver) **including explicit
zeros** for every eligible pair (every voter seen in that round and vote type x every
performer, excluding self). Zeros matter: a ballot is a ranking, and a model that only
sees non-zero points cannot learn who was *not* ranked.

Safety: the raw data is untrusted. It is only ever parsed with :func:`json.load`; no
code from the dataset is imported or executed, and the git commit is read from the
``.git`` folder as plain text instead of by running ``git`` inside the clone.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

log = logging.getLogger(__name__)

ROUND_ORDER: tuple[str, ...] = ("final", "semifinal1", "semifinal2")
VOTE_TYPE_ORDER: tuple[str, ...] = ("jury", "televote", "combined")

#: Raw score name -> analysis vote type. ``tele`` is the name used in the dataset README;
#: the data itself uses ``public``. Both are accepted.
SCORE_NAME_TO_VOTE_TYPE: dict[str, str] = {
    "jury": "jury",
    "public": "televote",
    "tele": "televote",
    "total": "combined",
}

TIDY_COLUMNS: tuple[str, ...] = (
    "year",
    "round",
    "vote_type",
    "voter",
    "receiver",
    "points",
    "receiver_place",
    "receiver_running",
    "vote_type_source",
    "voter_is_country",
    "voter_performs_in_round",
    "jury_method",
)

#: How national jurors' rankings were aggregated into the jury ballot (data audit #5).
JURY_METHODS: tuple[str, ...] = ("average_rank", "exponential_weight")
KEY_COLUMNS: tuple[str, ...] = ("year", "round", "vote_type", "voter", "receiver")


# --------------------------------------------------------------------------- reading
def read_json(path: Path) -> Any:
    """Parse a JSON file, refusing duplicate object keys (they would silently overwrite)."""

    def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [k for k, _ in pairs]
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        if dupes:
            raise ValueError(f"duplicate JSON keys {dupes} in {path}")
        return dict(pairs)

    with path.open(encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=_no_duplicates)


def load_countries(raw_root: Path) -> dict[str, str]:
    """Return the country-code -> country-name lookup (``data/countries.json``)."""
    data = read_json(raw_root / "data" / "countries.json")
    return {str(k): str(v) for k, v in data.items()}


def load_contestants(year_dir: Path) -> dict[int, str]:
    """Map contestant id -> country code for one contest year."""
    out: dict[int, str] = {}
    for cfile in sorted((year_dir / "contestants").glob("*/contestant.json")):
        c = read_json(cfile)
        cid = int(c["id"])
        if cid in out:
            raise ValueError(f"duplicate contestant id {cid} in {year_dir}")
        out[cid] = str(c["country"])
    return out


# --------------------------------------------------------------------------- mapping
def map_vote_type(
    score_name: str,
    score_names_in_round: Iterable[str],
    year: int,
    round_name: str,
    televote_only_semis_from: int = 2023,
) -> str:
    """Translate a raw score name into the analysis vote type.

    ``public``/``tele`` -> ``televote``; ``jury`` -> ``jury``; ``total`` -> ``combined``,
    **except** in a semi-final from ``televote_only_semis_from`` on that reports *only*
    ``total``: those semi-finals had no jury, so ``total`` *is* the televote.

    Raises:
        ValueError: for an unknown score name (a schema change we want to notice).
    """
    if score_name not in SCORE_NAME_TO_VOTE_TYPE:
        raise ValueError(f"unknown score name {score_name!r} ({year} {round_name})")
    only_total = set(score_names_in_round) == {"total"}
    is_semi = round_name.startswith("semifinal")
    if score_name == "total" and only_total and is_semi and year >= televote_only_semis_from:
        return "televote"
    return SCORE_NAME_TO_VOTE_TYPE[score_name]


def _int_or_none(value: Any) -> int | None:
    return None if value is None else int(value)


def round_to_long(
    year: int,
    round_name: str,
    performances: Sequence[dict[str, Any]],
    contestants: dict[int, str],
    televote_only_semis_from: int = 2023,
    non_country_voters: Iterable[str] = ("WLD",),
    jury_exponential_from: int = 2018,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert one round's ``performances`` into (votes, receiver_totals) tables.

    The eligible voters for a vote type are all codes that appear as a key in *any*
    performance's ``votes`` for that score name. Every voter x performer pair (excluding
    self) gets a row; missing pairs get ``points = 0``. A self-vote present in the raw data
    is kept (not silently dropped) so that validation can report it.

    Countries that did not perform in the round (e.g. NL in the 2024 final) get **no**
    receiver rows: an absent receiver is *missing*, not 0 points.

    ``jury_method`` is set on rows that contain a jury ballot (``jury`` and ``combined``
    in rounds with a jury): ``average_rank`` before ``jury_exponential_from``, else
    ``exponential_weight``; ``None`` otherwise.
    """
    non_country = set(non_country_voters)
    names_in_round = {s["name"] for p in performances for s in (p.get("scores") or [])}

    # receiver -> score name -> votes dict / raw points
    perf_rows: list[tuple[str, int | None, int | None, dict[str, dict[str, Any]]]] = []
    for p in performances:
        cid = int(p["contestantId"])
        if cid not in contestants:
            raise KeyError(f"contestantId {cid} not found in contestants ({year} {round_name})")
        scores = {str(s["name"]): s for s in (p.get("scores") or [])}
        perf_rows.append(
            (contestants[cid], _int_or_none(p.get("place")), _int_or_none(p.get("running")), scores)
        )

    performers = {r for r, _, _, _ in perf_rows}
    has_jury = "jury" in names_in_round
    method = JURY_METHODS[0] if year < jury_exponential_from else JURY_METHODS[1]

    vote_records: list[dict[str, Any]] = []
    total_records: list[dict[str, Any]] = []
    for score_name in sorted(names_in_round):
        vote_type = map_vote_type(
            score_name, names_in_round, year, round_name, televote_only_semis_from
        )
        jury_method = method if has_jury and vote_type in ("jury", "combined") else None
        voters = sorted(
            {
                str(v)
                for _, _, _, scores in perf_rows
                if score_name in scores
                for v in (scores[score_name].get("votes") or {})
            }
        )
        for receiver, place, running, scores in perf_rows:
            score = scores.get(score_name)
            votes = {str(k): int(v) for k, v in ((score or {}).get("votes") or {}).items()}
            if score is not None:
                total_records.append(
                    {
                        "year": year,
                        "round": round_name,
                        "vote_type": vote_type,
                        "receiver": receiver,
                        "raw_points": _int_or_none(score.get("points")),
                    }
                )
            for voter in voters:
                if voter == receiver and voter not in votes:
                    continue  # nobody may vote for themselves: not an eligible pair
                vote_records.append(
                    {
                        "year": year,
                        "round": round_name,
                        "vote_type": vote_type,
                        "voter": voter,
                        "receiver": receiver,
                        "points": votes.get(voter, 0),
                        "receiver_place": place,
                        "receiver_running": running,
                        "vote_type_source": score_name,
                        "voter_is_country": voter not in non_country,
                        "voter_performs_in_round": voter in performers,
                        "jury_method": jury_method,
                    }
                )
    return pd.DataFrame.from_records(vote_records), pd.DataFrame.from_records(total_records)


# --------------------------------------------------------------------------- provenance
def git_commit(repo_root: Path) -> str | None:
    """Return the checked-out commit hash of ``repo_root`` by reading ``.git`` as text.

    Handles a detached HEAD, loose refs and ``packed-refs``. Returns ``None`` when the
    folder is not a git clone (e.g. a downloaded zip). Never executes ``git``.
    """
    git_dir = repo_root / ".git"
    head_file = git_dir / "HEAD"
    if not head_file.is_file():
        return None
    head = head_file.read_text(encoding="utf-8").strip()
    if not head.startswith("ref:"):
        return head or None
    ref = head.split(":", 1)[1].strip()
    loose = git_dir / ref
    if loose.is_file():
        return loose.read_text(encoding="utf-8").strip() or None
    packed = git_dir / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0]
    return None


def fingerprint(files: Iterable[Path], root: Path) -> str:
    """SHA-256 over (relative path, bytes) of every raw file read, in sorted order.

    Identifies the exact input bytes even when the data is not a git clone.
    """
    h = hashlib.sha256()
    for f in sorted(set(files)):
        h.update(f.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(f.read_bytes())
    return h.hexdigest()


# --------------------------------------------------------------------------- build
@dataclass
class RawBuild:
    """Everything :func:`build_tidy` produces."""

    votes: pd.DataFrame
    receiver_totals: pd.DataFrame
    rounds: pd.DataFrame  # manifest: one row per requested (year, round) with a status
    countries: dict[str, str]
    provenance: dict[str, Any] = field(default_factory=dict)


def _empty_votes() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in TIDY_COLUMNS})


def _finalise_votes(df: pd.DataFrame) -> pd.DataFrame:
    """Set dtypes and a deterministic row order."""
    if df.empty:
        df = _empty_votes()
    df = df.astype(
        {
            "year": "int64",
            "round": "str",
            "vote_type": "str",
            "voter": "str",
            "receiver": "str",
            "points": "int64",
            "receiver_place": "Int64",
            "receiver_running": "Int64",
            "vote_type_source": "str",
            "voter_is_country": "bool",
            "voter_performs_in_round": "bool",
            "jury_method": "str",
        }
    )
    order = {
        "round": {r: i for i, r in enumerate(ROUND_ORDER)},
        "vote_type": {v: i for i, v in enumerate(VOTE_TYPE_ORDER)},
    }
    sort_keys = df.assign(
        _r=df["round"].map(order["round"]), _v=df["vote_type"].map(order["vote_type"])
    )
    df = sort_keys.sort_values(["year", "_r", "_v", "voter", "receiver"]).drop(columns=["_r", "_v"])
    return df.reset_index(drop=True)[list(TIDY_COLUMNS)]


def build_tidy(
    raw_root: Path,
    years: Iterable[int],
    rounds: Iterable[str] = ROUND_ORDER,
    contest: str = "senior",
    televote_only_semis_from: int = 2023,
    non_country_voters: Iterable[str] = ("WLD",),
    jury_exponential_from: int = 2018,
) -> RawBuild:
    """Read the raw dataset and return the tidy vote table plus side tables.

    Missing years/round files and cancelled rounds (``performances: null``, e.g. 2020)
    do not raise: they are recorded in ``RawBuild.rounds`` with a status and contribute
    no rows.
    """
    raw_root = Path(raw_root).resolve()
    if not (raw_root / "data" / "countries.json").is_file():
        raise FileNotFoundError(
            f"{raw_root} does not look like the Eurovision dataset "
            "(expected data/countries.json). Set ESC_DATA_ROOT or data.raw_root."
        )
    non_country = tuple(non_country_voters)
    files_read: list[Path] = [raw_root / "data" / "countries.json"]
    countries = load_countries(raw_root)

    vote_parts: list[pd.DataFrame] = []
    total_parts: list[pd.DataFrame] = []
    manifest: list[dict[str, Any]] = []
    for year in sorted(set(years)):
        year_dir = raw_root / "data" / contest / str(year)
        contestants = load_contestants(year_dir) if year_dir.is_dir() else {}
        files_read.extend(sorted((year_dir / "contestants").glob("*/contestant.json")))
        for round_name in rounds:
            entry: dict[str, Any] = {
                "year": year,
                "round": round_name,
                "status": "",
                "n_performances": 0,
                "score_names": "",
                "disqualified": "",
            }
            rfile = year_dir / "rounds" / f"{round_name}.json"
            if not rfile.is_file():
                manifest.append({**entry, "status": "missing"})
                log.warning("missing round file %s", rfile)
                continue
            files_read.append(rfile)
            data = read_json(rfile)
            performances = data.get("performances")
            disq = [contestants.get(int(i), f"id:{i}") for i in (data.get("disqualifieds") or [])]
            if not performances:
                manifest.append({**entry, "status": "cancelled"})
                log.info("no performances in %s %s (cancelled)", year, round_name)
                continue
            votes, totals = round_to_long(
                year,
                round_name,
                performances,
                contestants,
                televote_only_semis_from,
                non_country,
                jury_exponential_from,
            )
            vote_parts.append(votes)
            total_parts.append(totals)
            names = sorted({s["name"] for p in performances for s in (p.get("scores") or [])})
            manifest.append(
                {
                    **entry,
                    "status": "ok",
                    "n_performances": len(performances),
                    "score_names": ",".join(names),
                    "disqualified": ",".join(disq),
                }
            )

    votes_df = _finalise_votes(
        pd.concat(vote_parts, ignore_index=True) if vote_parts else _empty_votes()
    )
    totals_df = (
        pd.concat(total_parts, ignore_index=True)
        if total_parts
        else pd.DataFrame(columns=["year", "round", "vote_type", "receiver", "raw_points"])
    )
    manifest_df = pd.DataFrame.from_records(manifest)
    provenance = {
        "raw_root": str(raw_root),
        "raw_git_commit": git_commit(raw_root),
        "raw_sha256": fingerprint(files_read, raw_root),
        "n_raw_files": len(set(files_read)),
        "contest": contest,
        "years": sorted(set(years)),
        "rounds": list(rounds),
    }
    return RawBuild(votes_df, totals_df, manifest_df, countries, provenance)


# --------------------------------------------------------------------------- writing
def write_parquet(df: pd.DataFrame, path: Path, metadata: dict[str, Any] | None = None) -> Path:
    """Write ``df`` to parquet, embedding ``metadata`` as JSON in the file's schema."""
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    if metadata:
        merged = {**(table.schema.metadata or {}), b"esc_bias": json.dumps(metadata).encode()}
        table = table.replace_schema_metadata(merged)
    pq.write_table(table, path)
    return path


def read_parquet_metadata(path: Path) -> dict[str, Any]:
    """Return the ``esc_bias`` metadata embedded by :func:`write_parquet` (or ``{}``)."""
    meta = pq.read_schema(path).metadata or {}
    blob = meta.get(b"esc_bias")
    return json.loads(blob) if blob else {}
