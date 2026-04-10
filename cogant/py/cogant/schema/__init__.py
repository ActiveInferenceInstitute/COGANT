"""Versioned GNN schema detection, migration, and validation.

Exports
-------
SchemaVersion : Version identifiers for the GNN format.
GNN_V1_0_REQUIRED_SECTIONS : Sections required by GNN v1.0.
GNN_V1_1_REQUIRED_SECTIONS : Sections required by GNN v1.1.
detect_version : Detect the schema version of a GNN text.
migrate_gnn : Migrate a GNN text to a target schema version.
"""

from cogant.schema.versions import (
    SchemaVersion,
    GNN_V1_0_REQUIRED_SECTIONS,
    GNN_V1_1_REQUIRED_SECTIONS,
)
from cogant.schema.detector import detect_version
from cogant.schema.migrations import migrate_gnn

__all__ = [
    "SchemaVersion",
    "GNN_V1_0_REQUIRED_SECTIONS",
    "GNN_V1_1_REQUIRED_SECTIONS",
    "detect_version",
    "migrate_gnn",
]
