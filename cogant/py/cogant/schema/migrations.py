"""GNN schema migration functions."""
from __future__ import annotations

import re

from cogant.schema.detector import detect_version
from cogant.schema.versions import SchemaVersion

_GNN_SECTION_RE = re.compile(r"^##\s+GNNSection\b", re.MULTILINE)


def migrate_v1_0_to_v1_1(gnn_text: str) -> tuple[str, list[str]]:
    """Add GNNVersionAndFlags section if missing (v1.0 → v1.1)."""
    if detect_version(gnn_text) == SchemaVersion.V1_1:
        return gnn_text, []
    changes: list[str] = []
    match = _GNN_SECTION_RE.search(gnn_text)
    if match:
        # Insert after the GNNSection line and its model name value.
        lines = gnn_text.splitlines(keepends=True)
        insert_idx = gnn_text[:match.end()].count('\n')
        # skip the section name line + blank + model name
        out_lines = lines[:insert_idx + 3] + ["\n## GNNVersionAndFlags\nGNN v1\n"] + lines[insert_idx + 3:]
        migrated = "".join(out_lines)
        changes.append("Added ## GNNVersionAndFlags section (v1.0 → v1.1)")
    else:
        migrated = "## GNNVersionAndFlags\nGNN v1\n\n" + gnn_text
        changes.append("Prepended ## GNNVersionAndFlags (no GNNSection found)")
    return migrated, changes


def migrate_gnn(gnn_text: str, target: str = SchemaVersion.CURRENT) -> tuple[str, list[str]]:
    """Migrate gnn_text to target schema version. Idempotent."""
    current = detect_version(gnn_text)
    all_changes: list[str] = []
    if current == SchemaVersion.V1_0 and target in (SchemaVersion.V1_1, SchemaVersion.CURRENT):
        gnn_text, changes = migrate_v1_0_to_v1_1(gnn_text)
        all_changes.extend(changes)
    return gnn_text, all_changes


__all__ = ["migrate_v1_0_to_v1_1", "migrate_gnn"]
