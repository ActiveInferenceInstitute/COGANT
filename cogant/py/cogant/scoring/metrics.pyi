from dataclasses import dataclass
from typing import Any

from _typeshed import Incomplete as Incomplete

logger: Incomplete

@dataclass
class MetricsReport:
    complexity_score: float
    coupling_score: float
    cohesion_score: float
    semantic_coverage: float
    observability_score: float
    controllability_score: float
    node_count: int
    edge_count: int
    state_var_count: int
    observation_count: int
    action_count: int

class CodebaseMetrics:
    graph: Incomplete
    state_space: Incomplete
    mappings: Incomplete
    nodes: Incomplete
    edges: Incomplete
    state_vars: Incomplete
    observations: Incomplete
    actions: Incomplete
    def __init__(self, graph: dict[str, Any], state_space: dict[str, Any], mappings: dict[str, Any]) -> None: ...
    def complexity_score(self) -> float: ...
    def coupling_score(self) -> float: ...
    def cohesion_score(self) -> float: ...
    def semantic_coverage(self) -> float: ...
    def observability_score(self) -> float: ...
    def controllability_score(self) -> float: ...
    def summary(self) -> MetricsReport: ...
    def format_report(self) -> str: ...
    def to_dict(self) -> dict[str, Any]: ...
