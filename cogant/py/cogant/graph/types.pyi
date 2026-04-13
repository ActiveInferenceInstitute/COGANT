from __future__ import annotations

from typing import TypedDict

__all__: list[str]

class GraphStats(TypedDict, total=False):
    node_count: int
    edge_count: int
    density: float
    is_dag: bool
    component_count: int

CentralityDict: type[dict[str, float]]
CommunityList: type[list[frozenset[str]]]
PathList: type[list[list[str]]]
AdjacencyMatrix: type[list[list[int]]]
