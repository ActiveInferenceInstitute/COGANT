"""
Program flow diagram generation: control flow, call graphs, and dependency graphs.

Generates visual representations of:
- Control flow graphs (CFG) for individual functions
- Call graphs for project-wide function invocations
- Dependency graphs for module/file imports
- Mermaid flowcharts and sequence diagrams
- PNG and PDF exports via matplotlib backends
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import ProgramGraph

logger = logging.getLogger(__name__)


@dataclass
class ControlFlowGraph:
    """Control flow graph for a single function."""

    function_node: Node
    """The function this CFG represents."""

    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Basic block nodes: {block_id: {name, kind, ...}}."""

    edges: list[tuple[str, str, str]] = field(default_factory=list)
    """Edges as (source_id, target_id, edge_type: 'unconditional'|'conditional')."""

    entry_node_id: str | None = None
    """ID of entry block."""

    exit_node_ids: list[str] = field(default_factory=list)
    """IDs of exit blocks."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for export."""
        return {
            "function_id": self.function_node.id,
            "function_name": self.function_node.name,
            "nodes": self.nodes,
            "edges": self.edges,
            "entry": self.entry_node_id,
            "exits": self.exit_node_ids,
        }


@dataclass
class CallGraph:
    """Call graph for a program."""

    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Function nodes: {func_id: {name, kind, path, ...}}."""

    edges: list[tuple[str, str, dict[str, Any]]] = field(default_factory=list)
    """Edges as (source_id, target_id, {call_count, is_recursive, ...})."""

    entry_points: list[str] = field(default_factory=list)
    """IDs of functions with no incoming calls (entry points)."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for export."""
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "entry_points": self.entry_points,
        }


@dataclass
class DependencyGraph:
    """Module/file dependency graph for a program."""

    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Module nodes: {module_id: {name, kind, path, ...}}."""

    edges: list[tuple[str, str, dict[str, Any]]] = field(default_factory=list)
    """Edges as (source_id, target_id, {is_circular, depth, ...})."""

    root_modules: list[str] = field(default_factory=list)
    """IDs of top-level modules with no dependencies."""

    circular_modules: list[list[str]] = field(default_factory=list)
    """Cycles detected in the dependency graph."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for export."""
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "roots": self.root_modules,
            "cycles": self.circular_modules,
        }


