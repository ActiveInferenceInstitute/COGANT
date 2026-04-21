"""Tests for cogant.schema — versioned GNN schema detection and migration."""

from cogant.schema import SchemaVersion, detect_version, migrate_gnn
from cogant.schema.versions import (
    GNN_V1_0_REQUIRED_SECTIONS,
    GNN_V1_1_REQUIRED_SECTIONS,
)

# ---------------------------------------------------------------------------
# Fixtures — minimal GNN texts
# ---------------------------------------------------------------------------

GNN_V1_0_TEXT = """\
## GNNSection
Example section content.

## ModelName
TestModel

## StateSpaceBlock
Some state space definition.

## ActInfOntologyAnnotation
Ontology details here.
"""

GNN_V1_1_TEXT = """\
## GNNSection
Example section content.

## GNNVersionAndFlags
GNN v1

## ModelName
TestModel

## StateSpaceBlock
Some state space definition.

## ActInfOntologyAnnotation
Ontology details here.
"""


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------


def test_detect_version_v1_0():
    """GNN without GNNVersionAndFlags section is detected as V1_0."""
    assert detect_version(GNN_V1_0_TEXT) == SchemaVersion.V1_0


def test_detect_version_v1_1():
    """GNN with 'GNN v1' in GNNVersionAndFlags section is detected as V1_1."""
    assert detect_version(GNN_V1_1_TEXT) == SchemaVersion.V1_1


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------


def test_migrate_v1_0_to_v1_1_adds_header():
    """Migrating v1.0 GNN adds a GNNVersionAndFlags section."""
    result, changes = migrate_gnn(GNN_V1_0_TEXT)
    assert "## GNNVersionAndFlags" in result
    assert "GNN v1" in result


def test_migrate_idempotent():
    """Migrating an already-v1.1 GNN returns unchanged text."""
    result, changes = migrate_gnn(GNN_V1_1_TEXT)
    assert result == GNN_V1_1_TEXT
    assert changes == []


def test_migrate_returns_changes_list():
    """Changes list is non-empty for v1.0 input."""
    _result, changes = migrate_gnn(GNN_V1_0_TEXT)
    assert len(changes) > 0
    assert any("GNNVersionAndFlags" in c for c in changes)


def test_migrate_gnn_empty_string():
    """Empty string migrates without crash."""
    result, changes = migrate_gnn("")
    # Should add GNNVersionAndFlags even to empty text
    assert isinstance(result, str)
    assert isinstance(changes, list)


def test_required_sections_v1_1_superset():
    """v1.1 required sections are a strict superset of v1.0."""
    assert set(GNN_V1_0_REQUIRED_SECTIONS).issubset(set(GNN_V1_1_REQUIRED_SECTIONS))
    assert len(GNN_V1_1_REQUIRED_SECTIONS) > len(GNN_V1_0_REQUIRED_SECTIONS)
