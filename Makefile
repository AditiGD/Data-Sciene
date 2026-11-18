# One-command pipeline. Run `make help` for targets.
# The raw data root comes from ESC_DATA_ROOT (or data.raw_root in config/config.yaml).

UV      ?= uv
RUN     := $(UV) run
PY_SRC  := src tests notebooks

.PHONY: help setup data validate results test test-raw lint format all clean

help:  ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup:  ## create .venv from uv.lock (exact versions) and install git hooks
	$(UV) sync --locked
	-$(RUN) pre-commit install

data:  ## raw JSON -> data/processed/*.parquet
	$(RUN) esc-bias build-data

validate:  ## data contract + ballot integrity -> reports/validation_*
	$(RUN) esc-bias validate

results:  ## models, RQ1-RQ3, network -> reports/results/ and reports/figures/
	$(RUN) esc-bias analyze && $(RUN) esc-bias figures

test:  ## unit tests (+ raw-data integration tests if ESC_DATA_ROOT is set)
	$(RUN) pytest --cov --cov-report=term-missing:skip-covered

test-raw:  ## only the raw-data integration tests
	$(RUN) pytest -m rawdata

lint:  ## ruff lint + format check + mypy (our code only)
	$(RUN) ruff check $(PY_SRC)
	$(RUN) ruff format --check $(PY_SRC)
	$(RUN) mypy src

format:  ## auto-fix lint and formatting (our code only)
	$(RUN) ruff check --fix $(PY_SRC)
	$(RUN) ruff format $(PY_SRC)

all: lint test data validate  ## everything, in order

clean:  ## remove generated data and reports (never touches data/raw)
	rm -f data/processed/*.parquet data/processed/metadata.json data/interim/*.parquet
	rm -f reports/validation_report.csv reports/validation_summary.md reports/anomaly_candidates.csv
	rm -f reports/figures/*.png reports/figures/*.pdf
