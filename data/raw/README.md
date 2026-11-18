# Raw data (not committed)

The raw data is **never** committed to this repository. Fetch it once and point the
pipeline at it.

| | |
|---|---|
| Source (official course dataset) | https://github.com/Graph-Drawing-Contest/eurovision-dataset |
| Pinned commit | `1f39f6b238b94f2806694a08607998258ed8a41e` (2025-12-23, covers up to 2025) |
| Origin | fork of https://github.com/EurovisionAPI/dataset (same schema; 2016–2025 senior files byte-identical) |
| Licence | TODO: record the dataset's licence/terms here |

## Fetch and pin

```bash
git clone https://github.com/Graph-Drawing-Contest/eurovision-dataset data/raw/eurovision-dataset
git -C data/raw/eurovision-dataset checkout 1f39f6b238b94f2806694a08607998258ed8a41e
```

`data/raw/eurovision-dataset` is the default `data.raw_root` in `config/config.yaml`.
A clone elsewhere works too:

```bash
export ESC_DATA_ROOT=/path/to/eurovision-dataset
```

## How provenance is recorded

`esc-bias build-data` writes `data/processed/metadata.json` (also embedded in every
parquet file) with the raw path, the raw clone's git commit (read from `.git` as text;
`git` is never run inside the clone), a SHA-256 over every raw file read, and the code
version. A commit different from `expected_commit` in the config only logs a warning,
but it is always recorded. `reports/validation_summary.md` repeats the commit and hash.

## Optional 2026 hold-out

The course fork ends at 2025. 2026 exists only upstream (EurovisionAPI/dataset; audited
at commit `e56411125d4b91dc61f08dfb8d3c8a9fc91a6ad5`). It is a different ruleset
(register entry A23) and is only for an out-of-sample check:
`ESC_DATA_ROOT=<upstream clone> uv run esc-bias build-data --include-holdout`.

## Safety

Treat the clone as untrusted input: the pipeline only parses its JSON. Do not run
scripts from it.
