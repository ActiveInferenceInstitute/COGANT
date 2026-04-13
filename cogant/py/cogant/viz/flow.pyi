from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cogant.schemas.core import Node
from cogant.schemas.graph import ProgramGraph

@dataclass
class ControlFlowGraph:
    function_node: Node
    nodes: dict[str, dict[str, Any]]
    edges: list[tuple[str, str, str]]
    entry_node_id: str | None
    exit_node_ids: list[str]
    def to_dict(self) -> dict[str, Any]: ...

@dataclass
class CallGraph:
    nodes: dict[str, dict[str, Any]]
    edges: list[tuple[str, str, dict[str, Any]]]
    entry_points: list[str]
    def to_dict(self) -> dict[str, Any]: ...

@dataclass
class DependencyGraph:
    nodes: dict[str, dict[str, Any]]
    edges: list[tuple[str, str, dict[str, Any]]]
    root_modules: list[str]
    circular_modules: list[list[str]]
    def to_dict(self) -> dict[str, Any]: ...

class FlowDiagrammer:
    def __init__(self) -> None: ...
    def generate_cfg(
        self, function_node: Node, graph: ProgramGraph | None = None
    ) -> ControlFlowGraph: ...
    def generate_call_graph(self, program_graph: ProgramGraph) -> CallGraph: ...
    def generate_dependency_graph(self, program_graph: ProgramGraph) -> DependencyGraph: ...
    def to_mermaid_flowchart(self, cfg: ControlFlowGraph) -> str: ...
    def to_mermaid_sequence(self, call_graph: CallGraph) -> str: ...
    def to_png(
        self,
        graph: ControlFlowGraph | CallGraph | DependencyGraph,
        output_path: str,
        dpi: int = 150,
    ) -> str: ...
    def to_pdf(
        self, graph: ControlFlowGraph | CallGraph | DependencyGraph, output_path: str
    ) -> str: ...
