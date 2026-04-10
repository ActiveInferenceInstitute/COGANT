from _typeshed import Incomplete
from cogant.schemas.core import EdgeKind as EdgeKind, Node as Node, NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.schemas.semantic import MappingKind as MappingKind, SemanticMapping as SemanticMapping
from cogant.statespace.temporal import TemporalAnalyzer as TemporalAnalyzer, TimeRegime as TimeRegime
from cogant.statespace.variables import ConfidenceLevel as ConfidenceLevel, StateVariable as StateVariable, StateVariableExtractor as StateVariableExtractor
from dataclasses import dataclass, field
from typing import Any

logger: Incomplete

@dataclass
class ObservationModality:
    id: str
    name: str
    source_node_id: str
    modality_type: str
    cardinality: int | None = ...
    description: str | None = ...
    confidence: ConfidenceLevel = ...

@dataclass
class Action:
    id: str
    name: str
    controller_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    effects: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    description: str | None = ...
    confidence: ConfidenceLevel = ...

@dataclass
class Transition:
    id: str
    source_state: dict[str, Any]
    target_state: dict[str, Any]
    action_id: str | None = ...
    triggered_by: str | None = ...
    probability: float | None = ...
    confidence: ConfidenceLevel = ...

@dataclass
class Likelihood:
    id: str
    variable_id: str
    distribution_type: str
    parameters: dict[str, float] = field(default_factory=dict)
    confidence: ConfidenceLevel = ...

@dataclass
class Preference:
    id: str
    name: str
    description: str
    scope: list[str]
    expression: str
    weight: float = ...
    source: str | None = ...
    confidence: ConfidenceLevel = ...

@dataclass
class StateSpaceModel:
    id: str
    schema_name: str
    variables: dict[str, StateVariable]
    observations: dict[str, ObservationModality]
    actions: dict[str, Action]
    transitions: dict[str, Transition]
    likelihoods: dict[str, Likelihood]
    preferences: dict[str, Preference]
    time_regime: TimeRegime
    metadata: dict[str, Any] = field(default_factory=dict)

class StateSpaceCompiler:
    graph: Incomplete
    schema_name: Incomplete
    var_extractor: Incomplete
    temporal_analyzer: Incomplete
    def __init__(self, program_graph: ProgramGraph, schema_name: str) -> None: ...
    def compile(self, semantic_mappings: dict[str, SemanticMapping]) -> StateSpaceModel: ...
