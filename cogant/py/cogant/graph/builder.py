"""Program graph builder for constructing graphs from normalized facts."""

from datetime import UTC, datetime
from typing import Any

from cogant.normalize.identities import IdentityResolver
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph


class ProgramGraphBuilder:
    """Constructs typed Node and Edge objects to build a program graph.

    Supports incremental building from normalized static and dynamic evidence,
    with full query capabilities for exploration and analysis.
    """

    def __init__(self, repo_uri: str):
        """Initialize the graph builder.

        Args:
            repo_uri: URI or identifier of the repository.
        """
        self.repo_uri = repo_uri
        self.identity_resolver = IdentityResolver()

        # Initialize the graph
        self.graph = ProgramGraph(
            metadata=GraphMetadata(repo_uri=repo_uri),
        )

        self._languages: set[str] = set()

    def add_node(
        self,
        kind: NodeKind,
        name: str,
        qualified_name: str,
        path: str | None = None,
        language: str | None = None,
        source_range: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Node:
        """Add a node to the graph.

        Args:
            kind: Kind of node.
            name: Human-readable name.
            qualified_name: Fully qualified name.
            path: Optional file/module path.
            language: Source language.
            source_range: Optional source code range.
            metadata: Optional language-specific metadata.

        Returns:
            The created Node.
        """
        # Generate stable ID
        node_id = self.identity_resolver.get_id(
            entity_type=kind.value,
            repo_uri=self.repo_uri,
            path=path,
            qualified_name=qualified_name,
        )

        # Check if node already exists
        existing = self.graph.get_node(node_id)
        if existing:
            return existing

        # Create node
        node = Node(
            id=node_id,
            kind=kind,
            name=name,
            qualified_name=qualified_name,
            path=path,
            language=language,
            source_range=source_range,
            metadata=metadata or {},
        )

        # Add to graph
        self.graph.add_node(node)

        # Track language
        if language:
            self._languages.add(language)
            self.graph.metadata.languages.add(language)

        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        kind: EdgeKind,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
        evidence_sources: list[str] | None = None,
    ) -> Edge | None:
        """Add an edge to the graph.

        Args:
            source_id: ID of source node.
            target_id: ID of target node.
            kind: Kind of edge.
            weight: Edge weight (default 1.0).
            metadata: Optional edge metadata.
            evidence_sources: Optional list of evidence sources.

        Returns:
            The created Edge, or None if nodes don't exist.
        """
        # Validate nodes exist
        if not self.graph.get_node(source_id):
            return None
        if not self.graph.get_node(target_id):
            return None

        # Generate stable edge ID
        edge_id = self.identity_resolver.generate_edge_id(source_id, target_id, kind.value)

        # Check if edge already exists
        existing = self.graph.edges.get(edge_id)
        if existing:
            # Update weight and evidence if re-adding
            existing.weight = max(existing.weight, weight)
            if evidence_sources:
                for source in evidence_sources:
                    if source not in existing.evidence_sources:
                        existing.evidence_sources.append(source)
            return existing

        # Create edge
        edge = Edge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            kind=kind,
            weight=weight,
            metadata=metadata or {},
            evidence_sources=evidence_sources or [],
        )

        # Add to graph
        self.graph.add_edge(edge)

        return edge

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID.

        Args:
            node_id: ID of node.

        Returns:
            Node if found, None otherwise.
        """
        return self.graph.get_node(node_id)

    def get_neighbors(self, node_id: str) -> list[Node]:
        """Get all neighbors of a node.

        Args:
            node_id: ID of node.

        Returns:
            List of neighbor nodes.
        """
        return self.graph.get_neighbors(node_id)

    def find_path(self, source_id: str, target_id: str, max_depth: int = 10) -> list[str] | None:
        """Find a path between two nodes using BFS.

        Args:
            source_id: ID of source node.
            target_id: ID of target node.
            max_depth: Maximum search depth.

        Returns:
            List of node IDs forming a path, or None if no path found.
        """
        if source_id == target_id:
            return [source_id]

        visited = {source_id}
        queue = [(source_id, [source_id])]
        depth = 0

        while queue and depth < max_depth:
            depth += 1
            new_queue = []

            for current_id, path in queue:
                neighbors = self.graph.get_neighbors(current_id)

                for neighbor in neighbors:
                    if neighbor.id == target_id:
                        return path + [neighbor.id]

                    if neighbor.id not in visited:
                        visited.add(neighbor.id)
                        new_queue.append((neighbor.id, path + [neighbor.id]))

            queue = new_queue

        return None

    def get_subgraph(
        self,
        node_ids: list[str],
        include_neighbors: bool = False,
    ) -> ProgramGraph:
        """Extract a subgraph containing specified nodes.

        Args:
            node_ids: IDs of nodes to include.
            include_neighbors: Whether to include neighbors of specified nodes.

        Returns:
            New ProgramGraph containing the subgraph.
        """
        subgraph_nodes = set(node_ids)

        if include_neighbors:
            for nid in node_ids:
                neighbors = self.graph.get_neighbors(nid)
                subgraph_nodes.update(n.id for n in neighbors)

        # Create new graph
        subgraph = ProgramGraph(metadata=self.graph.metadata)

        # Add nodes
        for nid in subgraph_nodes:
            node = self.graph.get_node(nid)
            if node:
                subgraph.add_node(node)

        # Add edges between included nodes
        for edge in self.graph.edges.values():
            if edge.source_id in subgraph_nodes and edge.target_id in subgraph_nodes:
                subgraph.add_edge(edge)

        return subgraph

    def get_connected_components(self) -> list[list[str]]:
        """Find all connected components in the graph.

        Returns:
            List of lists, each containing node IDs in a connected component.
        """
        # Build an undirected adjacency list in O(|E|) so that the BFS
        # below runs in O(|V| + |E|) instead of O(|V| × |E|).
        # The original implementation called graph.get_neighbors() inside
        # the BFS loop; each call linearly scanned all edges (O(|E|) per
        # call), making the overall complexity O(|V| × |E|) which is ~133M
        # comparisons for dulwich (8601 nodes, 15441 edges).
        from collections import defaultdict, deque

        adj: dict[str, list[str]] = defaultdict(list)
        for edge in self.graph.edges.values():
            adj[edge.source_id].append(edge.target_id)
            adj[edge.target_id].append(edge.source_id)

        visited: set[str] = set()
        components: list[list[str]] = []

        for node_id in self.graph.nodes:
            if node_id in visited:
                continue

            # BFS using a deque (O(1) popleft) and the pre-built adj index.
            component: list[str] = []
            queue: deque[str] = deque([node_id])
            visited.add(node_id)

            while queue:
                current_id = queue.popleft()
                component.append(current_id)

                for neighbor_id in adj.get(current_id, []):
                    if neighbor_id not in visited and neighbor_id in self.graph.nodes:
                        visited.add(neighbor_id)
                        queue.append(neighbor_id)

            components.append(component)

        return components

    def find_cycles(self) -> list[list[str]]:
        """Find simple cycles in the graph.

        Returns:
            List of cycles, each represented as a list of node IDs.
        """
        cycles = []
        visited_global = set()

        def dfs_cycle(node_id: str, path: list[str], visited: set[str]) -> None:
            """DFS helper to find cycles."""
            if node_id in path:
                # Found a cycle
                cycle_start = path.index(node_id)
                cycle = path[cycle_start:] + [node_id]
                cycle_tuple = tuple(sorted(cycle))
                if cycle_tuple not in visited_global:
                    cycles.append(cycle)
                    visited_global.add(cycle_tuple)
                return

            if node_id in visited:
                return

            visited.add(node_id)
            neighbors = self.graph.get_neighbors(node_id)

            for neighbor in neighbors:
                dfs_cycle(neighbor.id, path + [node_id], visited.copy())

        # Start DFS from each node
        for node in self.graph.nodes.values():
            dfs_cycle(node.id, [], set())

        return cycles

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the graph.

        Returns:
            Dictionary with graph statistics.
        """
        edges_by_kind = {}
        for edge_kind in EdgeKind:
            edges = self.graph.get_edges_by_kind(edge_kind)
            if edges:
                edges_by_kind[edge_kind.value] = len(edges)

        nodes_by_kind = {}
        for node_kind in NodeKind:
            nodes = self.graph.get_nodes_by_kind(node_kind)
            if nodes:
                nodes_by_kind[node_kind.value] = len(nodes)

        return {
            "total_nodes": self.graph.node_count(),
            "total_edges": self.graph.edge_count(),
            "languages": list(self._languages),
            "connected_components": len(self.get_connected_components()),
            "nodes_by_kind": nodes_by_kind,
            "edges_by_kind": edges_by_kind,
        }

    def finalize(self) -> ProgramGraph:
        """Finalize the graph (update timestamps, etc.).

        Returns:
            The complete ProgramGraph.
        """
        self.graph.metadata.updated_at = datetime.now(UTC)
        return self.graph
