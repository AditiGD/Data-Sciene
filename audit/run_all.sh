#!/usr/bin/env bash
# Re-run the full audit pipeline. Usage: bash run_all.sh <DATA_DIR> [OUT_DIR]
# DATA_DIR = <repo>/data of EurovisionAPI/dataset or the GD-2026 fork (Graph-Drawing-Contest/eurovision-dataset).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; DATA="$1"; OUT="${2:-$HERE/out}"
python3 -I "$HERE/01_build_tidy.py" "$DATA" "$OUT"
python3 -I "$HERE/02_checks.py" "$DATA" "$OUT" --strict
python3 -I "$HERE/03_annotate_coverage.py" "$OUT"
python3 -I "$HERE/04_enrichment.py" "$OUT"
python3 -I "$HERE/05_schema.py" "$OUT"
python3 -I "$HERE/06_profile.py" "$OUT"
