"""``cogant.metrics`` must import, and fail clearly, outside a source checkout.

pyyaml is not a runtime dependency of the package and ``METRICS.yaml`` is
not package data, so the module used to raise ``ModuleNotFoundError`` at
import time on a plain install and an unexplained ``FileNotFoundError`` for
a path like ``<site-packages>/../evaluation/METRICS.yaml`` once yaml was
installed. The import must succeed, and ``load()`` must name the missing
piece.

Each scenario runs in a fresh interpreter so the module-level state and the
``lru_cache`` on ``load()`` start clean.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

pytestmark = pytest.mark.unit


def _run(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def test_import_succeeds_without_pyyaml_and_load_names_it() -> None:
    result = _run(
        """
        import sys
        sys.modules["yaml"] = None  # simulate an install without pyyaml
        import cogant.metrics as m
        try:
            m.load()
        except ImportError as exc:
            print("IMPORT_ERROR", exc)
        else:
            print("LOADED")
        """
    )

    assert result.returncode == 0, result.stderr
    assert "IMPORT_ERROR" in result.stdout
    assert "pyyaml" in result.stdout.lower()


def test_missing_metrics_file_raises_an_explanatory_error(tmp_path) -> None:
    missing = tmp_path / "evaluation" / "METRICS.yaml"
    result = _run(
        f"""
        import cogant.metrics as m
        from pathlib import Path
        m._METRICS_PATH = Path({str(missing)!r})
        try:
            m.version()
        except FileNotFoundError as exc:
            print("NOT_FOUND", exc)
        """
    )

    assert result.returncode == 0, result.stderr
    assert "NOT_FOUND" in result.stdout
    assert str(missing) in result.stdout
    assert "source checkout" in result.stdout
