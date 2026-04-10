"""Program graph schema definitions."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind

__all__ = ["GraphMetadata", "ProgramGraph"]


@dataclass
class GraphMetadata:
    """Metadata about a program graph."""

    repo_uri: str
    """URI or path of the repository."""

    languages: set[str] = field(default_factory=set)
    """Languages found in the codebase."""

    version: str = "1.0"
    """Graph schema version."""

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """Creation timestamp."""

    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """Last update timestamp."""

    evidence_sources: list[str] = field(default_factory=list)
    """Sources of evidence (static, dynamic, etc.)."""

    custom_metadata: dict[str, Any] = field(default_factory=dict)
    """Additional custom metadata."""


@dataclass
class ProgramGraph:
    """Represents a complete program graph."""

    metadata: GraphMetadata
    """Graph metadata."""

    nodes: dict[str, Node] = field(default_factory=dict)
    """Map of node ID to Node object."""

    edges: dict[str, Edge] = field(default_factory=dict)
    """Map of edge ID to Edge object."""

    def add_node(self, node: Node) -> None:
        """Add a node to the graph.

        Args:
            node: Node to add.
        """
        self.nodes[node.id] = node

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the graph.

        Args:
            node_id: ID of node to remove.
        """
        if node_id in self.nodes:
            del self.nodes[node_id]
            # Remove associated edges
            edges_to_remove = [
                eid for eid, e in self.edges.items()
                if e.source_id == node_id or e.target_id == node_id
            ]
            for eid in edges_to_remove:
                del self.edges[eid]

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph.

        Args:
            edge: Edge to add.
        """
        if edge.source_id in self.nodes and edge.target_id in self.nodes:
            self.edges[edge.id] = edge

    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge from the graph.

        Args:
            edge_id: ID of edge to remove.
        """
        if edge_id in self.edges:
            del self.edges[edge_id]

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID.

        Args:
            node_id: ID of node to retrieve.

        Returns:
            Node if found, None otherwise.
        """
        return self.nodes.get(node_id)

    def get_edges_from(self, node_id: str) -> list[Edge]:
        """Get all outgoing edges from a node.

        Args:
            node_id: ID of source node.

        Returns:
            List of outgoing edges.
        """
        return [e for e in self.edges.values() if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> list[Edge]:
        """Get all incoming edges to a node.

        Args:
            node_id: ID of target node.

        Returns:
            List of incoming edges.
        """
        return [e for e in self.edges.values() if e.target_id == node_id]

    def get_neighbors(self, node_id: str) -> list[Node]:
        """Get all neighbors of a node (both incoming and outgoing).

        Args:
            node_id: ID of node.

        Returns:
            List of neighbor nodes.
        """
        edges = self.get_edges_from(node_id) + self.get_edges_to(node_id)
        neighbors = set()
        for edge in edges:
            if edge.source_id == node_id:
                neighbors.add(edge.target_id)
            if edge.target_id == node_id:
                neighbors.add(edge.source_id)
        return [self.nodes[nid] for nid in neighbors if nid in self.nodes]

    def get_nodes_by_kind(self, kind: NodeKind) -> list[Node]:
        """Get all nodes of a specific kind.

        Args:
            kind: Kind of nodes to retrieve.

        Returns:
            List of nodes matching the kind.
        """
        return [n for n in self.nodes.values() if n.kind == kind]

    def get_edges_by_kind(self, kind: EdgeKind) -> list[Edge]:
        """Get all edges of a specific kind.

        Args:
            kind: Kind of edges to retrieve.

        Returns:
            List of edges matching the kind.
        """
        return [e for e in self.edges.values() if e.kind == kind]

    def node_count(self) -> int:
        """Get the number of nodes in the graph.

        Returns:
            Number of nodes.
        """
        return len(self.nodes)

    def edge_count(self) -> int:
        """Get the number of edges in the graph.

        Returns:
            Number of edges.
        """
        return len(self.edges)
