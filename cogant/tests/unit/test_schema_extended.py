"""Extended behavioral tests for cogant.schema — migrations.py, detector.py, versions.py.

Covers: detection edge cases, migration of text without GNNSection,
double migration idempotency, version constants, empty/whitespace inputs,
and GNNVersionAndFlags without GNN v1 marker.
"""

from __future__ import annotations

import pytest

from cogant.schema import SchemaVersion, detect_version, migrate_gnn
from cogant.schema.migrations import migrate_v1_0_to_v1_1
from cogant.schema.versions import GNN_V1_0_REQUIRED_SECTIONS, GNN_V1_1_REQUIRED_SECTIONS


# ---------------------------------------------------------------------------
# Detection edge cases
# ---------------------------------------------------------------------------


def test_detect_version_whitespace_only() -> None:
    """Whitespace-only string is detected as v1.0 (fallback)."""
    assert detect_version("   \n\t  ") == SchemaVersion.V1_0


def test_detect_version_version_header_without_marker() -> None:
    """GNNVersionAndFlags section without 'GNN v1' marker falls back to v1.0."""
    text = "## GNNVersionAndFlags\nSome other content\n"
    assert detect_version(text) == SchemaVersion.V1_0


def test_detect_version_marker_without_header() -> None:
    """'GNN v1' marker without GNNVersionAndFlags section falls back to v1.0."""
    text = "## SomeOtherSection\nGNN v1\n"
    assert detect_version(text) == SchemaVersion.V1_0


def test_detect_version_both_present() -> None:
    """Both GNNVersionAndFlags header and GNN v1 marker => v1.1."""
    text = "## GNNVersionAndFlags\nGNN v1\n\n## GNNSection\nContent\n"
    assert detect_version(text) == SchemaVersion.V1_1


def test_detect_version_case_sensitive_header() -> None:
    """The section header match is case-sensitive on '## GNNVersionAndFlags'."""
    text = "## gnnversionandflags\nGNN v1\n"
    assert detect_version(text) == SchemaVersion.V1_0


def test_detect_version_extra_whitespace_in_header() -> None:
    """Extra whitespace after ## is handled by regex."""
    text = "##   GNNVersionAndFlags\nGNN v1\n"
    assert detect_version(text) == SchemaVersion.V1_1


# ---------------------------------------------------------------------------
# Migration edge cases
# ---------------------------------------------------------------------------


def test_migrate_no_gnn_section_prepends_header() -> None:
    """Text without ## GNNSection gets GNNVersionAndFlags prepended."""
    text = "Some random text without any sections.\n"
    result, changes = migrate_v1_0_to_v1_1(text)
    assert result.startswith("## GNNVersionAndFlags")
    assert "GNN v1" in result
    assert len(changes) == 1
    assert "Prepended" in changes[0]


def test_migrate_double_migration_idempotent() -> None:
    """Migrating twice produces the same result as migrating once."""
    text = "## GNNSection\nModel\n\n## ModelName\nTest\n"
    result1, changes1 = migrate_gnn(text)
    result2, changes2 = migrate_gnn(result1)
    assert result1 == result2
    assert changes2 == []


def test_migrate_preserves_existing_content() -> None:
    """Migration adds the version header but doesn't alter existing sections."""
    text = "## GNNSection\nMyModel\n\n## StateSpaceBlock\nstates here\n"
    result, _ = migrate_gnn(text)
    assert "## GNNSection" in result
    assert "MyModel" in result
    assert "## StateSpaceBlock" in result
    assert "states here" in result


def test_migrate_v1_0_to_v1_1_already_v1_1() -> None:
    """migrate_v1_0_to_v1_1 is a no-op on already-v1.1 text."""
    text = "## GNNVersionAndFlags\nGNN v1\n\n## GNNSection\nContent\n"
    result, changes = migrate_v1_0_to_v1_1(text)
    assert result == text
    assert changes == []


# ---------------------------------------------------------------------------
# Version constants
# ---------------------------------------------------------------------------


def test_schema_version_current_is_v1_1() -> None:
    """SchemaVersion.CURRENT equals V1_1."""
    assert SchemaVersion.CURRENT == SchemaVersion.V1_1
    assert SchemaVersion.CURRENT == "1.1"


def test_v1_0_sections_are_subset_of_v1_1() -> None:
    """All v1.0 required sections appear in v1.1 required sections."""
    for section in GNN_V1_0_REQUIRED_SECTIONS:
        assert section in GNN_V1_1_REQUIRED_SECTIONS


def test_v1_1_adds_version_and_flags_section() -> None:
    """v1.1 adds 'GNNVersionAndFlags' that is not in v1.0."""
    assert "GNNVersionAndFlags" in GNN_V1_1_REQUIRED_SECTIONS
    assert "GNNVersionAndFlags" not in GNN_V1_0_REQUIRED_SECTIONS
