# 05 · Engineering standards

*How we build, check and ship this project, so that anyone can rerun every number and
figure from the raw data with one command. This answers plan-review issue **M7**
("reproducibility is scheduled for the last week") by making reproducibility the
starting point, not the final step. Each section states the rule, then how the repo
enforces it.*

Companion documents: [`01_plan_review.md`](01_plan_review.md) · [`02_literature_meta_analysis.md`](02_literature_meta_analysis.md) · [`03_data_audit.md`](03_data_audit.md) · [`04_study_design_v2.md`](04_study_design_v2.md) · [`06_red_team_review.md`](06_red_team_review.md)

---

## 1. Environment pinning

- **Rule:** one environment, pinned to exact versions, identical on both laptops and in CI.
- **How:** `pyproject.toml` declares dependencies (Python ≥ 3.11, pandas ≥ 3). `uv.lock`
  pins every package, including transitive ones. `.python-version` pins the interpreter
  that uv uses. `uv sync --locked` (in `make setup` and CI) fails if the lock is stale.
- To add a package: `uv add <pkg>` (or `uv add --dev <pkg>`), commit `pyproject.toml`
  **and** `uv.lock` in the same PR, and say why in the PR description. No `pip install`
  into the project environment.

## 2. Data versioning and provenance

- **Rule:** raw data is read-only, external and pinned. Every derived file says which
  raw bytes and which code produced it.
- **How:**
  - Raw data lives outside git (`data/raw/` is gitignored). The source is the course
    dataset `Graph-Drawing-Contest/eurovision-dataset` at commit
    `1f39f6b238b94f2806694a08607998258ed8a41e`. Fetch instructions are in
    [`data/raw/README.md`](../data/raw/README.md). The location is set by `ESC_DATA_ROOT`
    or `data.raw_root`.
  - `esc-bias build-data` records the raw path, the raw git commit (read from `.git` as
    text, never by running git in the clone), a SHA-256 over every raw file read, the
    anomaly-register hash and the code commit. It writes them to
    `data/processed/metadata.json` and embeds them in each parquet file.
  - If the commit differs from `expected_commit` in `config/config.yaml`, a warning is
    logged. The actual commit is always recorded.
  - The raw clone is untrusted input. Code only parses its JSON (duplicate keys
    rejected) and never imports or runs anything from it. Ad-hoc scripts that read it
    use `python3 -I`.
- No DVC: one pinned external dataset plus a content hash is enough at this size.

## 3. Data contract and validation

- **Rule:** the tidy table has a written, executable contract, and integrity problems
  are *reported*, never silently fixed and never fatal to the build.
- **How:** `src/esc_bias/validate.py`.
  - **Schema** (pandera): column types, allowed values (rounds, vote types, points scale,
    country-code pattern), nullable place/running.
  - **Ballot integrity:** every jury/televote ballot awards {12, 10, 8…1} exactly once.
    Every ballot covers all performers except the voter (explicit zeros). There are no
    self-votes, and jury + televote = combined for every pair. Per-receiver sums equal
    the raw `points` field. All codes are known (`WLD` is allowed only as a televote or
    combined voter). Keys are unique. Identical jury and televote ballots raise a warning.
    Missing or cancelled rounds are also reported as warnings.
  - The report (`reports/validation_report.csv`) has one row per check or per failing
    record. `reports/validation_summary.md` is deterministic (no timestamps), so it is
    committed and diffs show real changes. `esc-bias validate --strict` exits non-zero
    on any error-level failure. Failing ballots are also written as draft entries to
    `reports/anomaly_candidates.csv`.
  - **Anomaly register** (`config/anomaly_register.csv`): every known non-genuine or
    non-comparable vote (substitute juries, synthetic SM televote, `WLD`, 2020, the 2026
    ruleset…) has an id, match keys, a handling (`keep`/`flag`/`sensitivity`/`exclude`)
    and a source URL. Analyses filter **only** through the columns the register produces.
    Changes to it go through a reviewed PR.

## 4. Pipeline

