# Pilot: feasibility and planted-bias simulation

Exploratory pilot behind `docs/04a_methods_and_pilot.md`. It is **not** the production pipeline. That pipeline is the `esc_bias` package in `src/`. The model code here (`esc_models.py`: M0 baseline, M1 linear crossed effects with empirical-Bayes shrinkage, M2 top-10 Plackett–Luce with shrunk dyad effects) is the reference implementation to port into `src/esc_bias/models.py`.

Run from this folder, on a scratch copy (outputs are written to the current directory):

```bash
python build_long.py "$ESC_DATA_ROOT" long.csv
```

```bash
python covariates.py && python counts.py && python analysis_real.py
```

```bash
python sim.py
```

`sim.py` takes about 10 min on 4 cores. Small result summaries are kept in `results/`. Large intermediates (`long.csv`, `real_pair_estimates.csv`, `sim_raw.csv`) are not committed.

Known deviations from the final design:

- The San Marino televote (synthetic) is still included.
- Border, language and capital covariates are hand-coded in `covariates.py`. Replace them with CEPII GeoDist and the curated contiguity in `audit/reference_tables/`.
