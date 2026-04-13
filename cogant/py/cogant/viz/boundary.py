"""
Boundary mapping and analysis for program graphs.

Identifies module boundaries, type boundaries, and cross-boundary couplings.
"""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, cast

from cogant.schemas.core import Edge, EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph

if TYPE_CHECKING:
    from cogant.markov.extractor import SeedStrategy

logger = logging.getLogger(__name__)


class BoundaryMapper:
    """Analyze and visualize module and type boundaries."""

    def __init__(self) -> None:
        """Initialize the BoundaryMapper."""
        pass

    def map_module_boundaries(self, graph: ProgramGraph) -> str:
        """
        Generate Mermaid diagram showing module boundaries with rich detail.

        Shows class groupings within modules, cross-class call edges,
        and annotates with edge counts.

        Args:
            graph: ProgramGraph to analyze.

        Returns:
            Mermaid graph syntax string.
        """
        # Get all modules
        modules = graph.get_nodes_by_kind(NodeKind.MODULE)
        {node.id: node for node in modules}

        lines = ["graph TD"]

        # Track cross-module edges for annotation
        cross_module_edge_counts: dict[tuple[str, str], int] = defaultdict(int)

        # Add module clusters with classes inside
        for module in modules:
            safe_id = module.id.replace("-", "_").replace(".", "_")
            label = module.name or module.qualified_name
            lines.append(f"    subgraph {safe_id}['{label}']")

            # Get classes in this module. ``get_node`` may return
            # ``None`` for dangling edges, so filter explicitly before
            # using attributes on the narrowed result.
            classes = []
            for edge in graph.get_edges_from(module.id):
                if edge.kind != EdgeKind.CONTAINS:
                    continue
                target = graph.get_node(edge.target_id)
                if target is not None and target.kind == NodeKind.CLASS:
                    classes.append(target)

            # Add class subgraphs within modules
            for cls in classes:
                cls_safe = cls.id.replace("-", "_").replace(".", "_")
                lines.append(f"        subgraph {cls_safe}['{cls.name}']")

                # Get methods/functions in this class
                methods = []
                for edge in graph.get_edges_from(cls.id):
                    if edge.kind != EdgeKind.CONTAINS:
                        continue
                    target = graph.get_node(edge.target_id)
                    if target is not None:
                        methods.append(target)

                for method in methods[:3]:  # Limit to 3 methods per class
                    method_safe = method.id.replace("-", "_").replace(".", "_")
                    lines.append(f"            {method_safe}['{method.name}']")

                lines.append("        end")

            lines.append("    end")

        # Add cross-class call edges
        cross_class_edges: list[Edge] = []
        for edge in graph.edges.values():
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)
            if source and target:
                # Find containing classes
                source_class = self._find_containing_class(source.id, graph)
                target_class = self._find_containing_class(target.id, graph)
                if (
                    source_class and target_class and source_class != target_class
                    and edge.kind == EdgeKind.CALLS
                ):
                    cross_class_edges.append(edge)

        # Annotate with edge counts
        for edge in cross_class_edges[:15]:  # Limit to 15 edges
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)
            if source and target:
                source_safe = source.id.replace("-", "_").replace(".", "_")
                target_safe = target.id.replace("-", "_").replace(".", "_")
                edge_key = (source_safe, target_safe)
                cross_module_edge_counts[edge_key] += 1

        # Draw cross-module edges
        cross_module_edges: list[Edge] = []
        for edge in graph.edges.values():
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)
            if source and target:
                source_module = self._find_containing_module(source.id, graph)
                target_module = self._find_containing_module(target.id, graph)
                if source_module and target_module and source_module != target_module:
                    if edge.kind in (
                        EdgeKind.IMPORTS,
                        EdgeKind.DEPENDS_ON,
                        EdgeKind.CALLS,
                    ):
                        cross_module_edges.append(edge)

        # Draw cross-module edges with counts
        for edge in cross_module_edges[:20]:  # Limit to 20 edges
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)
            if source and target:
                source_safe = source.id.replace("-", "_").replace(".", "_")
                target_safe = target.id.replace("-", "_").replace(".", "_")
                edge_label = edge.kind.value
                weight = f" |{int(edge.weight)}|" if hasattr(edge, 'weight') and edge.weight > 1 else ""
                lines.append(f"    {source_safe} -->|{edge_label}{weight}| {target_safe}")

        return "\n".join(lines)

    def _find_containing_class(
        self, node_id: str, graph: ProgramGraph
    ) -> str | None:
        """
        Find the class that contains a given node.

        Args:
            node_id: ID of the node.
            graph: ProgramGraph to search.

        Returns:
            Class node ID if found, None otherwise.
        """
        for edge in graph.edges.values():
            if edge.target_id == node_id and edge.kind == EdgeKind.CONTAINS:
                target = graph.get_node(edge.source_id)
                if target and target.kind == NodeKind.CLASS:
                    return edge.source_id
        return None

    def map_type_boundaries(self, graph: ProgramGraph) -> str:
        """
        Generate diagram grouping nodes by type (CLASS/FUNCTION/MODULE) with inter-group edges.

        Args:
            graph: ProgramGraph to analyze.

        Returns:
            Mermaid graph syntax string.
        """
        # Group nodes by type
        classes = graph.get_nodes_by_kind(NodeKind.CLASS)
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        modules = graph.get_nodes_by_kind(NodeKind.MODULE)

        lines = ["graph TD"]

        # Add class cluster
        if classes:
            lines.append("    subgraph Classes")
            for cls in classes[:5]:  # Limit to top 5 for readability
                safe_id = cls.id.replace("-", "_")
                lines.append(f"        {safe_id}['{cls.name}']")
            if len(classes) > 5:
                lines.append(f"        ... ['... and {len(classes) - 5} more classes']")
            lines.append("    end")

        # Add function cluster
        if functions:
            lines.append("    subgraph Functions")
            for func in functions[:5]:
                safe_id = func.id.replace("-", "_")
                lines.append(f"        {safe_id}['{func.name}']")
            if len(functions) > 5:
                lines.append(f"        ... ['... and {len(functions) - 5} more functions']")
            lines.append("    end")

        # Add module cluster
        if modules:
            lines.append("    subgraph Modules")
            for mod in modules[:5]:
                safe_id = mod.id.replace("-", "_")
                lines.append(f"        {safe_id}['{mod.name}']")
            if len(modules) > 5:
                lines.append(f"        ... ['... and {len(modules) - 5} more modules']")
            lines.append("    end")

        # Add inter-type edges
        inter_type_edges = self._find_inter_type_edges(graph)
        for edge in inter_type_edges[:10]:  # Limit to top 10
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)
            if source and target:
                source_safe = source.id.replace("-", "_")
                target_safe = target.id.replace("-", "_")
                lines.append(f"    {source_safe} -->|{edge.kind.value}| {target_safe}")

        return "\n".join(lines)

    def generate_boundary_report(self, graph: ProgramGraph) -> dict[str, Any]:
        """
        Generate metrics on boundary crossings and coupling scores.

        Args:
            graph: ProgramGraph to analyze.

        Returns:
            Dict with keys: "total_boundary_crossings", "module_coupling_matrix",
            "type_coupling_score", "external_dependencies".
        """
        report: dict[str, Any] = {}

        # Count boundary crossings
        boundary_crossings = 0
        crossing_by_type: dict[str, int] = defaultdict(int)

        for edge in graph.edges.values():
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)
            if source and target:
                source_module = self._find_containing_module(source.id, graph)
                target_module = self._find_containing_module(target.id, graph)
                if source_module and target_module and source_module != target_module:
                    boundary_crossings += 1
                    crossing_by_type[edge.kind.value] += 1

        report["total_boundary_crossings"] = boundary_crossings

        # Module coupling matrix
        modules = graph.get_nodes_by_kind(NodeKind.MODULE)
        module_names = {node.id: node.name for node in modules}

        coupling_matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for edge in graph.edges.values():
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)
            if source and target:
                source_module = self._find_containing_module(source.id, graph)
                target_module = self._find_containing_module(target.id, graph)
                if source_module and target_module and source_module != target_module:
                    source_name = module_names.get(source_module, "Unknown")
                    target_name = module_names.get(target_module, "Unknown")
                    coupling_matrix[source_name][target_name] += 1

        report["module_coupling_matrix"] = dict(coupling_matrix)
        report["edge_type_distribution"] = dict(crossing_by_type)

        # Type coupling score (0-1): ratio of inter-type edges to total edges
        type_edges = self._find_inter_type_edges(graph)
        type_coupling_score = (
            len(type_edges) / len(graph.edges) if graph.edges else 0
        )
        report["type_coupling_score"] = round(type_coupling_score, 3)

        # External dependencies (edges going out of repo)
        external_deps = [
            edge
            for edge in graph.edges.values()
            if edge.kind == EdgeKind.IMPORTS
            and (
                edge.metadata.get("external", False)
                or "external" in edge.metadata.get("evidence_sources", [])
            )
        ]
        report["external_dependencies_count"] = len(external_deps)

        return report

    def _find_containing_module(
        self, node_id: str, graph: ProgramGraph
    ) -> str | None:
        """
        Find the module that contains a given node.

        Args:
            node_id: ID of the node.
            graph: ProgramGraph to search.

        Returns:
            Module node ID if found, None otherwise.
        """
        # Check if node has a "contained by" edge pointing to a module
        for edge in graph.edges.values():
            if (
                edge.target_id == node_id
                and edge.kind == EdgeKind.CONTAINS
            ):
                target = graph.get_node(edge.source_id)
                if target and target.kind == NodeKind.MODULE:
                    return edge.source_id

        # Try to infer from path
        node = graph.get_node(node_id)
        if node and node.path:
            parts = node.path.split("/")
            if len(parts) > 1:
                # First part is often module
                possible_module = parts[0]
                for m in graph.get_nodes_by_kind(NodeKind.MODULE):
                    if possible_module in m.name or m.name in possible_module:
                        return m.id

        return None

    def _find_inter_type_edges(self, graph: ProgramGraph) -> list[Edge]:
        """
        Find edges that cross type boundaries (CLASS, FUNCTION, MODULE).

        Args:
            graph: ProgramGraph to analyze.

        Returns:
            List of inter-type edges.
        """
        inter_type_edges = []
        type_categories = {
            NodeKind.CLASS: "class",
            NodeKind.FUNCTION: "function",
            NodeKind.METHOD: "function",
            NodeKind.MODULE: "module",
        }

        for edge in graph.edges.values():
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)
            if source and target:
                source_type = type_categories.get(source.kind)
                target_type = type_categories.get(target.kind)
                if source_type and target_type and source_type != target_type:
                    inter_type_edges.append(edge)

        return inter_type_edges

    # ------------------------------------------------------------------ #
    # Markov blanket visualization                                        #
    # ------------------------------------------------------------------ #

    def markov_blanket_collapsed_mermaid(
        self,
        graph: ProgramGraph,
        blanket: Any = None,
        *,
        strategy: str = "auto",
        **extract_kwargs: Any,
    ) -> str:
        """Render the four-role collapsed view of a Markov blanket.

        This is a thin wrapper over
        :meth:`cogant.markov.BlanketNetwork.to_mermaid` that also accepts
        an uncomputed graph and extracts the blanket on the fly.

        Args:
            graph: The program graph.
            blanket: An already-computed
                :class:`~cogant.markov.MarkovBlanket`. If ``None`` a new
                one will be extracted using ``strategy`` and any
                ``extract_kwargs``.
            strategy: Seed strategy to use when ``blanket`` is ``None``.
            **extract_kwargs: Forwarded to
                :meth:`~cogant.markov.MarkovBlanketExtractor.extract`.

        Returns:
            A Mermaid ``graph LR`` block with four nodes — μ, s, a, η —
            labelled by role counts and linked by aggregate edge counts.
        """
        from cogant.markov import (
            MarkovBlanketExtractor,
            build_blanket_network,
        )

        if blanket is None:
            extractor = MarkovBlanketExtractor(graph)
            blanket = extractor.extract(
                strategy=cast("SeedStrategy", strategy), **extract_kwargs
            )
        network = build_blanket_network(graph, blanket)
        return network.to_mermaid()

    def markov_blanket_detailed_mermaid(
        self,
        graph: ProgramGraph,
        blanket: Any = None,
        *,
        strategy: str = "auto",
        max_per_role: int = 12,
        **extract_kwargs: Any,
    ) -> str:
        """Render a detailed Mermaid diagram of the Markov blanket.

        The detailed view draws each role as a ``subgraph`` and places
        the (optionally capped) individual node members inside. Edges
        between member nodes are drawn as well, so the user can see the
        actual boundary topology rather than the collapsed counts.

        Nodes are styled by role so the internal / sensory / active /
        external partition is visible at a glance.

        Args:
            graph: The program graph.
            blanket: Optional precomputed
                :class:`~cogant.markov.MarkovBlanket`.
            strategy: Seed strategy when ``blanket`` is ``None``.
            max_per_role: Upper bound on the number of nodes to draw
                per role (deterministic: sorted by id). Roles with more
                members will show a ``+N more`` placeholder node.
            **extract_kwargs: Forwarded to
                :meth:`~cogant.markov.MarkovBlanketExtractor.extract`.

        Returns:
            A Mermaid ``graph LR`` block.
        """
        from cogant.markov import MarkovBlanketExtractor

        if blanket is None:
            extractor = MarkovBlanketExtractor(graph)
            blanket = extractor.extract(
                strategy=cast("SeedStrategy", strategy), **extract_kwargs
            )

        def _safe(nid: str) -> str:
            return "n_" + nid.replace("-", "_").replace(".", "_").replace(":", "_")

        def _label(nid: str) -> str:
            node = graph.get_node(nid)
            if node is None:
                return nid
            name = (node.name or node.qualified_name or nid).replace('"', "'")
            kind = node.kind.value if hasattr(node.kind, "value") else str(node.kind)
            return f"{name} :{kind}"

        role_members: dict[str, list[str]] = {
            "internal": sorted(blanket.internal_ids),
            "sensory": sorted(blanket.sensory_ids),
            "active": sorted(blanket.active_ids),
            "external": sorted(blanket.external_ids),
        }
        role_titles = {
            "internal": "μ internal",
            "sensory": "s sensory",
            "active": "a active",
            "external": "η external",
        }

        lines = ["graph LR"]
        drawn: set[str] = set()
        for role, members in role_members.items():
            total = len(members)
            shown = members[:max_per_role]
            lines.append(f"    subgraph {role}[\"{role_titles[role]} ({total})\"]")
            for nid in shown:
                node_id = _safe(nid)
                lines.append(f"        {node_id}[\"{_label(nid)}\"]")
                drawn.add(nid)
            if total > max_per_role:
                placeholder = f"more_{role}"
                lines.append(
                    f"        {placeholder}([\"+{total - max_per_role} more\"])"
                )
            lines.append("    end")

        # Draw edges between drawn members.
        for edge in graph.edges.values():
            if edge.source_id in drawn and edge.target_id in drawn:
                src = _safe(edge.source_id)
                dst = _safe(edge.target_id)
                kind = edge.kind.value if hasattr(edge.kind, "value") else str(edge.kind)
                lines.append(f"    {src} -->|{kind}| {dst}")

        # Style nodes by role.
        role_styles = {
            "internal": "fill:#d8efff,stroke:#3a6aa8",
            "sensory": "fill:#fff4d0,stroke:#b48a1e",
            "active": "fill:#d9f2d7,stroke:#3a8a3a",
            "external": "fill:#f1d9d9,stroke:#a03a3a",
        }
        for role, style in role_styles.items():
            lines.append(f"    classDef {role} {style}")
            members = role_members[role][:max_per_role]
            if members:
                ids = ",".join(_safe(nid) for nid in members)
                lines.append(f"    class {ids} {role}")

        return "\n".join(lines)
