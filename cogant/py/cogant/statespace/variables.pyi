from _typeshed import Incomplete
from cogant.schemas.core import EdgeKind as EdgeKind, Node as Node, NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.schemas.semantic import MappingKind as MappingKind, SemanticMapping as SemanticMapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger: Incomplete

class StateVariableType(StrEnum):
    BOOLEAN = 'boolean'
    DISCRETE = 'discrete'
    CONTINUOUS = 'continuous'
    CATEGORICAL = 'categorical'
    VECTOR = 'vector'
    COMPOSITE = 'composite'

class ConfidenceLevel(StrEnum):
    DEFINITE = 'definite'
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'
    UNCERTAIN = 'uncertain'

@dataclass
class StateVariable:
    id: str
    name: str
    var_type: StateVariableType
    node_id: str
    cardinality: int | None = ...
    domain: list[Any] | None = ...
    factors: list[str] | None = ...
    is_discrete: bool = ...
    confidence: ConfidenceLevel = ...
    description: str | None = ...
    mutations: list[str] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)
    observable: bool = ...

@dataclass
class FactorizationInfo:
    factors: list[str]
    independence_score: float
    dependencies: dict[str, list[str]]

class StateVariableExtractor:
    graph: Incomplete
    state_variables: dict[str, StateVariable]
    factorization_map: dict[str, FactorizationInfo]
    def __init__(self, program_graph: ProgramGraph) -> None: ...
    def extract(self, semantic_mappings: dict[str, SemanticMapping]) -> dict[str, StateVariable]: ...
    def get_state_variables(self) -> dict[str, StateVariable]: ...
    def get_factorization(self, var_id: str) -> FactorizationInfo | None: ...
    def compute_dimensionality(self) -> int: ...
