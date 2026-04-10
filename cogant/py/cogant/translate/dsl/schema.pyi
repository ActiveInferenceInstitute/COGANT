from dataclasses import dataclass, field

from _typeshed import Incomplete as Incomplete

KNOWN_CONDITION_KEYS: Incomplete

@dataclass(frozen=True)
class DSLCondition:
    node_kind: str | None = ...
    name_pattern: str | None = ...
    has_method: str | None = ...
    edge_type: str | None = ...

@dataclass
class DSLRule:
    name: str
    role: str
    confidence: float
    conditions: list[DSLCondition]
    description: str | None = ...

@dataclass
class DSLRuleSet:
    rules: list[DSLRule] = field(default_factory=list)
