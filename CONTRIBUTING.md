# Contributing

Two people, one rule: **nothing reaches `main` without the other person's review.**

## Workflow

1. Branch from an up-to-date `main`: `git switch main && git pull && git switch -c <type>/<short-topic>`
   (e.g. `feat/dyad-model`, `fix/wld-handling`, `docs/data-audit`).
2. Commit small, focused changes (see commit style). Run `make lint test` before pushing.
3. Open a pull request. CI (lint, mypy, tests) must be green.
4. **The other teammate reviews and approves** (four-eyes rule, plan review m6). The
   author merges (squash or rebase), then deletes the branch.
5. Analysis decisions that change results (exclusion rules, thresholds, model settings)
   go into `docs/04_study_design_v2.md` or `config/` in the same PR, with the reason.
   After the Milestone-2 freeze, label such changes **exploratory** in the PR title.

### What the reviewer checks

- Does it run from scratch (`make all`)? Are new outputs produced by code, not by hand?
- Is there a test for new logic in `src/esc_bias/` (synthetic data, no raw data needed)?
- Are new exclusions recorded in `config/anomaly_register.csv` with a `source_url`?
- Are seeds fixed and reported? Does every ranked estimate show `n_obs` and uncertainty?
- Is the wording neutral ("excess points", "dyadic affinity"), with no causal claims?

## Commit style

[Conventional Commits](https://www.conventionalcommits.org/): `<type>: <imperative summary>`,
types `feat`, `fix`, `docs`, `test`, `refactor`, `data`, `chore`. Example:
`feat: add rank-percentile residual to baseline`. Body: *why*, not *what*.

## How to run

```bash
uv sync                                  # exact environment from uv.lock
export ESC_DATA_ROOT=/path/to/eurovision-dataset   # see data/raw/README.md
make all                                 # lint, test, build data, validate
make help                                # all targets
```

## Where things go

| Change | Location |
|---|---|
| Reusable logic (loading, metrics, models, plots helpers) | `src/esc_bias/` + a test in `tests/` |
| Exploration, figures, narrative | `notebooks/*.py` (jupytext percent format; import from the package) |
| Settings (years, seeds, paths) | `config/config.yaml` |
| Known data issues and their handling | `config/anomaly_register.csv` |
| Methods, decisions, standards | `docs/` |

Never commit raw data, secrets, `.ipynb` outputs or generated figures; `.gitignore`
and the pre-commit hooks (`make setup`) enforce most of this.
