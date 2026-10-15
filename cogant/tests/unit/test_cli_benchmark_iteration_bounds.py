"""``cogant benchmark`` requires at least one iteration.

With ``--iterations 0`` (or a negative count) no run is timed, so the
statistics step divided by zero. The option must be rejected up front as a
usage error.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.utils import strip_ansi
from typer.testing import CliRunner

from cogant.cli.main import app


@pytest.mark.parametrize("count", ["0", "-2"])
@pytest.mark.parametrize("color", [False, True])
def test_benchmark_rejects_non_positive_iterations(tmp_path: Path, count: str, color: bool) -> None:
    result = CliRunner().invoke(
        app,
        ["benchmark", str(tmp_path), "--iterations", count],
        color=color,
        env={"TERM": "xterm-256color", "FORCE_COLOR": "1", "NO_COLOR": None},
    )

    assert result.exit_code == 2, result.output
    assert not isinstance(result.exception, ZeroDivisionError)
    output = strip_ansi(result.output)
    assert "--iterations" in output
    assert f"{count} is not in the range x>=1" in output
