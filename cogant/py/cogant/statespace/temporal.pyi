from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cogant.schemas.graph import ProgramGraph as ProgramGraph

class TimeRegime(StrEnum):
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    EVENT_DRIVEN = "event_driven"
    HYBRID = "hybrid"

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
    graph: Any
    time_regime: Any
    orderings: list[TemporalOrdering]
    event_patterns: list[EventPattern]
    metrics: TemporalMetrics | None
    def __init__(self, program_graph: ProgramGraph) -> None: ...
    def analyze(self) -> TimeRegime: ...
    def get_ordering_constraints(self) -> list[TemporalOrdering]: ...
    def get_event_patterns(self) -> list[EventPattern]: ...
    def get_metrics(self) -> TemporalMetrics | None: ...
    def get_critical_path(self) -> list[str]: ...
    def compute_critical_path(self) -> list[str]: ...
    def get_markov_order(self) -> int: ...
    def find_feedback_loops(self) -> list[list[str]]: ...
    def to_mermaid(self) -> str: ...
