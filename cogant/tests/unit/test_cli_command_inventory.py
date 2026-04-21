"""Regression test for the top-level Typer command surface.

The CLI exposes a fixed surface of subcommands documented in
``cogant/docs/cli/commands.md`` and ``manuscript/03_api_and_workflows.md``.
This test guards against accidental drift in either direction (a command
silently dropped, or a new one added without updating the docs) by
asserting the exact count plus the presence of three commands the docs
flag as central.
"""

from __future__ import annotations

import pytest
import typer
from typer.main import get_command
from typer.testing import CliRunner

from cogant.cli.main import app

pytestmark = pytest.mark.unit

EXPECTED_COMMAND_COUNT = 28
REQUIRED_COMMANDS = {"reverse", "roundtrip", "upstream-gnn", "translate", "validate"}


def _registered_command_names() -> set[str]:
    """Enumerate top-level command names as Click sees them after Typer wires
    the Typer app into a Click MultiCommand."""
    click_cmd = get_command(app)
    if not hasattr(click_cmd, "commands"):
        raise AssertionError("Typer app did not produce a Click group")
    return set(click_cmd.commands.keys())  # type: ignore[attr-defined]


def test_top_level_command_count() -> None:
    names = _registered_command_names()
    assert len(names) == EXPECTED_COMMAND_COUNT, (
        f"expected exactly {EXPECTED_COMMAND_COUNT} top-level commands, "
        f"found {len(names)}: {sorted(names)}"
    )


def test_required_commands_present() -> None:
    names = _registered_command_names()
    missing = REQUIRED_COMMANDS - names
    assert not missing, f"missing required commands: {sorted(missing)}"


def test_typer_app_imports_cleanly() -> None:
    assert isinstance(app, typer.Typer)


def test_reverse_subcommand_signature_preserved() -> None:
    """The ``reverse`` command must expose its real options after the
    decorator-form rewrite (regression test for typer + functools.wraps)."""
    runner = CliRunner()
    result = runner.invoke(app, ["reverse", "--help"])
    assert result.exit_code == 0
    assert "GNN_FILE" in result.output
    assert "--output" in result.output
    assert "--json" in result.output


def test_roundtrip_subcommand_signature_preserved() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["roundtrip", "--help"])
    assert result.exit_code == 0
    assert "TARGET" in result.output
    assert "--threshold" in result.output
