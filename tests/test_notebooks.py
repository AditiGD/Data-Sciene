"""Notebooks are plain-Python percent files: they must at least compile.

Running them end to end needs the processed data (``make data``); that is part of
``make all``, not of the unit tests.
"""

from __future__ import annotations

import py_compile
from pathlib import Path

import pytest

NOTEBOOKS = sorted((Path(__file__).resolve().parents[1] / "notebooks").glob("*.py"))


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_compiles(path: Path) -> None:
    py_compile.compile(str(path), doraise=True)


def test_there_are_notebooks() -> None:
    assert NOTEBOOKS
