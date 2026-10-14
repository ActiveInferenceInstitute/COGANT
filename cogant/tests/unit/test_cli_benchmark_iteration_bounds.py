"""``cogant benchmark`` requires at least one iteration.

With ``--iterations 0`` (or a negative count) no run is timed, so the
statistics step divided by zero. The option must be rejected up front as a
usage error.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cogant.cli.main import app


@pytest.mark.parametrize("count", ["0", "-2"])
def test_benchmark_rejects_non_positive_iterations(tmp_path: Path, count: str) -> None:
    result = CliRunner().invoke(app, ["benchmark", str(tmp_path), "--iterations", count])

    assert result.exit_code == 2, result.output
    assert not isinstance(result.exception, ZeroDivisionError)
    assert "--iterations" in result.output