class FlowDiagrammer:
    """Generate control flow, call, and dependency diagrams from program graphs."""

    def __init__(self) -> None:
        """Initialize the FlowDiagrammer."""
        pass

    def generate_cfg(self, function_node: Node, graph: ProgramGraph | None = None) -> ControlFlowGraph:
        """
        Generate a control flow graph for a single function.

        Args:
            function_node: The function node to generate CFG for.
            graph: Optional program graph for context (unused in basic implementation).

        Returns:
            ControlFlowGraph with entry/exit blocks and conditional edges.
        """
        cfg = ControlFlowGraph(function_node=function_node)

        # For now, create a simple single-block CFG
        # In a full implementation, this would parse AST and extract basic blocks
        block_id = f"{function_node.id}_entry"
        cfg.nodes[block_id] = {
            "id": block_id,
            "name": f"Entry: {function_node.name}",
            "kind": "basic_block",
        }
        cfg.entry_node_id = block_id
        cfg.exit_node_ids = [block_id]

        return cfg

    def generate_call_graph(self, program_graph: ProgramGraph) -> CallGraph:
        """
        Generate a call graph for the entire program.

        Args:
            program_graph: The program graph to analyze.

        Returns:
            CallGraph with function nodes and call edges.
        """
        call_graph = CallGraph()

        # Extract all functions
        functions = program_graph.get_nodes_by_kind(NodeKind.FUNCTION)
        for func in functions:
            call_graph.nodes[func.id] = {
                "id": func.id,
                "name": func.name,
                "kind": NodeKind.FUNCTION,
                "path": func.path,
                "qualified_name": func.qualified_name,
            }

        # Extract CALLS edges
        for edge in program_graph.edges.values():
            if edge.kind == EdgeKind.CALLS:
                source_node = program_graph.nodes.get(edge.source_id)
                target_node = program_graph.nodes.get(edge.target_id)

                if (
                    source_node
                    and target_node
                    and source_node.kind in (NodeKind.FUNCTION, NodeKind.METHOD)
                    and target_node.kind in (NodeKind.FUNCTION, NodeKind.METHOD)
                ):
                    call_count = edge.metadata.get("call_count", 1) if edge.metadata else 1
                    is_recursive = (
                        edge.metadata.get("is_recursive", False) if edge.metadata else False
                    )

                    call_graph.edges.append(
                        (
                            edge.source_id,
                            edge.target_id,
                            {"call_count": call_count, "is_recursive": is_recursive},
                        )
                    )

        # Find entry points (functions with no incoming calls)
        incoming: dict[str, int] = {}
        for _, target, _ in call_graph.edges:
            incoming[target] = incoming.get(target, 0) + 1

        for func_id in call_graph.nodes:
            if incoming.get(func_id, 0) == 0:
                call_graph.entry_points.append(func_id)

        return call_graph

    def generate_dependency_graph(self, program_graph: ProgramGraph) -> DependencyGraph:
        """
        Generate a module/file dependency graph.

        Args:
            program_graph: The program graph to analyze.

        Returns:
            DependencyGraph with module nodes and import edges.
        """
        dep_graph = DependencyGraph()

        # Extract modules and files
        modules = program_graph.get_nodes_by_kind(NodeKind.MODULE) + program_graph.get_nodes_by_kind(
            NodeKind.FILE
        )

        for mod in modules:
            dep_graph.nodes[mod.id] = {
                "id": mod.id,
                "name": mod.name,
                "kind": mod.kind,
                "path": mod.path,
                "qualified_name": mod.qualified_name,
            }

        # Extract IMPORTS edges
        for edge in program_graph.edges.values():
            if edge.kind == EdgeKind.IMPORTS:
                source_node = program_graph.nodes.get(edge.source_id)
                target_node = program_graph.nodes.get(edge.target_id)

                if (
                    source_node
                    and target_node
                    and source_node.kind in (NodeKind.MODULE, NodeKind.FILE)
                    and target_node.kind in (NodeKind.MODULE, NodeKind.FILE)
                ):
                    dep_graph.edges.append(
                        (
                            edge.source_id,
                            edge.target_id,
                            {"is_circular": False},
                        )
                    )

        # Find root modules (no incoming imports)
        incoming: dict[str, int] = {}
        for _, target, _ in dep_graph.edges:
            incoming[target] = incoming.get(target, 0) + 1

        for mod_id in dep_graph.nodes:
            if incoming.get(mod_id, 0) == 0:
                dep_graph.root_modules.append(mod_id)

        return dep_graph

    def to_mermaid_flowchart(self, cfg: ControlFlowGraph) -> str:
        """
        Render a control flow graph as a Mermaid flowchart.

        Args:
            cfg: The control flow graph to render.

        Returns:
            Mermaid flowchart syntax as string.
        """
        lines = ["flowchart TD"]

        # Render nodes
        for block_id, block_info in cfg.nodes.items():
            node_label = block_info.get("name", block_id)
            safe_id = block_id.replace("-", "_").replace(".", "_")
            lines.append(f'    {safe_id}["{node_label}"]')

        # Render edges
        for source_id, target_id, edge_type in cfg.edges:
            source_safe = source_id.replace("-", "_").replace(".", "_")
            target_safe = target_id.replace("-", "_").replace(".", "_")

            if edge_type == "conditional":
                lines.append(f"    {source_safe} -->|conditional| {target_safe}")
            else:
                lines.append(f"    {source_safe} --> {target_safe}")

        return "\n".join(lines)

    def to_mermaid_sequence(self, call_graph: CallGraph) -> str:
        """
        Render key call sequences as a Mermaid sequence diagram.

        Selects entry points and their immediate callees for readability.

        Args:
            call_graph: The call graph to render.

        Returns:
            Mermaid sequence diagram syntax as string.
        """
        lines = ["sequenceDiagram"]

        # Limit to entry points and their direct callees for clarity
        participants: set[str] = set()
        call_pairs: list[tuple[str, str]] = []

        for entry_id in call_graph.entry_points[:5]:  # Limit to first 5 entry points
            participants.add(entry_id)

            for source, target, _ in call_graph.edges:
                if source == entry_id:
                    participants.add(target)
                    call_pairs.append((entry_id, target))

        # Add participant declarations
        for participant_id in sorted(participants):
            participant_name = call_graph.nodes[participant_id]["name"]
            safe_name = participant_name.replace('"', '\\"')
            lines.append(f'    participant {safe_name}')

        # Add call sequences
        for source_id, target_id in call_pairs:
            source_name = call_graph.nodes[source_id]["name"].replace('"', '\\"')
            target_name = call_graph.nodes[target_id]["name"].replace('"', '\\"')
            lines.append(f'    {source_name}->>+{target_name}: call')
            lines.append(f'    {target_name}-->>-{source_name}: return')

        return "\n".join(lines) if len(lines) > 1 else "sequenceDiagram\n    participant None"

    def to_png(self, graph: ControlFlowGraph | CallGraph | DependencyGraph, output_path: str, dpi: int = 150) -> str:
        """
        Render a flow diagram to PNG.

        Requires matplotlib and networkx. Falls back gracefully if unavailable.

        Args:
            graph: The graph to render (CFG, CallGraph, or DependencyGraph).
            output_path: Path to write PNG file.
            dpi: Resolution in dots per inch.

        Returns:
            Path to rendered file, or empty string if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
        except ImportError:
            logger.warning("matplotlib or networkx not available; skipping PNG render")
            return ""

        # Create NetworkX graph
        G = nx.DiGraph()

        if isinstance(graph, ControlFlowGraph):
            for node_id, node_info in graph.nodes.items():
                G.add_node(node_id, label=node_info.get("name", node_id))

            for source, target, _ in graph.edges:
                G.add_edge(source, target)

        elif isinstance(graph, CallGraph):
            for node_id, node_info in graph.nodes.items():
                G.add_node(node_id, label=node_info.get("name", node_id))

            for source, target, _ in graph.edges:
                G.add_edge(source, target)

        elif isinstance(graph, DependencyGraph):
            for node_id, node_info in graph.nodes.items():
                G.add_node(node_id, label=node_info.get("name", node_id))

            for source, target, _ in graph.edges:
                G.add_edge(source, target)

        # Render
        try:
            fig, ax = plt.subplots(figsize=(14, 10), dpi=dpi)
            pos = nx.spring_layout(G, k=2, iterations=50)

            nx.draw_networkx_nodes(G, pos, node_color="lightblue", node_size=500, ax=ax)
            nx.draw_networkx_edges(G, pos, edge_color="gray", arrows=True, ax=ax)

            labels = {node: G.nodes[node].get("label", node) for node in G.nodes()}
            nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)

            ax.set_title(f"Flow Diagram: {type(graph).__name__}")
            fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Rendered flow diagram to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error rendering PNG: {e}")
            return ""

    def to_pdf(self, graph: ControlFlowGraph | CallGraph | DependencyGraph, output_path: str) -> str:
        """
        Render a flow diagram to PDF.

        Requires matplotlib and networkx. Falls back gracefully if unavailable.

        Args:
            graph: The graph to render (CFG, CallGraph, or DependencyGraph).
            output_path: Path to write PDF file.

        Returns:
            Path to rendered file, or empty string if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
        except ImportError:
            logger.warning("matplotlib or networkx not available; skipping PDF render")
            return ""

        # Create NetworkX graph
        G = nx.DiGraph()

        if isinstance(graph, ControlFlowGraph):
            for node_id, node_info in graph.nodes.items():
                G.add_node(node_id, label=node_info.get("name", node_id))

            for source, target, _ in graph.edges:
                G.add_edge(source, target)

        elif isinstance(graph, CallGraph):
            for node_id, node_info in graph.nodes.items():
                G.add_node(node_id, label=node_info.get("name", node_id))

            for source, target, _ in graph.edges:
                G.add_edge(source, target)

        elif isinstance(graph, DependencyGraph):
            for node_id, node_info in graph.nodes.items():
                G.add_node(node_id, label=node_info.get("name", node_id))

            for source, target, _ in graph.edges:
                G.add_edge(source, target)

        # Render
        try:
            fig, ax = plt.subplots(figsize=(14, 10))
            pos = nx.spring_layout(G, k=2, iterations=50)

            nx.draw_networkx_nodes(G, pos, node_color="lightblue", node_size=500, ax=ax)
            nx.draw_networkx_edges(G, pos, edge_color="gray", arrows=True, ax=ax)

            labels = {node: G.nodes[node].get("label", node) for node in G.nodes()}
            nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)

            ax.set_title(f"Flow Diagram: {type(graph).__name__}")
            fig.savefig(output_path, format="pdf", bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Rendered flow diagram to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error rendering PDF: {e}")
            return ""
