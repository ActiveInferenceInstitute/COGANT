from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cogant.schemas.graph import ProgramGraph

@dataclass
class GraphMetrics:
    node_count: int
    edge_count: int
    density: float
    avg_degree: float
    max_degree: int
    connected_components: int
    is_dag: bool
    diameter: int | None
    clustering_coefficient: float

@dataclass
class CentralityScores:
    betweenness_centrality: dict[str, float]
    degree_centrality: dict[str, float]
    pagerank: dict[str, float]
    closeness_centrality: dict[str, float]

@dataclass
class CycleDetection:
    has_cycles: bool
    cycles: list[list[str]]
    strongly_connected_components: list[frozenset[str]]

@dataclass
class PathAnalysis:
    shortest_path: list[str] | None
    all_paths: list[list[str]]
    critical_path: list[str]

@dataclass
class HotspotAnalysis:
    hubs: list[tuple[str, int]]
    bottlenecks: list[tuple[str, float]]
    sinks: list[str]
    sources: list[str]

class GraphAnalyzer:
    def __init__(self, graph: ProgramGraph) -> None: ...
    def compute_metrics(self) -> GraphMetrics: ...
    def compute_centrality(self) -> CentralityScores: ...
    def find_communities(self) -> list[frozenset[str]]: ...
    def find_cycles(self) -> CycleDetection: ...
    def find_hotspots(self, top_n: int = 10) -> HotspotAnalysis: ...
    def get_subgraph(self, nodes: set[str]) -> ProgramGraph: ...
    def to_networkx(self) -> Any: ...
    def to_adjacency_matrix(self) -> list[list[int]]: ...
    def summary(self) -> dict[str, Any]: ...
