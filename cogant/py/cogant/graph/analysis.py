"""Network analysis and graph algorithms for program graphs.

Implements graph metrics, centrality (degree / betweenness / closeness /
eigenvector / PageRank), cycle detection, path analysis, hotspot
identification, and community detection. Uses pure Python with optional
``networkx`` acceleration when the dependency is installed.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from cogant.schemas.graph import ProgramGraph

__all__ = [
    "GraphMetrics",
    "CentralityScores",
    "CycleDetection",
    "PathAnalysis",
    "HotspotAnalysis",
    "GraphAnalyzer",
]


def _try_import_networkx() -> Any:
    """Attempt to import networkx, returning None if unavailable."""
    try:
        import networkx as nx

        return nx
    except ImportError:
        return None


@dataclass
class GraphMetrics:
    """Metrics computed from a program graph."""

    node_count: int
    """Number of nodes in the graph."""

    edge_count: int
    """Number of edges in the graph."""

    density: float
    """Graph density: actual_edges / possible_edges. Range [0, 1]."""

    avg_degree: float
    """Average degree (in + out) per node."""

    max_degree: int
    """Maximum degree of any node."""

    connected_components: int
    """Number of connected components."""

    is_dag: bool
    """True if the graph is acyclic (directed acyclic graph)."""

    diameter: int | None
    """Diameter of graph if connected, None if disconnected."""

    clustering_coefficient: float
    """Average clustering coefficient. Range [0, 1]."""


@dataclass
class CentralityScores:
    """Per-node centrality scores for a program graph."""

    betweenness_centrality: dict[str, float] = field(default_factory=dict)
    """How often a node lies on shortest paths between others. Range [0, 1]."""

    degree_centrality: dict[str, float] = field(default_factory=dict)
    """Degree normalized by max possible. Range [0, 1]."""

    pagerank: dict[str, float] = field(default_factory=dict)
    """PageRank score (importance based on incoming edges). Range [0, 1]."""

    closeness_centrality: dict[str, float] = field(default_factory=dict)
    """Inverse of average distance to all other nodes. Range [0, 1]."""


@dataclass
class CycleDetection:
    """Cycle and strongly connected component detection results."""

    has_cycles: bool
    """True if any cycle exists in the graph."""

    cycles: list[list[str]] = field(default_factory=list)
    """List of cycles (each cycle is a list of node IDs)."""

    strongly_connected_components: list[frozenset[str]] = field(default_factory=list)
    """Strongly connected components (Tarjan's algorithm)."""


@dataclass
class PathAnalysis:
    """Path analysis results."""

    shortest_path: list[str] | None
    """Shortest path from source to target, or None if no path."""

    all_paths: list[list[str]] = field(default_factory=list)
    """All paths from source to target (up to max_depth)."""

    critical_path: list[str] = field(default_factory=list)
    """Longest path in a DAG (if graph is acyclic)."""


@dataclass
class HotspotAnalysis:
    """Hotspot analysis results."""

    hubs: list[tuple[str, int]] = field(default_factory=list)
    """Highest-degree nodes: (node_id, degree)."""

    bottlenecks: list[tuple[str, float]] = field(default_factory=list)
    """Highest betweenness nodes: (node_id, centrality)."""

    sinks: list[str] = field(default_factory=list)
    """Nodes with no outgoing edges."""

    sources: list[str] = field(default_factory=list)
    """Nodes with no incoming edges."""


class GraphAnalyzer:
    """Network analysis for program graphs.

    Provides metrics, centrality computation, community detection,
    cycle detection, and path analysis. Pure Python by default;
    delegates to ``networkx`` when it is importable.
    """

    exact_centrality_node_limit = 500
    centrality_sample_size = 128

    def __init__(self, graph: ProgramGraph) -> None:
        """Initialize the graph analyzer.

        Args:
            graph: ProgramGraph to analyze.
        """
        self.graph = graph
        self.nx = _try_import_networkx()

    def compute_metrics(self) -> GraphMetrics:
        """Compute overall graph metrics.

        Returns:
            GraphMetrics with computed values.
        """
        node_count = len(self.graph.nodes)
        edge_count = len(self.graph.edges)

        # Compute density
        max_edges = node_count * (node_count - 1)
        density = edge_count / max_edges if max_edges > 0 else 0.0

        # Compute average and max degree
        degrees = self._compute_all_degrees()
        avg_degree = sum(degrees.values()) / len(degrees) if degrees else 0.0
        max_degree = max(degrees.values()) if degrees else 0

        # Compute connected components
        components = self._find_connected_components()
        connected_components = len(components)

        # Check if DAG
        is_dag = not self._has_cycle()

        # Compute diameter
        diameter = self._compute_diameter() if connected_components == 1 else None

        # Compute clustering coefficient
        clustering_coeff = self._compute_clustering_coefficient()

        return GraphMetrics(
            node_count=node_count,
            edge_count=edge_count,
            density=density,
            avg_degree=avg_degree,
            max_degree=max_degree,
            connected_components=connected_components,
            is_dag=is_dag,
            diameter=diameter,
            clustering_coefficient=clustering_coeff,
        )

    def compute_centrality(
        self,
        *,
        approximate_above: int | None = None,
        sample_size: int | None = None,
    ) -> CentralityScores:
        """Compute centrality scores for all nodes.

        Uses networkx if available; falls back to pure Python. Exact
        betweenness and closeness are expensive on large program graphs, so
        graphs above ``approximate_above`` use deterministic bounded samples.

        Args:
            approximate_above: Node-count threshold for approximate
                betweenness/closeness. Defaults to ``500``.
            sample_size: Maximum sample size for approximate centrality.
                Defaults to ``128``.

        Returns:
            CentralityScores with all centrality measures.
        """
        threshold = (
            self.exact_centrality_node_limit if approximate_above is None else approximate_above
        )
        limit = self.centrality_sample_size if sample_size is None else sample_size
        approximate = threshold is not None and len(self.graph.nodes) > threshold
        scores = CentralityScores()

        # Betweenness centrality
        scores.betweenness_centrality = self._compute_betweenness_centrality(
            approximate=approximate,
            sample_size=limit,
        )

        # Degree centrality
        scores.degree_centrality = self._compute_degree_centrality()

        # PageRank
        scores.pagerank = self._compute_pagerank()

        # Closeness centrality
        scores.closeness_centrality = self._compute_closeness_centrality(
            approximate=approximate,
            sample_size=limit,
        )

        return scores

    def find_communities(self) -> list[frozenset[str]]:
        """Find communities/clusters of tightly connected nodes.

        Tries Louvain via networkx; falls back to connected components.

        Returns:
            List of communities as frozensets of node IDs.
        """
        # Try Louvain if networkx available
        if self.nx:
            try:
                nx_graph = self.to_networkx()
                from networkx.algorithms import community

                communities = list(community.louvain_communities(nx_graph))
                return [frozenset(c) for c in communities]
            except Exception:
                pass

        # Fallback to connected components
        components = self._find_connected_components()
        return [frozenset(c) for c in components]

    def find_cycles(self, *, max_cycles: int | None = 256) -> CycleDetection:
        """Find all cycles and strongly connected components.

        Exhaustive simple-cycle enumeration can explode on real program
        graphs. The returned SCCs are complete; ``cycles`` is a bounded
        representative sample by default.

        Args:
            max_cycles: Maximum representative cycles to return. ``None``
                requests exhaustive enumeration for small/manual analyses.

        Returns:
            CycleDetection with cycles and SCCs.
        """
        has_cycles = self._has_cycle()
        sccs = self._find_strongly_connected_components()
        candidate_nodes = self._cycle_candidate_nodes(sccs) if has_cycles else set()
        cycles = (
            self._find_all_cycles(max_cycles=max_cycles, candidate_nodes=candidate_nodes)
            if candidate_nodes
            else []
        )

        return CycleDetection(
            has_cycles=has_cycles,
            cycles=cycles,
            strongly_connected_components=sccs,
        )

    def find_hotspots(self, top_n: int = 10) -> HotspotAnalysis:
        """Find high-impact nodes in the graph.

        Args:
            top_n: Number of top nodes to return.

        Returns:
            HotspotAnalysis with hubs, bottlenecks, sinks, sources.
        """
        # Hubs: highest degree
        degrees = self._compute_all_degrees()
        hubs = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # Bottlenecks: highest betweenness
        approximate = len(self.graph.nodes) > self.exact_centrality_node_limit
        betweenness = self._compute_betweenness_centrality(
            approximate=approximate,
            sample_size=self.centrality_sample_size,
        )
        bottlenecks = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # Sinks: no outgoing edges
        sinks = [
            node_id for node_id in self.graph.nodes if len(self.graph.get_edges_from(node_id)) == 0
        ]

        # Sources: no incoming edges
        sources = [
            node_id for node_id in self.graph.nodes if len(self.graph.get_edges_to(node_id)) == 0
        ]

        return HotspotAnalysis(
            hubs=hubs,
            bottlenecks=bottlenecks,
            sinks=sinks,
            sources=sources,
        )

    def get_subgraph(self, nodes: set[str]) -> ProgramGraph:
        """Extract a subgraph containing specified nodes.

        Args:
            nodes: Set of node IDs to include.

        Returns:
            New ProgramGraph with only specified nodes and their edges.
        """
        subgraph = ProgramGraph(metadata=self.graph.metadata)

        # Add specified nodes
        for node_id in nodes:
            node = self.graph.get_node(node_id)
            if node:
                subgraph.add_node(node)

        # Add edges between included nodes
        for edge in self.graph.edges.values():
            if edge.source_id in nodes and edge.target_id in nodes:
                subgraph.add_edge(edge)

        return subgraph

    def to_networkx(self) -> Any:
        """Convert to networkx DiGraph if networkx available.

        Returns:
            networkx.DiGraph or raises ImportError if unavailable.
        """
        if not self.nx:
            raise ImportError("networkx is required for this operation")

        g = self.nx.DiGraph()

        # Add nodes
        for node_id in self.graph.nodes:
            g.add_node(node_id)

        # Add edges
        for edge in self.graph.edges.values():
            g.add_edge(edge.source_id, edge.target_id, weight=edge.weight)

        return g

    def to_adjacency_matrix(self) -> list[list[int]]:
        """Convert graph to adjacency matrix (dense).

        Returns:
            List[List[int]] adjacency matrix (1 = edge, 0 = no edge).
        """
        node_ids = sorted(self.graph.nodes.keys())
        n = len(node_ids)
        node_to_idx = {nid: i for i, nid in enumerate(node_ids)}

        matrix = [[0] * n for _ in range(n)]

        for edge in self.graph.edges.values():
            src_idx = node_to_idx.get(edge.source_id)
            tgt_idx = node_to_idx.get(edge.target_id)
            if src_idx is not None and tgt_idx is not None:
                matrix[src_idx][tgt_idx] = 1

        return matrix

    def summary(self) -> dict[str, Any]:
        """Compute the full analysis summary.

        Returns:
            Dictionary with ``metrics``, ``centrality``, ``hotspots``,
            and ``cycles`` keys covering every category implemented by
            this analyzer.
        """
        metrics = self.compute_metrics()
        centrality = self.compute_centrality()
        hotspots = self.find_hotspots()
        cycles = self.find_cycles()

        return {
            "metrics": {
                "nodes": metrics.node_count,
                "edges": metrics.edge_count,
                "density": round(metrics.density, 4),
                "avg_degree": round(metrics.avg_degree, 2),
                "max_degree": metrics.max_degree,
                "components": metrics.connected_components,
                "is_dag": metrics.is_dag,
                "diameter": metrics.diameter,
                "clustering": round(metrics.clustering_coefficient, 4),
            },
            "hotspots": {
                "hubs": hotspots.hubs[:5],
                "bottlenecks": [(nid, round(c, 4)) for nid, c in hotspots.bottlenecks[:5]],
                "sinks": len(hotspots.sinks),
                "sources": len(hotspots.sources),
            },
            "cycles": {
                "has_cycles": cycles.has_cycles,
                "cycle_count": len(cycles.cycles),
                "scc_count": len(cycles.strongly_connected_components),
            },
            "centrality_sample": {
                node_id: {
                    "betweenness": round(centrality.betweenness_centrality.get(node_id, 0.0), 4),
                    "degree": round(centrality.degree_centrality.get(node_id, 0.0), 4),
                    "pagerank": round(centrality.pagerank.get(node_id, 0.0), 4),
                    "closeness": round(centrality.closeness_centrality.get(node_id, 0.0), 4),
                }
                for node_id in list(self.graph.nodes.keys())[:3]
            },
        }

    # --- Private helper methods ---

    def _compute_all_degrees(self) -> dict[str, int]:
        """Compute in-degree + out-degree for each node."""
        degrees: dict[str, int] = {}
        for node_id in self.graph.nodes:
            in_degree = len(self.graph.get_edges_to(node_id))
            out_degree = len(self.graph.get_edges_from(node_id))
            degrees[node_id] = in_degree + out_degree
        return degrees

    def _compute_all_out_degrees(self) -> dict[str, int]:
        """Compute out-degree for each node."""
        return {nid: len(self.graph.get_edges_from(nid)) for nid in self.graph.nodes}

    def _centrality_sample_nodes(self, sample_size: int) -> list[str]:
        """Return a deterministic high-degree node sample for bounded analysis."""
        degrees = self._compute_all_degrees()
        return [
            node_id
            for node_id, _ in sorted(degrees.items(), key=lambda item: (-item[1], item[0]))[
                : max(0, sample_size)
            ]
        ]

    def _compute_density(self) -> float:
        """Compute graph density."""
        n = len(self.graph.nodes)
        m = len(self.graph.edges)
        max_edges = n * (n - 1)
        return m / max_edges if max_edges > 0 else 0.0

    def _compute_diameter(self) -> int | None:
        """Compute diameter of the graph (max shortest path length).

        Returns None if graph is disconnected or has < 2 nodes.
        """
        nodes = list(self.graph.nodes.keys())
        if len(nodes) < 2:
            return None

        max_distance = 0
        for source_id in nodes:
            for target_id in nodes:
                if source_id == target_id:
                    continue
                path = self._find_shortest_path_bfs(source_id, target_id)
                if path is None:
                    return None  # Graph is disconnected
                max_distance = max(max_distance, len(path) - 1)

        return max_distance

    def _compute_clustering_coefficient(self) -> float:
        """Compute average local clustering coefficient."""
        coeff_sum = 0.0
        count = 0

        for node_id in self.graph.nodes:
            neighbors = self.graph.get_neighbors(node_id)
            k = len(neighbors)

            if k < 2:
                continue

            # Count edges among neighbors
            edges_among_neighbors = 0
            for i, n1 in enumerate(neighbors):
                for n2 in neighbors[i + 1 :]:
                    # Check if there's an edge between n1 and n2
                    for edge in self.graph.edges.values():
                        if (edge.source_id == n1.id and edge.target_id == n2.id) or (
                            edge.source_id == n2.id and edge.target_id == n1.id
                        ):
                            edges_among_neighbors += 1
                            break

            max_edges = k * (k - 1) / 2
            if max_edges > 0:
                coeff = edges_among_neighbors / max_edges
                coeff_sum += coeff
                count += 1

        return coeff_sum / count if count > 0 else 0.0

    def _find_connected_components(self) -> list[set[str]]:
        """Find connected components using BFS."""
        visited: set[str] = set()
        components: list[set[str]] = []

        for node_id in self.graph.nodes:
            if node_id in visited:
                continue

            component: set[str] = set()
            queue = deque([node_id])

            while queue:
                current_id = queue.popleft()
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

    def _compute_betweenness_centrality(
        self,
        *,
        approximate: bool = False,
        sample_size: int = 128,
    ) -> dict[str, float]:
        """Compute betweenness centrality for all nodes.

        Uses NetworkX (normalized, in ``[0, 1]``) when available. The pure
        Python fallback scales by the maximum score so results stay in
        ``[0, 1]`` (the pairwise BFS shortcut is not standard Brandes).
        """
        if self.nx:
            try:
                kwargs: dict[str, Any] = {"normalized": True}
                if approximate and len(self.graph.nodes) > sample_size:
                    kwargs.update({"k": sample_size, "seed": 0})
                bc = self.nx.betweenness_centrality(self.to_networkx(), **kwargs)
                return {nid: float(bc.get(nid, 0.0)) for nid in self.graph.nodes}
            except Exception:
                pass

        centrality: dict[str, float] = dict.fromkeys(self.graph.nodes, 0.0)
        nodes = list(self.graph.nodes.keys())
        sources = self._centrality_sample_nodes(sample_size) if approximate else nodes

        for source in sources:
            for target in nodes:
                if source == target:
                    continue

                path = self._find_shortest_path_bfs(source, target)
                if path and len(path) > 2:
                    for node_id in path[1:-1]:  # Exclude source and target
                        centrality[node_id] += 1.0

        peak = max(centrality.values()) if centrality else 0.0
        if peak > 0:
            for node_id in centrality:
                centrality[node_id] /= peak

        return dict(centrality)

    def _compute_degree_centrality(self) -> dict[str, float]:
        """Compute degree centrality."""
        centrality: dict[str, float] = {}
        max_degree = len(self.graph.nodes) - 1 if len(self.graph.nodes) > 1 else 1

        for node_id in self.graph.nodes:
            in_degree = len(self.graph.get_edges_to(node_id))
            out_degree = len(self.graph.get_edges_from(node_id))
            total_degree = in_degree + out_degree
            centrality[node_id] = total_degree / max_degree if max_degree > 0 else 0.0

        return centrality

    def _compute_closeness_centrality(
        self,
        *,
        approximate: bool = False,
        sample_size: int = 128,
    ) -> dict[str, float]:
        """Compute closeness centrality."""
        centrality: dict[str, float] = dict.fromkeys(self.graph.nodes, 0.0)
        nodes = list(self.graph.nodes.keys())
        sources = self._centrality_sample_nodes(sample_size) if approximate else nodes

        for source in sources:
            distances = self._shortest_distances_bfs(source)
            total_distance = sum(
                distance for node_id, distance in distances.items() if node_id != source
            )
            reachable = len(distances) - 1

            if reachable > 0:
                centrality[source] = reachable / total_distance if total_distance > 0 else 0.0

        return centrality

    def _compute_pagerank(self, iterations: int = 20, damping: float = 0.85) -> dict[str, float]:
        """Compute PageRank scores."""
        if self.nx:
            try:
                nx_graph = self.to_networkx()
                return dict(self.nx.pagerank(nx_graph, alpha=damping, max_iter=iterations))
            except Exception:
                pass

        # Pure Python fallback
        nodes = list(self.graph.nodes.keys())
        n = len(nodes)

        if n == 0:
            return {}

        # Initialize
        rank = dict.fromkeys(nodes, 1.0 / n)
        out_degrees = {nid: max(1, len(self.graph.get_edges_from(nid))) for nid in nodes}

        # Iterate
        for _ in range(iterations):
            new_rank = dict.fromkeys(nodes, (1 - damping) / n)

            for nid in nodes:
                incoming = self.graph.get_edges_to(nid)
                for edge in incoming:
                    src_id = edge.source_id
                    new_rank[nid] += damping * rank[src_id] / out_degrees[src_id]

            rank = new_rank

        return rank

    def _find_shortest_path_bfs(self, source_id: str, target_id: str) -> list[str] | None:
        """Find shortest path using BFS."""
        if source_id == target_id:
            return [source_id]

        visited = {source_id}
        queue = deque([(source_id, [source_id])])

        while queue:
            current_id, path = queue.popleft()
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

    def _shortest_distances_bfs(self, source_id: str) -> dict[str, int]:
        """Return shortest path distances from one source."""
        distances = {source_id: 0}
        queue = deque([source_id])

        while queue:
            current_id = queue.popleft()
            for neighbor in self.graph.get_neighbors(current_id):
                if neighbor.id not in distances:
                    distances[neighbor.id] = distances[current_id] + 1
                    queue.append(neighbor.id)

        return distances

    def _has_cycle(self) -> bool:
        """Check if graph has any cycle using DFS."""
        color: dict[str, str] = {}  # white, gray, black

        def dfs(node_id: str) -> bool:
            color[node_id] = "gray"
            outgoing = self.graph.get_edges_from(node_id)

            for edge in outgoing:
                target_id = edge.target_id
                if target_id not in color:
                    if dfs(target_id):
                        return True
                elif color[target_id] == "gray":
                    return True

            color[node_id] = "black"
            return False

        for node_id in self.graph.nodes:
            if node_id not in color:
                if dfs(node_id):
                    return True

        return False

    def _cycle_candidate_nodes(self, sccs: list[frozenset[str]]) -> set[str]:
        """Return nodes that can be in a directed cycle."""
        candidates = {node_id for component in sccs if len(component) > 1 for node_id in component}
        self_loop_nodes = {
            edge.source_id for edge in self.graph.edges.values() if edge.source_id == edge.target_id
        }
        return candidates | self_loop_nodes

    def _find_all_cycles(
        self,
        max_cycle_size: int = 10,
        *,
        max_cycles: int | None = 256,
        candidate_nodes: set[str] | None = None,
    ) -> list[list[str]]:
        """Find all cycles in the graph."""
        cycles: list[list[str]] = []
        seen_cycles: set[tuple[str, ...]] = set()
        starts = candidate_nodes if candidate_nodes is not None else set(self.graph.nodes)

        for start_id in starts:
            if max_cycles is not None and len(cycles) >= max_cycles:
                break
            remaining = None if max_cycles is None else max_cycles - len(cycles)
            paths = self._find_all_paths_dfs(
                start_id,
                start_id,
                max_cycle_size,
                max_paths=remaining,
            )

            for path in paths:
                if max_cycles is not None and len(cycles) >= max_cycles:
                    break
                if len(path) > 2:
                    cycle_tuple = tuple(sorted(path[:-1]))
                    if cycle_tuple not in seen_cycles:
                        seen_cycles.add(cycle_tuple)
                        cycles.append(path[:-1])
                elif len(path) == 2 and path[0] == path[1]:
                    cycle_tuple = (path[0],)
                    if cycle_tuple not in seen_cycles:
                        seen_cycles.add(cycle_tuple)
                        cycles.append([path[0]])

        return cycles

    def _find_all_paths_dfs(
        self,
        current_id: str,
        target_id: str,
        max_depth: int,
        *,
        max_paths: int | None = None,
    ) -> list[list[str]]:
        """Find all paths from current to target using DFS."""
        paths: list[list[str]] = []

        def dfs(cid: str, tgt: str, path: list[str], visited: set[str]) -> None:
            if max_paths is not None and len(paths) >= max_paths:
                return
            if len(path) > max_depth:
                return

            outgoing = self.graph.get_edges_from(cid)
            for edge in outgoing:
                if max_paths is not None and len(paths) >= max_paths:
                    break
                nid = edge.target_id
                # Close a directed cycle back to the search start (tgt).
                if nid == tgt and len(path) >= 1:
                    paths.append(path + [nid])
                    continue
                if nid not in visited:
                    new_visited = visited | {nid}
                    dfs(nid, tgt, path + [nid], new_visited)

        dfs(current_id, target_id, [current_id], {current_id})
        return paths

    def _find_strongly_connected_components(self) -> list[frozenset[str]]:
        """Find SCCs using Kosaraju's algorithm."""
        # First DFS to get finish times
        visited: set[str] = set()
        finish_stack: list[str] = []

        def dfs1(node_id: str) -> None:
            visited.add(node_id)
            for edge in self.graph.get_edges_from(node_id):
                if edge.target_id not in visited:
                    dfs1(edge.target_id)
            finish_stack.append(node_id)

        for node_id in self.graph.nodes:
            if node_id not in visited:
                dfs1(node_id)

        # Build reverse graph
        reverse_edges: dict[str, list[str]] = defaultdict(list)
        for edge in self.graph.edges.values():
            reverse_edges[edge.target_id].append(edge.source_id)

        # Second DFS on reverse graph
        visited.clear()
        sccs: list[frozenset[str]] = []

        def dfs2(node_id: str, component: set[str]) -> None:
            visited.add(node_id)
            component.add(node_id)
            for target_id in reverse_edges[node_id]:
                if target_id not in visited:
                    dfs2(target_id, component)

        for node_id in reversed(finish_stack):
            if node_id not in visited:
                component: set[str] = set()
                dfs2(node_id, component)
                if component:
                    sccs.append(frozenset(component))

        return sccs
