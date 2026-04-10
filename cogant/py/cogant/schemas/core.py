"""Core schema definitions for program graphs."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


__all__ = ["NodeKind", "EdgeKind", "Node", "Edge"]


class NodeKind(StrEnum):
    """Types of nodes in a program graph."""
    # Code structure
    REPO = "repo"
    MODULE = "module"
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"

    # Endpoints and interfaces
    ENDPOINT = "endpoint"
    EVENT = "event"
    PARAMETER = "parameter"
    RETURN_VALUE = "return_value"

    # Data and configuration
    DATA_STRUCTURE = "data_structure"
    CONFIGURATION = "configuration"
    FEATURE_FLAG = "feature_flag"

    # Runtime and semantic
    TEST = "test"
    ASSERTION = "assertion"
    POLICY = "policy"
    ACTION = "action"


class EdgeKind(StrEnum):
    """Types of edges in a program graph."""
    # Structural
    CONTAINS = "contains"
    IMPORTS = "imports"
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    DEPENDS_ON = "depends_on"

    # Data flow
    READS = "reads"
    WRITES = "writes"
    RETURNS = "returns"
    CALLS = "calls"

    # Control flow
    THROWS = "throws"
    CATCHES = "catches"
    YIELDS = "yields"

    # Semantic
    OBSERVES = "observes"
    MUTATES = "mutates"
    GUARDS = "guards"
    TRIGGERS = "triggers"

    # Provenance
    EVIDENCE_FROM_STATIC = "evidence_from_static"
    EVIDENCE_FROM_DYNAMIC = "evidence_from_dynamic"


@dataclass
class Node:
    """Represents a node in the program graph."""

    id: str
    """Stable identifier (deterministic hash of repo, path, qualified_name)."""

    kind: NodeKind
    """Type of node (class, function, module, etc.)."""

    name: str
    """Human-readable name."""

    qualified_name: str
    """Fully qualified name in source language."""

    path: str | None = None
    """File path or module path."""

    language: str | None = None
    """Source language (python, javascript, java, etc.)."""

    source_range: dict[str, Any] | None = None
    """Start/end line and column in source file."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Language-specific metadata (visibility, decorators, etc.)."""

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """Timestamp of creation."""

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.id == other.id


@dataclass
class Edge:
    """Represents an edge (relationship) in the program graph."""

    id: str
    """Stable edge identifier."""

    source_id: str
    """Source node ID."""

    target_id: str
    """Target node ID."""

    kind: EdgeKind
    """Type of relationship."""

    weight: float = 1.0
    """Edge weight (frequency, confidence, etc.)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional relationship metadata."""

    evidence_sources: list[str] = field(default_factory=list)
    """List of evidence sources (static, dynamic, etc.)."""

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """Timestamp of creation."""

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Edge):
            return NotImplemented
        return self.id == other.id
