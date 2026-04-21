from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cogant.schemas.graph import ProgramGraph as ProgramGraph

@dataclass
class GraphDiff:
    added_nodes: list[str]
    removed_nodes: list[str]
    changed_nodes: dict[str, dict[str, Any]]
    added_edges: list[tuple[str, str]]
    removed_edges: list[tuple[str, str]]

@dataclass
class MergeConflict:
    conflict_type: str
    source_graph: str
    entity_id: str
    details: dict[str, Any]
    resolution: str | None = ...

@dataclass
class MergeProvenance:
    timestamp: datetime
    source_graphs: list[str]
    conflicts: list[MergeConflict]
    edges_added: int = ...
    edges_updated: int = ...
    nodes_added: int = ...

class GraphMerger:
    merge_history: list[MergeProvenance]
    def __init__(self) -> None: ...
    def merge(
        self, graphs: list[ProgramGraph], conflict_resolution: str = "union"
    ) -> ProgramGraph: ...
    def merge_graphs(
        self,
        static_graph: ProgramGraph,
        dynamic_graph: ProgramGraph,
        conflict_resolution: str = "union",
    ) -> tuple[ProgramGraph, MergeProvenance]: ...
    def merge_multiple_graphs(self, graphs: list[tuple[str, ProgramGraph]]) -> ProgramGraph: ...
    def get_merge_statistics(self) -> dict[str, Any]: ...
    def merge_incremental(self, base: ProgramGraph, delta: ProgramGraph) -> ProgramGraph: ...
    def diff(self, g1: ProgramGraph, g2: ProgramGraph) -> GraphDiff: ...
