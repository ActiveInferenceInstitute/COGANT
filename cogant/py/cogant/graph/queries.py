"""Graph query operations for analysis and exploration."""

from collections import defaultdict
from typing import Any

from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import ProgramGraph


class GraphQuery:
    """Advanced query operations on program graphs.

    Supports filtering, path finding, centrality computation, and analysis.
    """

    def __init__(self, graph: ProgramGraph):
        """Initialize graph query engine.

        Args:
            graph: ProgramGraph to query.
        """
        self.graph = graph

    def find_nodes_by_kind(self, kind: NodeKind) -> list[Node]:
        """Find all nodes of a given kind (convenience method).

        Args:
            kind: NodeKind to filter by.

        Returns:
            List of nodes with matching kind.
        """
        return self.filter_nodes(kind=kind)

    def filter_nodes(
        self,
        kind: NodeKind | None = None,
        language: str | None = None,
        name_pattern: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[Node]:
        """Filter nodes by various criteria.

        Args:
            kind: Filter by node kind.
            language: Filter by language.
            name_pattern: Substring pattern to match in name.
            metadata_filter: Dictionary of metadata key-value pairs to match.

        Returns:
            List of matching nodes.
        """
        results = list(self.graph.nodes.values())

        if kind:
            results = [n for n in results if n.kind == kind]

        if language:
            results = [n for n in results if n.language == language]

        if name_pattern:
            results = [n for n in results if name_pattern.lower() in n.name.lower()]

        if metadata_filter:
            for key, value in metadata_filter.items():
                results = [n for n in results if n.metadata.get(key) == value]

        return results

    def filter_edges(
        self,
        kind: EdgeKind | None = None,
        source_id: str | None = None,
        target_id: str | None = None,
        min_weight: float = 0.0,
    ) -> list[Edge]:
        """Filter edges by various criteria.

        Args:
            kind: Filter by edge kind.
            source_id: Filter edges from a source node.
            target_id: Filter edges to a target node.
            min_weight: Filter by minimum weight.

        Returns:
            List of matching edges.
        """
        results = list(self.graph.edges.values())

        if kind:
            results = [e for e in results if e.kind == kind]

        if source_id:
            results = [e for e in results if e.source_id == source_id]

        if target_id:
            results = [e for e in results if e.target_id == target_id]

        if min_weight > 0.0:
            results = [e for e in results if e.weight >= min_weight]

        return results

    def find_shortest_path(
        self,
        source_id: str,
        target_id: str,
    ) -> list[str] | None:
        """Find shortest path between two nodes using BFS.

        Args:
            source_id: ID of source node.
            target_id: ID of target node.

        Returns:
            List of node IDs forming shortest path, or None if no path.
        """
        if source_id == target_id:
            return [source_id]

        visited = {source_id}
        queue = [(source_id, [source_id])]

        while queue:
            current_id, path = queue.pop(0)
            current_node = self.graph.get_node(current_id)

            if not current_node:
                continue

            neighbors = self.graph.get_neighbors(current_id)

            for neighbor in neighbors:
                if neighbor.id == target_id:
                    return path + [neighbor.id]

                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    queue.append((neighbor.id, path + [neighbor.id]))

        return None

    def find_all_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> list[list[str]]:
        """Find all paths between two nodes up to max depth.

        Args:
            source_id: ID of source node.
            target_id: ID of target node.
            max_depth: Maximum path length.

        Returns:
            List of paths, each represented as list of node IDs.
        """
        paths = []

        def dfs(current_id: str, target: str, path: list[str], visited: set[str]) -> None:
            """Depth-first walk that records every simple path up to ``max_depth``."""
            if len(path) > max_depth:
                return

            if current_id == target:
                paths.append(path)
                return

            neighbors = self.graph.get_neighbors(current_id)
            for neighbor in neighbors:
                if neighbor.id not in visited:
                    new_visited = visited | {neighbor.id}
                    dfs(neighbor.id, target, path + [neighbor.id], new_visited)

        dfs(source_id, target_id, [source_id], {source_id})
        return paths

    def compute_in_degree(self, node_id: str) -> int:
        """Compute in-degree (incoming edges) of a node.

        Args:
            node_id: ID of node.

        Returns:
            In-degree count.
        """
        edges = self.graph.get_edges_to(node_id)
        return len(edges)

    def compute_out_degree(self, node_id: str) -> int:
        """Compute out-degree (outgoing edges) of a node.

        Args:
            node_id: ID of node.

        Returns:
            Out-degree count.
        """
        edges = self.graph.get_edges_from(node_id)
        return len(edges)

    def compute_betweenness_centrality(self) -> dict[str, float]:
        """Compute betweenness centrality for all nodes.

        Measures how often a node appears in shortest paths between other nodes.

        Returns:
            Dictionary mapping node IDs to centrality scores.
        """
        centrality: dict[str, float] = defaultdict(float)
        nodes = list(self.graph.nodes.keys())

        for source in nodes:
            for target in nodes:
                if source == target:
                    continue

                path = self.find_shortest_path(source, target)
                if path:
                    for node_id in path[1:-1]:  # Exclude source and target
                        centrality[node_id] += 1.0

        # Normalize
        max_paths = (len(nodes) - 1) * (len(nodes) - 2) / 2
        if max_paths > 0:
            for node_id in centrality:
                centrality[node_id] /= max_paths

        return dict(centrality)

    def compute_closeness_centrality(self) -> dict[str, float]:
        """Compute closeness centrality for all nodes.

        Measures average distance to all other nodes.

        Returns:
            Dictionary mapping node IDs to centrality scores.
        """
        centrality = {}
        nodes = list(self.graph.nodes.keys())

        for source in nodes:
            total_distance = 0
            reachable = 0

            for target in nodes:
                if source == target:
                    continue

                path = self.find_shortest_path(source, target)
                if path:
                    total_distance += len(path) - 1
                    reachable += 1

            if reachable > 0:
                centrality[source] = reachable / total_distance if total_distance > 0 else 0.0

        return centrality

    def compute_degree_centrality(self) -> dict[str, float]:
        """Compute degree centrality for all nodes.

        Measures the number of connections relative to maximum possible.

        Returns:
            Dictionary mapping node IDs to centrality scores.
        """
        centrality = {}
        max_degree = len(self.graph.nodes) - 1 if len(self.graph.nodes) > 1 else 1

        for node_id in self.graph.nodes:
            in_degree = self.compute_in_degree(node_id)
            out_degree = self.compute_out_degree(node_id)
            total_degree = in_degree + out_degree
            centrality[node_id] = total_degree / max_degree if max_degree > 0 else 0.0

        return centrality

    def find_connected_components(self) -> list[set[str]]:
        """Find all connected components.

        Returns:
            List of sets, each containing node IDs in a component.
        """
        visited = set()
        components = []

        for node_id in self.graph.nodes:
            if node_id in visited:
                continue

            component = set()
            queue = [node_id]

            while queue:
                current_id = queue.pop(0)
                if current_id in visited:
                    continue

                visited.add(current_id)
                component.add(current_id)

                neighbors = self.graph.get_neighbors(current_id)
                for neighbor in neighbors:
                    if neighbor.id not in visited:
                        queue.append(neighbor.id)

            if component:
                components.append(component)

        return components

    def find_cycles(self, max_cycle_size: int = 10) -> list[list[str]]:
        """Find cycles in the graph.

        Args:
            max_cycle_size: Maximum size of cycles to detect.

        Returns:
            List of cycles, each represented as list of node IDs.
        """
        cycles = []
        seen_cycles = set()

        for start_node_id in self.graph.nodes:
            paths = self.find_all_paths(start_node_id, start_node_id, max_cycle_size)

            for path in paths:
                if len(path) > 2:  # Exclude trivial self-loops
                    cycle_tuple = tuple(sorted(path[:-1]))
                    if cycle_tuple not in seen_cycles:
                        seen_cycles.add(cycle_tuple)
                        cycles.append(path[:-1])

        return cycles

    def extract_subgraph_by_kind(
        self,
        node_kinds: list[NodeKind],
    ) -> ProgramGraph:
        """Extract subgraph containing only nodes of specified kinds.

        Args:
            node_kinds: List of node kinds to include.

        Returns:
            New ProgramGraph containing only matching nodes and their edges.
        """
        subgraph = ProgramGraph(metadata=self.graph.metadata)

        # Add matching nodes
        for node in self.graph.nodes.values():
            if node.kind in node_kinds:
                subgraph.add_node(node)

        # Add edges between included nodes
        for edge in self.graph.edges.values():
            if edge.source_id in subgraph.nodes and edge.target_id in subgraph.nodes:
                subgraph.add_edge(edge)

        return subgraph

    def get_dependency_chain(self, node_id: str, max_depth: int = 5) -> dict[str, list[str]]:
        """Get all dependencies of a node up to max depth.

        Args:
            node_id: ID of node.
            max_depth: Maximum depth to traverse.

        Returns:
            Dictionary mapping depth level to list of node IDs.
        """
        dependencies: dict[str, list[str]] = defaultdict(list)
        visited = {node_id}
        current_level = [node_id]
        depth = 0

        while current_level and depth < max_depth:
            depth += 1
            next_level = []

            for current_id in current_level:
                neighbors = self.graph.get_neighbors(current_id)
                for neighbor in neighbors:
                    if neighbor.id not in visited:
                        visited.add(neighbor.id)
                        next_level.append(neighbor.id)
                        dependencies[str(depth)].append(neighbor.id)

            current_level = next_level

        return dict(dependencies)

    def get_statistics(self) -> dict[str, Any]:
        """Get query statistics.

        Returns:
            Dictionary with statistics.
        """
        return {
            "total_nodes": len(self.graph.nodes),
            "total_edges": len(self.graph.edges),
            "connected_components": len(self.find_connected_components()),
            "cycles": len(self.find_cycles()),
        }

    def find_by_role(self, role: str) -> list[Node]:
        """Find nodes by AII semantic role.

        Args:
            role: Semantic role to filter by (from metadata or convention).

        Returns:
            List of nodes matching the role.
        """
        return [
            n
            for n in self.graph.nodes.values()
            if n.metadata.get("role") == role or n.metadata.get("semantic_role") == role
        ]

    def find_paths_between(self, source_role: str, target_role: str) -> list[list[str]]:
        """Find paths between nodes of two semantic roles.

        Args:
            source_role: Source semantic role.
            target_role: Target semantic role.

        Returns:
            List of paths (each path is a list of node IDs).
        """
        paths = []

        source_nodes = self.find_by_role(source_role)
        target_nodes = self.find_by_role(target_role)

        for source in source_nodes:
            for target in target_nodes:
                path = self.find_shortest_path(source.id, target.id)
                if path:
                    paths.append(path)

        return paths

    def get_neighborhood(self, node_id: str, depth: int = 2) -> set[str]:
        """Get all nodes within N hops of a given node.

        Args:
            node_id: ID of center node.
            depth: Maximum hop distance.

        Returns:
            Set of node IDs within the neighborhood.
        """
        neighborhood: set[str] = {node_id}
        current_level = {node_id}
        visited = {node_id}

        for _ in range(depth):
            next_level: set[str] = set()

            for nid in current_level:
                neighbors = self.graph.get_neighbors(nid)
                for neighbor in neighbors:
                    if neighbor.id not in visited:
                        visited.add(neighbor.id)
                        next_level.add(neighbor.id)
                        neighborhood.add(neighbor.id)

            current_level = next_level
            if not current_level:
                break

        return neighborhood

    def filter_by_edge_type(self, edge_type: str) -> ProgramGraph:
        """Extract subgraph containing only edges of a specific type.

        Args:
            edge_type: Edge type to filter by (e.g., "calls", "reads").

        Returns:
            New ProgramGraph with only edges of specified type.
        """
        # Convert string to EdgeKind if needed
        try:
            edge_kind = EdgeKind(edge_type)
        except ValueError:
            # If not a valid EdgeKind, return empty graph
            return ProgramGraph(metadata=self.graph.metadata)

        subgraph = ProgramGraph(metadata=self.graph.metadata)

        # Find all edges of this kind
        edges = self.filter_edges(kind=edge_kind)

        # Add nodes involved in these edges
        node_ids: set[str] = set()
        for edge in edges:
            node_ids.add(edge.source_id)
            node_ids.add(edge.target_id)

        for node_id in node_ids:
            node = self.graph.get_node(node_id)
            if node:
                subgraph.add_node(node)

        # Add the edges
        for edge in edges:
            subgraph.add_edge(edge)

        return subgraph

    def get_interface_nodes(self) -> list[Node]:
        """Find nodes that bridge components (high betweenness).

        Nodes with high betweenness are critical for connecting different parts
        of the graph and represent interface or gateway nodes.

        Returns:
            List of high-centrality nodes sorted by betweenness.
        """
        centrality = self.compute_betweenness_centrality()

        # Find nodes in top quartile
        if not centrality:
            return []

        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        threshold_idx = max(1, len(sorted_nodes) // 4)

        interface_node_ids = [nid for nid, _ in sorted_nodes[:threshold_idx]]

        return [
            self.graph.get_node(nid)
            for nid in interface_node_ids
            if self.graph.get_node(nid) is not None
        ]