- **Rule:** one command from raw data to every reported number. No manual steps, no
  copy-pasted outputs.
- **How:** `make all` = `lint → test → data → validate`, then analysis targets as they
  are added. Each step is a CLI subcommand (`esc-bias …`) that reads `config/config.yaml`
  and writes into `data/processed/` or `reports/`. Notebooks read those outputs and never
  write processed data. `make clean` removes all generated files (never `data/raw`).
  Make is enough here; Snakemake or DVC would add more than they save.

## 5. Testing pyramid

| Level | What | Where | Runs in CI |
|---|---|---|---|
| Unit | Pure functions on tiny hand-built inputs with hand-computed answers (baseline, QAP, disparity filter, vote-type mapping) | `tests/test_*.py` | yes |
| Component | Raw JSON → tidy table → validation on a **synthetic** dataset in the real layout (`tests/conftest.py`), including corruption tests (bad ballot, self-vote, duplicate key, missing zero) | `tests/test_io.py`, `test_validate.py`, `test_cli.py` | yes |
| Integration | Full build and validation on the real clone; exact counts at the pinned commit | `tests/test_rawdata_integration.py`, marker `rawdata` | no (needs `ESC_DATA_ROOT`) |
| Smoke | Notebooks compile; `make all` runs end to end | `tests/test_notebooks.py`, `make all` | compile only |

Rules: every new function in `src/` gets a test in the same PR. A bug fix starts with a
failing test. Test data is synthetic or derived (never a copy of the raw data). Branch
coverage is reported (`make test`); aim for ≥ 90 % on `src/`, excluding stubs.

## 6. Continuous integration

`.github/workflows/ci.yml` runs on every push and PR: `uv sync --locked`,
`ruff check`, `ruff format --check`, `mypy src`, `pytest --cov`. A red CI blocks merging.
CI has no raw data, so the raw-data integration tests are skipped there and must be run
locally (`make test` with `ESC_DATA_ROOT` set) before merging data-touching PRs.

## 7. Code review

Four-eyes rule: every PR is reviewed and approved by the other teammate before merge
(plan review m6). The reviewer checklist is in [`CONTRIBUTING.md`](../CONTRIBUTING.md):
reruns from scratch, tests, register entries with sources, seeds, uncertainty next to
every ranking, neutral wording. Keep PRs small (< ~400 changed lines) so review is real.

## 8. Code style

- `src/` layout, a typed public API (`mypy` with `disallow_untyped_defs`), docstrings on
  every public function, small functions, no hidden global state.
- `ruff` lint and format (line length 100) on `src/`, `tests/` and `notebooks/`. Run
  with `make format`. Pre-commit runs it on each commit (`make setup` installs the hooks).
- Prefer clear pandas over clever pandas. A function that needs a comment to explain a
  chained expression should be split.

## 9. Notebook hygiene

- Notebooks are **thin**: load processed data, call `esc_bias` functions, show tables
  and figures. Any logic used twice, or that a result depends on, moves to `src/` with a test.
- Source of truth: jupytext percent `.py` files in `notebooks/`. `.ipynb` files are
  local views (gitignored). Pair with `jupytext --sync notebooks/<name>.py`. The
  `nbstripout` hook strips outputs from any notebook that is committed anyway.
- Numbered names (`01_data_overview.py`, `02_baseline_reference.py`, …), a markdown
  header stating the purpose and prerequisites, and they run top to bottom on a fresh kernel.

## 10. Seeds and determinism

- One global seed in `config/config.yaml` (`seeds.global`). Functions that draw random
  numbers take an explicit `seed` or `numpy.random.Generator`. Nothing calls
  `np.random.seed` or uses the global RNG.
- Every permutation p-value is reported with its seed and number of permutations
  (`PermutationResult` stores both). Use the add-one p-value `(1 + #extreme) / (1 + n)`.
- Outputs are deterministic: sorted rows, no timestamps in committed reports, and PDF
  figures are saved without a creation date.

## 11. Logging

