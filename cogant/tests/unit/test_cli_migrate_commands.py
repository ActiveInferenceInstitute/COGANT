"""Behavioral tests for the current-only ``cogant migrate`` verifier."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cogant.cli.migrate import migrate_app
from cogant.schema import CURRENT_GNN_VERSION, UNSUPPORTED_GNN_VERSION, detect_version

runner = CliRunner()

CURRENT_GNN = """## GNNSection

TestModel

## GNNVersionAndFlags
GNN v2.0.0

## ModelName

TestModel
"""

UNSUPPORTED_GNN = """## GNNSection

TestModel

## GNNVersionAndFlags
GNN experimental
"""


def test_detect_version_current_returns_current() -> None:
    assert detect_version(CURRENT_GNN) == CURRENT_GNN_VERSION


def test_detect_version_unsupported_returns_unsupported() -> None:
    assert detect_version(UNSUPPORTED_GNN) == UNSUPPORTED_GNN_VERSION


def test_cli_migrate_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "missing.gnn.md"
    result = runner.invoke(migrate_app, [str(missing)])
    assert result.exit_code == 1


def test_cli_migrate_current_file_passes(tmp_path: Path) -> None:
    gnn_file = tmp_path / "model.gnn.md"
    gnn_file.write_text(CURRENT_GNN, encoding="utf-8")
    result = runner.invoke(migrate_app, [str(gnn_file)])
    assert result.exit_code == 0
    assert "current schema" in result.output
    assert gnn_file.read_text(encoding="utf-8") == CURRENT_GNN


def test_cli_migrate_unsupported_file_fails_without_rewrite(tmp_path: Path) -> None:
    gnn_file = tmp_path / "model.gnn.md"
    gnn_file.write_text(UNSUPPORTED_GNN, encoding="utf-8")
    result = runner.invoke(migrate_app, [str(gnn_file)])
    assert result.exit_code == 1
    assert "Unsupported GNN schema" in result.output
    assert gnn_file.read_text(encoding="utf-8") == UNSUPPORTED_GNN
