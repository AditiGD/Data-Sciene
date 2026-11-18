# Eurovision Song Contest voting patterns, 2016–2025

*Tannu Malik, Aditi Deshpande. Data Science course project.*

Do some countries repeatedly give more points to others than the receiving song's
popularity explains? We study the Eurovision Song Contest in the split jury/televote
era (2016–2025; no contest in 2020) as a directed, weighted, dynamic network:
countries are nodes, votes are edges, points are weights. Finals **and** semi-finals
are used, with jury and televote analysed separately.

## Research questions

- **RQ1** Which voter → receiver pairs give more points than the receiver's quality
  predicts, and do these pairs share a region, border, language or diaspora?
- **RQ2** Are these relationships stable across 2016–2025, or do they appear and disappear?
- **RQ3** For the same pairs, how large is the gap between jury and televote bias?

Findings are descriptive: no causal claims, no significance claims for single pairs.
The methodological upgrades (joint quality + dyad models per vote type, anomaly
register, QAP inference, shrinkage, reproducibility from day 1) are motivated in
[`docs/01_plan_review.md`](docs/01_plan_review.md) and specified in
[`docs/04_study_design_v2.md`](docs/04_study_design_v2.md).

## Quickstart

```bash
uv sync                                            # exact environment from uv.lock
git clone https://github.com/Graph-Drawing-Contest/eurovision-dataset data/raw/eurovision-dataset
git -C data/raw/eurovision-dataset checkout 1f39f6b238b94f2806694a08607998258ed8a41e
export ESC_DATA_ROOT=$PWD/data/raw/eurovision-dataset   # or any other clone
make all                                           # lint, test, build data, validate
make results                                       # fit models, run RQ1-RQ3 + network, write reports/results + figures (~9 min)
```

`make all` writes `data/processed/votes.parquet` (the tidy vote table) and
`reports/validation_summary.md`. Details on the data and its pinning:
[`data/raw/README.md`](data/raw/README.md). Without `ESC_DATA_ROOT`, `make test` still
runs every unit test on small synthetic data; the raw-data integration tests are skipped.

## Repository map

```
config/
  config.yaml             years, rounds, vote types, rules, seeds, paths
  anomaly_register.csv    known data issues and their handling (keep/flag/sensitivity/exclude)
src/esc_bias/
  config.py               load config (+ ESC_DATA_ROOT override)
  io.py                   raw JSON -> tidy long table with explicit zeros; provenance
  anomalies.py            apply the anomaly register (is_flagged, exclude, sensitivity)
  validate.py             pandera data contract + ballot-integrity report
  baseline.py             proposal's leave-one-out metric (reference implementation)
  models.py               joint quality + dyad models (interfaces; fitting to do)
  inference.py            QAP correlation, node-label and within-ballot permutations
  network.py              signed bias graph, disparity-filter backbone
  viz.py                  figure style and saving
  cli.py                  `esc-bias build-data`, `esc-bias validate`
tests/                    unit tests (synthetic fixtures) + @rawdata integration tests
notebooks/                thin jupytext notebooks (.py, percent format)
data/raw/                 not committed; how to fetch it
data/interim/, data/processed/   generated, not committed
reports/                  validation report; figures/ (generated, not committed)
docs/                     plan review, literature, data audit, study design, standards, red team
audit/                    data-audit scripts (as run) + curated reference tables (contiguity, coverage)
meta_analysis/            effect table, meta-analysis script, search log
pilot/                    exploratory methods pilot + planted-bias simulation (reference code for models.py)
```

### The tidy vote table (`data/processed/votes.parquet`)

One row per `(year, round, vote_type, voter, receiver)`, **including explicit zeros**
for every voter × performer pair (no self-votes). Absent countries have no rows:
missing is not 0.

| column | meaning |
|---|---|
| `year`, `round` | 2016–2025; `final`, `semifinal1`, `semifinal2` |
| `vote_type` | `jury`, `televote`, `combined`. 2023–25 semi-finals are televote-only (raw `total`) |
| `vote_type_source` | raw score name: `jury`, `public`, `total` |
| `voter`, `receiver`, `points` | country codes and points (0–12; combined 0–24) |
| `receiver_place`, `receiver_running` | result and running order of the receiver in that round |
| `voter_is_country` | `False` for `WLD` (Rest of the World televote, 2023+) |
| `voter_performs_in_round` | `False` for e.g. Big Five voting in a semi-final |
| `jury_method` | `average_rank` (2016–17) / `exponential_weight` (2018+) on rows with a jury ballot |
| `is_flagged`, `exclude`, `sensitivity`, `anomaly_ids` | from the anomaly register |

Primary pair-level analyses use `votes[~votes.exclude]`; the pre-specified sensitivity
run also drops `votes.sensitivity` rows.

## Documentation

| Document | Content |
|---|---|
| [`docs/01_plan_review.md`](docs/01_plan_review.md) | Review of the proposal: strengths, issues by severity, scorecard |
| [`docs/02_literature_meta_analysis.md`](docs/02_literature_meta_analysis.md) | Literature and meta-analysis |
| [`docs/03_data_audit.md`](docs/03_data_audit.md) | Data audit and anomaly list |
| [`docs/04_study_design_v2.md`](docs/04_study_design_v2.md) | Upgraded study design (pre-registration at Milestone 2) |
| [`docs/04a_methods_and_pilot.md`](docs/04a_methods_and_pilot.md) | Methods detail, pilot and planted-bias simulation |
| [`docs/05_engineering_standards.md`](docs/05_engineering_standards.md) | Engineering standards and definition of done |
| [`docs/06_red_team_review.md`](docs/06_red_team_review.md) | Red-team review |
| [`docs/07_results.md`](docs/07_results.md) | Results of the first full pipeline run (RQ1–RQ3, network, robustness) |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Branching, review, commit style |

## Data

Graph Drawing Contest 2026 Eurovision dataset
(<https://github.com/Graph-Drawing-Contest/eurovision-dataset>, pinned commit
`1f39f6b2`), a fork of the unofficial EurovisionAPI dataset
(<https://github.com/EurovisionAPI/dataset>). Public data, no personal information.

## License

TODO: the team chooses a licence for the code and text (and checks the dataset's terms)
before publishing. No licence is granted until then.

## AI-use statement

Placeholder: the team will document any AI assistance here, as required by the course rules.
