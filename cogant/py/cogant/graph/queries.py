"""Graph query operations for analysis and exploration."""

from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from cogant.schemas.core import Node, Edge, NodeKind, EdgeKind
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

    def find_nodes_by_kind(self, kind: NodeKind) -> List[Node]:
        """Find all nodes of a given kind (convenience method).

        Args:
            kind: NodeKind to filter by.

        Returns:
            List of nodes with matching kind.
        """
        return self.filter_nodes(kind=kind)

    def filter_nodes(
        self,
        kind: Optional[NodeKind] = None,
        language: Optional[str] = None,
        name_pattern: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Node]:
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
        kind: Optional[EdgeKind] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        min_weight: float = 0.0,
    ) -> List[Edge]:
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
    ) -> Optional[List[str]]:
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
    ) -> List[List[str]]:
        """Find all paths between two nodes up to max depth.

        Args:
            source_id: ID of source node.
            target_id: ID of target node.
            max_depth: Maximum path length.

        Returns:
            List of paths, each represented as list of node IDs.
        """
        paths = []

        def dfs(current_id: str, target: str, path: List[str], visited: Set[str]) -> None:
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

    def compute_betweenness_centrality(self) -> Dict[str, float]:
        """Compute betweenness centrality for all nodes.

        Measures how often a node appears in shortest paths between other nodes.

        Returns:
            Dictionary mapping node IDs to centrality scores.
        """
        centrality = defaultdict(float)
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

    def compute_closeness_centrality(self) -> Dict[str, float]:
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

    def compute_degree_centrality(self) -> Dict[str, float]:
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

    def find_connected_components(self) -> List[Set[str]]:
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

    def find_cycles(self, max_cycle_size: int = 10) -> List[List[str]]:
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
        node_kinds: List[NodeKind],
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

    def get_dependency_chain(self, node_id: str, max_depth: int = 5) -> Dict[str, List[str]]:
        """Get all dependencies of a node up to max depth.

        Args:
            node_id: ID of node.
            max_depth: Maximum depth to traverse.

        Returns:
            Dictionary mapping depth level to list of node IDs.
        """
        dependencies = defaultdict(list)
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
                        dependencies[depth].append(neighbor.id)

            current_level = next_level

        return dict(dependencies)

    def get_statistics(self) -> Dict[str, Any]:
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
