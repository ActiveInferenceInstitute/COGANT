"""Behavioral tests for cogant.cli.migrate module internals.

Tests exercise detect_version and migrate_gnn directly (the underlying
business logic that the CLI delegates to) and also test the migrate_app
Typer CLI via CliRunner — real files, no mocks.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cogant.schema import SchemaVersion, detect_version, migrate_gnn
from cogant.cli.migrate import migrate_app

runner = CliRunner()

# ------------------------------------------------------------------ #
# Fixtures — canonical GNN documents
# ------------------------------------------------------------------ #

GNN_V1_0 = """## GNNSection

TestModel

## ModelName

TestModel

## StateSpaceBlock

s: [s0, s1]

## ActInfOntologyAnnotation

type: agent
"""

GNN_V1_1 = """## GNNSection

TestModel

## ModelName

TestModel

## GNNVersionAndFlags
GNN v1

## StateSpaceBlock

s: [s0, s1]

## ActInfOntologyAnnotation

type: agent
"""


# ------------------------------------------------------------------ #
# detect_version (pure-function tests)
# ------------------------------------------------------------------ #


def test_detect_version_v1_0_returns_v1_0() -> None:
    assert detect_version(GNN_V1_0) == SchemaVersion.V1_0


def test_detect_version_v1_1_returns_v1_1() -> None:
    assert detect_version(GNN_V1_1) == SchemaVersion.V1_1


def test_detect_version_empty_string_fallback() -> None:
    assert detect_version("") == SchemaVersion.V1_0


def test_detect_version_random_text_fallback() -> None:
    assert detect_version("Hello world, no GNN content here.") == SchemaVersion.V1_0


# ------------------------------------------------------------------ #
# migrate_gnn (pure-function tests)
# ------------------------------------------------------------------ #


def test_migrate_gnn_v1_0_adds_flags_section() -> None:
    migrated, changes = migrate_gnn(GNN_V1_0, target=SchemaVersion.V1_1)
    assert "GNNVersionAndFlags" in migrated
    assert len(changes) == 1


def test_migrate_gnn_v1_1_already_at_target() -> None:
    migrated, changes = migrate_gnn(GNN_V1_1, target=SchemaVersion.V1_1)
    assert changes == []
    assert migrated == GNN_V1_1


def test_migrate_gnn_idempotent() -> None:
    """Running migrate twice on already-v1.1 text produces no further changes."""
    migrated1, _ = migrate_gnn(GNN_V1_0, target=SchemaVersion.V1_1)
    migrated2, changes2 = migrate_gnn(migrated1, target=SchemaVersion.V1_1)
    assert changes2 == []
    assert migrated1 == migrated2


def test_migrate_gnn_result_detects_as_v1_1() -> None:
    migrated, _ = migrate_gnn(GNN_V1_0, target=SchemaVersion.V1_1)
    assert detect_version(migrated) == SchemaVersion.V1_1


# ------------------------------------------------------------------ #
# CLI via CliRunner (real temp files)
# ------------------------------------------------------------------ #


def test_cli_migrate_file_not_found(tmp_path: Path) -> None:
    """migrate exits with code 1 when the file does not exist."""
    missing = tmp_path / "nonexistent.gnn.md"
    result = runner.invoke(migrate_app, [str(missing)])
    assert result.exit_code == 1


def test_cli_migrate_already_at_current(tmp_path: Path) -> None:
    """migrate reports 'Already at target version' for a v1.1 file."""
    gnn_file = tmp_path / "model.gnn.md"
    gnn_file.write_text(GNN_V1_1, encoding="utf-8")
    result = runner.invoke(migrate_app, [str(gnn_file)])
    assert result.exit_code == 0
    assert "Already at target" in result.output


def test_cli_migrate_applies_migration(tmp_path: Path) -> None:
    """migrate upgrades a v1.0 file to v1.1 in-place."""
    gnn_file = tmp_path / "model.gnn.md"
    gnn_file.write_text(GNN_V1_0, encoding="utf-8")

    result = runner.invoke(migrate_app, [str(gnn_file)])
    assert result.exit_code == 0

    updated = gnn_file.read_text(encoding="utf-8")
    assert "GNNVersionAndFlags" in updated
    assert detect_version(updated) == SchemaVersion.V1_1


def test_cli_migrate_dry_run_does_not_modify_file(tmp_path: Path) -> None:
    """--dry-run prints diff but does not write the file."""
    gnn_file = tmp_path / "model.gnn.md"
    gnn_file.write_text(GNN_V1_0, encoding="utf-8")

    result = runner.invoke(migrate_app, [str(gnn_file), "--dry-run"])
    assert result.exit_code == 0

    # File content must be unchanged
    unchanged = gnn_file.read_text(encoding="utf-8")
    assert unchanged == GNN_V1_0
