"""Graph merging for combining static and dynamic evidence graphs."""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

from cogant.schemas.core import Node, Edge, EdgeKind
from cogant.schemas.graph import ProgramGraph, GraphMetadata


@dataclass
class MergeConflict:
    """Record of a merge conflict."""

    conflict_type: str
    """Type of conflict (edge_weight_mismatch, evidence_divergence, etc.)."""

    source_graph: str
    """Which graph the conflict originated from."""

    entity_id: str
    """ID of the conflicting entity."""

    details: Dict[str, Any]
    """Conflict details."""

    resolution: Optional[str] = None
    """How the conflict was resolved."""


@dataclass
class MergeProvenance:
    """Record of merge operations and provenance."""

    timestamp: datetime
    """When the merge occurred."""

    source_graphs: List[str]
    """Names of merged graphs."""

    conflicts: List[MergeConflict]
    """Conflicts encountered."""

    edges_added: int = 0
    """Number of edges added."""

    edges_updated: int = 0
    """Number of edges updated."""

    nodes_added: int = 0
    """Number of nodes added."""


class GraphMerger:
    """Merges multiple program graphs while handling conflicts and recording provenance."""

    def __init__(self):
        """Initialize the graph merger."""
        self.merge_history: List[MergeProvenance] = []

    def merge(self, graphs: List[ProgramGraph], conflict_resolution: str = "union") -> ProgramGraph:
        """Merge multiple graphs into one (convenience method).

        Args:
            graphs: List of ProgramGraphs to merge.
            conflict_resolution: Strategy for conflicts ("union", "static_priority", "dynamic_priority").

        Returns:
            Merged ProgramGraph.
        """
        if not graphs:
            raise ValueError("Must provide at least one graph to merge")

        if len(graphs) == 1:
            return graphs[0]

        # Merge graphs pairwise
        result = graphs[0]
        for i in range(1, len(graphs)):
            result, _ = self.merge_graphs(result, graphs[i], conflict_resolution)

        return result

    def merge_graphs(
        self,
        static_graph: ProgramGraph,
        dynamic_graph: ProgramGraph,
        conflict_resolution: str = "union",
    ) -> Tuple[ProgramGraph, MergeProvenance]:
        """Merge static and dynamic graphs.

        Args:
            static_graph: Graph from static analysis.
            dynamic_graph: Graph from dynamic/runtime analysis.
            conflict_resolution: Strategy for conflicts ("union", "static_priority", "dynamic_priority").

        Returns:
            Tuple of (merged graph, merge provenance).
        """
        merged = ProgramGraph(metadata=self._merge_metadata(static_graph, dynamic_graph))

        provenance = MergeProvenance(
            timestamp=datetime.now(timezone.utc),
            source_graphs=["static", "dynamic"],
            conflicts=[],
        )

        # Merge nodes
        nodes_added = self._merge_nodes(static_graph, dynamic_graph, merged)
        provenance.nodes_added = nodes_added

        # Merge edges
        edges_added, edges_updated, conflicts = self._merge_edges(
            static_graph,
            dynamic_graph,
            merged,
            conflict_resolution,
        )
        provenance.edges_added = edges_added
        provenance.edges_updated = edges_updated
        provenance.conflicts = conflicts

        self.merge_history.append(provenance)

        return merged, provenance

    def _merge_metadata(
        self,
        static_graph: ProgramGraph,
        dynamic_graph: ProgramGraph,
    ) -> GraphMetadata:
        """Merge graph metadata.

        Args:
            static_graph: Static analysis graph.
            dynamic_graph: Dynamic analysis graph.

        Returns:
            Merged metadata.
        """
        merged_metadata = GraphMetadata(
            repo_uri=static_graph.metadata.repo_uri,
        )

        # Combine languages
        merged_metadata.languages = (
            static_graph.metadata.languages | dynamic_graph.metadata.languages
        )

        # Combine evidence sources
        evidence_sources = set(static_graph.metadata.evidence_sources)
        evidence_sources.update(dynamic_graph.metadata.evidence_sources)
        merged_metadata.evidence_sources = list(evidence_sources)

        return merged_metadata

    def _merge_nodes(
        self,
        static_graph: ProgramGraph,
        dynamic_graph: ProgramGraph,
        merged: ProgramGraph,
    ) -> int:
        """Merge nodes from both graphs.

        Args:
            static_graph: Static graph.
            dynamic_graph: Dynamic graph.
            merged: Merged graph to populate.

        Returns:
            Number of nodes added.
        """
        nodes_added = 0

        # Add all nodes from static graph
        for node in static_graph.nodes.values():
            merged.add_node(node)
            nodes_added += 1

        # Add nodes from dynamic graph not in static
        for node in dynamic_graph.nodes.values():
            if node.id not in merged.nodes:
                merged.add_node(node)
                nodes_added += 1

        return nodes_added

    def _merge_edges(
        self,
        static_graph: ProgramGraph,
        dynamic_graph: ProgramGraph,
        merged: ProgramGraph,
        conflict_resolution: str,
    ) -> Tuple[int, int, List[MergeConflict]]:
        """Merge edges from both graphs, handling conflicts.

        Args:
            static_graph: Static graph.
            dynamic_graph: Dynamic graph.
            merged: Merged graph to populate.
            conflict_resolution: Conflict resolution strategy.

        Returns:
            Tuple of (edges_added, edges_updated, conflicts).
        """
        edges_added = 0
        edges_updated = 0
        conflicts: List[MergeConflict] = []

        # Add edges from static graph
        for edge in static_graph.edges.values():
            if edge.source_id in merged.nodes and edge.target_id in merged.nodes:
                merged.add_edge(edge)
                edges_added += 1

        # Merge edges from dynamic graph
        for dynamic_edge in dynamic_graph.edges.values():
            if dynamic_edge.source_id not in merged.nodes or dynamic_edge.target_id not in merged.nodes:
                continue

            # Check if edge exists in merged graph
            existing_edge = None
            for merged_edge in merged.edges.values():
                if (merged_edge.source_id == dynamic_edge.source_id and
                    merged_edge.target_id == dynamic_edge.target_id and
                    merged_edge.kind == dynamic_edge.kind):
                    existing_edge = merged_edge
                    break

            if existing_edge:
                # Handle conflict
                conflict = self._resolve_edge_conflict(
                    existing_edge,
                    dynamic_edge,
                    conflict_resolution,
                )

                if conflict:
                    conflicts.append(conflict)
                    edges_updated += 1
                else:
                    # No conflict, merge evidence
                    if dynamic_edge.evidence_sources:
                        for source in dynamic_edge.evidence_sources:
                            if source not in existing_edge.evidence_sources:
                                existing_edge.evidence_sources.append(source)
                    # Update weight to be maximum
                    existing_edge.weight = max(existing_edge.weight, dynamic_edge.weight)
                    edges_updated += 1
            else:
                # New edge
                merged.add_edge(dynamic_edge)
                edges_added += 1

        return edges_added, edges_updated, conflicts

    def _resolve_edge_conflict(
        self,
        static_edge: Edge,
        dynamic_edge: Edge,
        strategy: str,
    ) -> Optional[MergeConflict]:
        """Resolve a conflict between two edges.

        Args:
            static_edge: Edge from static graph.
            dynamic_edge: Edge from dynamic graph.
            strategy: Resolution strategy.

        Returns:
            MergeConflict if conflict was detected, None otherwise.
        """
        conflict = None

        # Check for weight mismatch
        if abs(static_edge.weight - dynamic_edge.weight) > 0.1:
            conflict = MergeConflict(
                conflict_type="edge_weight_mismatch",
                source_graph="mixed",
                entity_id=static_edge.id,
                details={
                    "static_weight": static_edge.weight,
                    "dynamic_weight": dynamic_edge.weight,
                },
            )

            # Resolve based on strategy
            if strategy == "union":
                static_edge.weight = max(static_edge.weight, dynamic_edge.weight)
                conflict.resolution = "union"
            elif strategy == "static_priority":
                conflict.resolution = "static_priority"
            elif strategy == "dynamic_priority":
                static_edge.weight = dynamic_edge.weight
                conflict.resolution = "dynamic_priority"

        return conflict

    def merge_multiple_graphs(
        self,
        graphs: List[Tuple[str, ProgramGraph]],
    ) -> ProgramGraph:
        """Merge multiple graphs sequentially.

        Args:
            graphs: List of (name, graph) tuples.

        Returns:
            Merged graph.
        """
        if not graphs:
            raise ValueError("No graphs to merge")

        merged = graphs[0][1]

        for name, graph in graphs[1:]:
            merged, _ = self.merge_graphs(merged, graph)

        return merged

    def get_merge_statistics(self) -> Dict[str, Any]:
        """Get statistics about merges performed.

        Returns:
            Dictionary with merge statistics.
        """
        if not self.merge_history:
            return {"total_merges": 0}

        total_conflicts = sum(len(p.conflicts) for p in self.merge_history)
        total_edges_added = sum(p.edges_added for p in self.merge_history)
        total_edges_updated = sum(p.edges_updated for p in self.merge_history)
        total_nodes_added = sum(p.nodes_added for p in self.merge_history)

        return {
            "total_merges": len(self.merge_history),
            "total_conflicts": total_conflicts,
            "total_edges_added": total_edges_added,
            "total_edges_updated": total_edges_updated,
            "total_nodes_added": total_nodes_added,
        }
