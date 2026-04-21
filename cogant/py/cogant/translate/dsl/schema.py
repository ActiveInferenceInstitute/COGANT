"""DSL schema dataclasses for YAML-based rule definitions."""

from __future__ import annotations

from dataclasses import dataclass, field

# Keys that a condition dict is allowed to contain.
KNOWN_CONDITION_KEYS = frozenset(
    {
        "node_kind",
        "name_pattern",
        "has_method",
        "edge_type",
    }
)


@dataclass(frozen=True)
class DSLCondition:
    """A single match condition within a DSL rule.

    Exactly one of the optional fields should be set; the loader
    validates this and raises ``ValueError`` for unknown keys.
    """

    node_kind: str | None = None
    """Match nodes whose ``NodeKind.value`` equals this (case-insensitive)."""

    name_pattern: str | None = None
    """Glob pattern matched against ``node.name`` via ``fnmatch``."""

    has_method: str | None = None
    """Class must contain a METHOD child whose name equals this string."""

    edge_type: str | None = None
    """Node must have at least one outgoing edge whose ``EdgeKind.value`` matches."""


@dataclass
class DSLRule:
    """A single rule defined in the DSL."""

    name: str
    """Human-readable rule name (used for provenance)."""

    role: str
    """Semantic role to assign on match (e.g. HIDDEN_STATE, ACTION, OBSERVATION)."""

    confidence: float
    """Confidence score returned when the rule matches (0.0 -- 1.0)."""

    conditions: list[DSLCondition]
    """All conditions must match for the rule to fire."""

    description: str | None = None
    """Optional human-readable description."""


@dataclass
class DSLRuleSet:
    """An ordered collection of DSL rules."""

    rules: list[DSLRule] = field(default_factory=list)