Use the standard `logging` module (`log = logging.getLogger(__name__)`), never `print`,
in `src/`. INFO is for pipeline steps and counts. WARNING is for data surprises that
do not stop the run (commit mismatch, missing round file, anomaly candidates). The CLI
sets the format, and `esc-bias -v` switches to DEBUG.

## 12. Figure standards

- Made by code (notebook or `src/`), saved via `esc_bias.viz.save_figure` to
  `reports/figures/` as PNG (300 dpi) and PDF, with a stable name `figNN_<what>`.
- `viz.set_style()` sets recessive grids, no top or right spines and a consistent font
  size. Vote types always use the same colours (`VOTE_TYPE_COLORS`). Bias heatmaps use
  the blue ↔ grey ↔ red diverging map with symmetric limits (`symmetric_limits`).
  Magnitudes use a single-hue sequential map. No rainbow maps and no dual y-axes.
- Every ranked estimate shows its uncertainty and `n_obs`. Labels use neutral wording
  ("excess points"). Captions state the data scope (years, rounds, vote type,
  exclusions) and the seed where relevant.
- The network figure shows a backbone (disparity filter or interval-excludes-zero), not
  an arbitrary top-k. The heatmap is seriated (community or clustering order).

## 13. Definition of done per milestone

| Milestone | Done when |
|---|---|
| **M1 · Repo & skeleton** (Nov 3–5) | `make setup && make test` green on both laptops and in CI. Environment locked. README quickstart works. |
| **Data dictionary** (Nov 6–16) | `make data validate` green on the pinned commit. Tidy-table columns documented (README). Data audit (`03`) merged. Anomaly register seeded with sources. |
| **Clean data & baseline** (Nov 17–30) | Register reviewed by both. Baseline reference metric tested and reported. Coverage (obs per pair) reported. Region, border and language covariates as a versioned, sourced table with tests. |
| **M2 · Progress report** (Dec 15–17) | `04_study_design_v2.md` frozen (pre-registration). Primary models implemented with tests on simulated data where the true effects are known. RQ1/RQ3 first results produced by `make all`. Everything after this point is labelled exploratory. |
| **Network & robustness** (Dec 18–Jan 6) | QAP/MRQAP with seeds and permutation counts reported. Sensitivity runs (register `sensitivity` rows, finals-only, rank model) produced by code. Backbone and consensus communities with a null comparison. |
| **Final** (Jan 15–27) | A fresh clone + `uv sync` + `make all` reproduces every number and figure in the report. All figures are produced by code. CITATION, licence and AI-use statement completed. Tag a release. |

General definition of done for any PR: tests added and passing, CI green, reviewed by
the teammate, docs and config updated, and no generated or raw data committed.

## 14. Checklist against plan-review M7

| M7 requirement | Where it is met | Status |
|---|---|---|
| Pinned environment | `pyproject.toml`, `uv.lock`, `.python-version`, `uv sync --locked` | done |
| `src/` package + thin notebooks | `src/esc_bias/`, `notebooks/*.py` (jupytext) | done |
| One-command pipeline (`make all`) | `Makefile`, `esc-bias build-data` / `validate` | done (analysis steps to be added) |
| Data-validation tests | `validate.py` contract + integrity report; `tests/test_validate.py`; `rawdata` integration tests | done |
| CI on every push | `.github/workflows/ci.yml` | done |
| Pinned data commit hash | `config.yaml: expected_commit`; commit + SHA-256 in `metadata.json` and the validation summary | done |
| Fixed seeds | `config.yaml: seeds`; explicit `seed` arguments; seed stored in results | done |
| Anomaly handling is explicit (C3) | `config/anomaly_register.csv` → `exclude` / `sensitivity` / `is_flagged` | done (domain entries from `03`) |
| Four-eyes review (m6) | `CONTRIBUTING.md`; branch protection on `main` (to switch on in GitHub settings) | to do: enable branch protection |
| Primary models, MRQAP, communities | `models.py`, `inference.mrqap`, `network.detect_communities` interfaces documented | to do (stubs) |
