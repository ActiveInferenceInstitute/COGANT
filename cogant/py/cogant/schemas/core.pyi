from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

class NodeKind(StrEnum):
    REPO = 'repo'
    MODULE = 'module'
    FILE = 'file'
    CLASS = 'class'
    FUNCTION = 'function'
    METHOD = 'method'
    VARIABLE = 'variable'
    ENDPOINT = 'endpoint'
    EVENT = 'event'
    PARAMETER = 'parameter'
    RETURN_VALUE = 'return_value'
    DATA_STRUCTURE = 'data_structure'
    CONFIGURATION = 'configuration'
    FEATURE_FLAG = 'feature_flag'
    TEST = 'test'
    ASSERTION = 'assertion'
    POLICY = 'policy'
    ACTION = 'action'

class EdgeKind(StrEnum):
    CONTAINS = 'contains'
    IMPORTS = 'imports'
    INHERITS = 'inherits'
    IMPLEMENTS = 'implements'
    DEPENDS_ON = 'depends_on'
    READS = 'reads'
    WRITES = 'writes'
    RETURNS = 'returns'
    CALLS = 'calls'
    THROWS = 'throws'
    CATCHES = 'catches'
    YIELDS = 'yields'
    OBSERVES = 'observes'
    MUTATES = 'mutates'
    GUARDS = 'guards'
    TRIGGERS = 'triggers'
    EVIDENCE_FROM_STATIC = 'evidence_from_static'
    EVIDENCE_FROM_DYNAMIC = 'evidence_from_dynamic'

@dataclass
class Node:
    id: str
    kind: NodeKind
    name: str
    qualified_name: str
    path: str | None = ...
    language: str | None = ...
    source_range: dict[str, Any] | None = ...
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=Incomplete)
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...

@dataclass
class Edge:
    id: str
    source_id: str
    target_id: str
    kind: EdgeKind
    weight: float = ...
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence_sources: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=Incomplete)
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
