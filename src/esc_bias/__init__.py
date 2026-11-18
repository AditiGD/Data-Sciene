"""esc_bias: Eurovision Song Contest voting favouritism (2016-2025).

The package is organised as a small pipeline:

``config`` -> ``io`` (raw JSON -> tidy table) -> ``anomalies`` (flags) ->
``validate`` (data contract + ballot integrity) -> ``baseline`` / ``models`` /
``inference`` / ``network`` (analysis) -> ``viz`` (figures).

Notebooks only import from here; they never re-implement logic.
"""

__version__ = "0.1.0"
