from dataclasses import dataclass
from enum import StrEnum

from _typeshed import Incomplete as Incomplete

from cogant.schemas.graph import ProgramGraph as ProgramGraph

logger: Incomplete

class TimeRegime(StrEnum):
    SYNCHRONOUS = 'synchronous'
    ASYNCHRONOUS = 'asynchronous'
    EVENT_DRIVEN = 'event_driven'
    HYBRID = 'hybrid'

@dataclass
class TemporalOrdering:
    predecessor_id: str
    successor_id: str
    constraint_type: str
    confidence: float

@dataclass
class EventPattern:
    event_node_id: str
    trigger_nodes: list[str]
    handler_nodes: list[str]
    is_async: bool = ...

@dataclass
class TemporalMetrics:
    async_fraction: float
    event_driven_fraction: float
    parallel_edges_count: int
    sequential_edges_count: int
    event_patterns_count: int
    has_async_handlers: bool
    has_event_triggers: bool
    has_loops: bool = ...
    is_discrete: bool = ...

class TemporalAnalyzer:
    graph: Incomplete
    time_regime: Incomplete
    orderings: list[TemporalOrdering]
    event_patterns: list[EventPattern]
    metrics: TemporalMetrics | None
    def __init__(self, program_graph: ProgramGraph) -> None: ...
    def analyze(self) -> TimeRegime: ...
    def get_ordering_constraints(self) -> list[TemporalOrdering]: ...
    def get_event_patterns(self) -> list[EventPattern]: ...
    def get_metrics(self) -> TemporalMetrics | None: ...
    def get_critical_path(self) -> list[str]: ...
