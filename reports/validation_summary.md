# Validation summary

## Provenance

- **raw_source_url**: `https://github.com/Graph-Drawing-Contest/eurovision-dataset`
- **raw_git_commit**: `1f39f6b238b94f2806694a08607998258ed8a41e`
- **raw_sha256**: `1a444e54e8de5e693db9a2209f11f1bb30a8045ec622bceed0fc6a783eec46b1`
- **years**: `[2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]`
- **n_rows**: `41350`

## Row counts

| year | round | performers | rows | voters_jury | voters_televote | voters_combined |
|---|---|---|---|---|---|---|
| 2016 | final | 26 | 3198 | 42 | 42 | 42 |
| 2016 | semifinal1 | 18 | 1080 | 21 | 21 | 21 |
| 2016 | semifinal2 | 18 | 1080 | 21 | 21 | 21 |
| 2017 | final | 26 | 3198 | 42 | 42 | 42 |
| 2017 | semifinal1 | 18 | 1080 | 21 | 21 | 21 |
| 2017 | semifinal2 | 18 | 1080 | 21 | 21 | 21 |
| 2018 | final | 26 | 3276 | 43 | 43 | 43 |
| 2018 | semifinal1 | 19 | 1197 | 22 | 22 | 22 |
| 2018 | semifinal2 | 18 | 1080 | 21 | 21 | 21 |
| 2019 | final | 26 | 3120 | 41 | 41 | 41 |
| 2019 | semifinal1 | 17 | 969 | 20 | 20 | 20 |
| 2019 | semifinal2 | 18 | 1080 | 21 | 21 | 21 |
| 2021 | final | 26 | 2964 | 39 | 39 | 39 |
| 2021 | semifinal1 | 16 | 864 | 19 | 19 | 19 |
| 2021 | semifinal2 | 17 | 969 | 20 | 20 | 20 |
| 2022 | final | 25 | 2925 | 40 | 40 | 40 |
| 2022 | semifinal1 | 17 | 918 | 19 | 19 | 19 |
| 2022 | semifinal2 | 18 | 1080 | 21 | 21 | 21 |
| 2023 | final | 26 | 2860 | 37 | 38 | 38 |
| 2023 | semifinal1 | 15 | 270 | <NA> | 19 | <NA> |
| 2023 | semifinal2 | 16 | 304 | <NA> | 20 | <NA> |
| 2024 | final | 25 | 2750 | 37 | 38 | 38 |
| 2024 | semifinal1 | 15 | 270 | <NA> | 19 | <NA> |
| 2024 | semifinal2 | 16 | 304 | <NA> | 20 | <NA> |
| 2025 | final | 26 | 2860 | 37 | 38 | 38 |
| 2025 | semifinal1 | 15 | 270 | <NA> | 19 | <NA> |
| 2025 | semifinal2 | 16 | 304 | <NA> | 20 | <NA> |

## Checks

10 checks, 0 failing error-level checks.

| check | severity | status | n_failures | example |
|---|---|---|---|---|
| schema | error | pass | 0 |  |
| unique_keys | error | pass | 0 |  |
| no_self_votes | error | pass | 0 |  |
| ballot_points_set | error | pass | 0 |  |
| complete_ballots | error | pass | 0 |  |
| jury_plus_televote_equals_combined | error | pass | 0 |  |
| identical_jury_televote_ballot | warning | pass | 0 |  |
| round_coverage | warning | FAIL | 3 | 2020 final: round cancelled |
| receiver_totals_match_raw | error | pass | 0 |  |
| known_codes | error | pass | 0 |  |

Full per-record results: `validation_report.csv`.
