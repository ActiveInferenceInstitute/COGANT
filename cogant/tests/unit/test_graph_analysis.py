"""Unit tests for graph analysis module."""

import pytest
from pathlib import Path
from datetime import datetime, UTC

from cogant.graph.analysis import (
    GraphAnalyzer,
    GraphMetrics,
    CentralityScores,
    CycleDetection,
    HotspotAnalysis,
)
from cogant.schemas.graph import ProgramGraph, GraphMetadata
from cogant.schemas.core import Node, Edge, NodeKind, EdgeKind


@pytest.fixture
def empty_graph() -> ProgramGraph:
    """Create an empty program graph."""
    metadata = GraphMetadata(repo_uri="test://repo")
    return ProgramGraph(metadata=metadata)


@pytest.fixture
def simple_dag() -> ProgramGraph:
    """Create a simple directed acyclic graph: A -> B -> C."""
    metadata = GraphMetadata(repo_uri="test://repo")
    graph = ProgramGraph(metadata=metadata)

    # Add nodes
    node_a = Node(id="A", kind=NodeKind.FUNCTION, name="A", qualified_name="module.A")
    node_b = Node(id="B", kind=NodeKind.FUNCTION, name="B", qualified_name="module.B")
    node_c = Node(id="C", kind=NodeKind.FUNCTION, name="C", qualified_name="module.C")

    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_node(node_c)

    # Add edges
    edge_ab = Edge(id="e1", source_id="A", target_id="B", kind=EdgeKind.CALLS)
    edge_bc = Edge(id="e2", source_id="B", target_id="C", kind=EdgeKind.CALLS)

    graph.add_edge(edge_ab)
    graph.add_edge(edge_bc)

    return graph


@pytest.fixture
def cyclic_graph() -> ProgramGraph:
    """Create a graph with a cycle: A -> B -> C -> A."""
    metadata = GraphMetadata(repo_uri="test://repo")
    graph = ProgramGraph(metadata=metadata)

    node_a = Node(id="A", kind=NodeKind.FUNCTION, name="A", qualified_name="module.A")
    node_b = Node(id="B", kind=NodeKind.FUNCTION, name="B", qualified_name="module.B")
    node_c = Node(id="C", kind=NodeKind.FUNCTION, name="C", qualified_name="module.C")

    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_node(node_c)

    edge_ab = Edge(id="e1", source_id="A", target_id="B", kind=EdgeKind.CALLS)
    edge_bc = Edge(id="e2", source_id="B", target_id="C", kind=EdgeKind.CALLS)
    edge_ca = Edge(id="e3", source_id="C", target_id="A", kind=EdgeKind.CALLS)

    graph.add_edge(edge_ab)
    graph.add_edge(edge_bc)
    graph.add_edge(edge_ca)

    return graph


@pytest.fixture
def hub_graph() -> ProgramGraph:
    """Create a graph with a hub node (central node with many connections)."""
    metadata = GraphMetadata(repo_uri="test://repo")
    graph = ProgramGraph(metadata=metadata)

    # Create nodes: center with 4 leaves
    center = Node(id="center", kind=NodeKind.FUNCTION, name="center", qualified_name="module.center")
    graph.add_node(center)

    for i in range(4):
        node = Node(
            id=f"leaf{i}",
            kind=NodeKind.FUNCTION,
            name=f"leaf{i}",
            qualified_name=f"module.leaf{i}",
        )
        graph.add_node(node)

    # Connect all leaves to center
    for i in range(4):
        edge = Edge(
            id=f"e{i}",
            source_id=f"leaf{i}",
            target_id="center",
            kind=EdgeKind.CALLS,
        )
        graph.add_edge(edge)

    return graph


@pytest.mark.unit
class TestGraphMetrics:
    """Test GraphMetrics dataclass."""

    def test_creation(self) -> None:
        """Test creating GraphMetrics."""
        metrics = GraphMetrics(
            node_count=10,
            edge_count=15,
            density=0.5,
            avg_degree=3.0,
            max_degree=5,
            connected_components=1,
            is_dag=True,
            diameter=5,
            clustering_coefficient=0.3,
        )
        assert metrics.node_count == 10
        assert metrics.is_dag is True


@pytest.mark.unit
class TestGraphAnalyzer:
    """Test GraphAnalyzer."""

    def test_empty_graph_metrics(self, empty_graph: ProgramGraph) -> None:
        """Test metrics on empty graph."""
        analyzer = GraphAnalyzer(empty_graph)
        metrics = analyzer.compute_metrics()

        assert metrics.node_count == 0
        assert metrics.edge_count == 0
        assert metrics.density == 0.0
        assert metrics.avg_degree == 0.0
        assert metrics.max_degree == 0

    def test_simple_dag_metrics(self, simple_dag: ProgramGraph) -> None:
        """Test metrics on simple DAG."""
        analyzer = GraphAnalyzer(simple_dag)
        metrics = analyzer.compute_metrics()

        assert metrics.node_count == 3
        assert metrics.edge_count == 2
        assert metrics.is_dag is True
        assert metrics.connected_components == 1

    def test_cyclic_graph_is_not_dag(self, cyclic_graph: ProgramGraph) -> None:
        """Test that cyclic graph is not detected as DAG."""
        analyzer = GraphAnalyzer(cyclic_graph)
        metrics = analyzer.compute_metrics()

        assert metrics.is_dag is False

    def test_find_cycles_on_dag(self, simple_dag: ProgramGraph) -> None:
        """Test cycle detection on DAG."""
        analyzer = GraphAnalyzer(simple_dag)
        cycles = analyzer.find_cycles()

        assert cycles.has_cycles is False
        assert cycles.cycles == []

    def test_find_cycles_on_cyclic_graph(self, cyclic_graph: ProgramGraph) -> None:
        """Test cycle detection on cyclic graph."""
        analyzer = GraphAnalyzer(cyclic_graph)
        cycles = analyzer.find_cycles()

        assert cycles.has_cycles is True
        assert len(cycles.cycles) > 0

    def test_compute_centrality(self, simple_dag: ProgramGraph) -> None:
        """Test centrality computation."""
        analyzer = GraphAnalyzer(simple_dag)
        centrality = analyzer.compute_centrality()

        assert isinstance(centrality, CentralityScores)
        assert len(centrality.degree_centrality) == 3
        assert len(centrality.betweenness_centrality) == 3

    def test_degree_centrality_values(self, hub_graph: ProgramGraph) -> None:
        """Test that hub node has highest degree centrality."""
        analyzer = GraphAnalyzer(hub_graph)
        centrality = analyzer.compute_centrality()

        center_degree = centrality.degree_centrality["center"]
        leaf_degrees = [centrality.degree_centrality[f"leaf{i}"] for i in range(4)]

        assert center_degree > min(leaf_degrees)

    def test_find_communities(self, simple_dag: ProgramGraph) -> None:
        """Test community detection."""
        analyzer = GraphAnalyzer(simple_dag)
        communities = analyzer.find_communities()

        assert len(communities) > 0
        assert all(isinstance(c, frozenset) for c in communities)

    def test_find_hotspots(self, hub_graph: ProgramGraph) -> None:
        """Test hotspot analysis."""
        analyzer = GraphAnalyzer(hub_graph)
        hotspots = analyzer.find_hotspots()

        assert isinstance(hotspots, HotspotAnalysis)
        assert len(hotspots.hubs) > 0
        assert len(hotspots.sources) > 0

    def test_hotspots_sources_and_sinks(self, simple_dag: ProgramGraph) -> None:
        """Test sources and sinks identification."""
        analyzer = GraphAnalyzer(simple_dag)
        hotspots = analyzer.find_hotspots()

        # In A -> B -> C, A is source, C is sink
        assert "A" in hotspots.sources
        assert "C" in hotspots.sinks

    def test_get_subgraph(self, simple_dag: ProgramGraph) -> None:
        """Test subgraph extraction."""
        analyzer = GraphAnalyzer(simple_dag)
        subgraph = analyzer.get_subgraph({"A", "B"})

        assert subgraph.node_count() == 2
        assert subgraph.edge_count() == 1

    def test_get_subgraph_isolated_nodes(self, simple_dag: ProgramGraph) -> None:
        """Test subgraph with isolated nodes."""
        analyzer = GraphAnalyzer(simple_dag)
        subgraph = analyzer.get_subgraph({"A", "C"})

        assert subgraph.node_count() == 2
        # A -> B -> C, but B not included, so no edge between A and C directly
        assert subgraph.edge_count() == 0

    def test_summary(self, simple_dag: ProgramGraph) -> None:
        """Test summary computation."""
        analyzer = GraphAnalyzer(simple_dag)
        summary = analyzer.summary()

        assert "metrics" in summary
        assert "hotspots" in summary
        assert "cycles" in summary
        assert "centrality_sample" in summary

        assert summary["metrics"]["nodes"] == 3
        assert summary["metrics"]["edges"] == 2
        assert summary["cycles"]["has_cycles"] is False

    def test_to_adjacency_matrix(self, simple_dag: ProgramGraph) -> None:
        """Test conversion to adjacency matrix."""
        analyzer = GraphAnalyzer(simple_dag)
        matrix = analyzer.to_adjacency_matrix()

        assert len(matrix) == 3
        assert all(len(row) == 3 for row in matrix)
        # Should contain 1s for edges, 0s otherwise
        assert all(val in [0, 1] for row in matrix for val in row)

    def test_diameter_on_connected_dag(self, simple_dag: ProgramGraph) -> None:
        """Test diameter computation on connected DAG."""
        analyzer = GraphAnalyzer(simple_dag)
        metrics = analyzer.compute_metrics()

        # A -> B -> C has diameter 2 (longest path)
        assert metrics.diameter == 2

    def test_density_calculation(self, simple_dag: ProgramGraph) -> None:
        """Test density calculation."""
        analyzer = GraphAnalyzer(simple_dag)
        metrics = analyzer.compute_metrics()

        # 3 nodes can have at most 3*2 = 6 edges, we have 2
        # Density = 2 / 6 = 0.333
        assert 0.0 <= metrics.density <= 1.0

    def test_clustering_coefficient(self, hub_graph: ProgramGraph) -> None:
        """Test clustering coefficient computation."""
        analyzer = GraphAnalyzer(hub_graph)
        metrics = analyzer.compute_metrics()

        assert 0.0 <= metrics.clustering_coefficient <= 1.0

    def test_pagerank_computation(self, simple_dag: ProgramGraph) -> None:
        """Test PageRank computation."""
        analyzer = GraphAnalyzer(simple_dag)
        centrality = analyzer.compute_centrality()

        assert len(centrality.pagerank) == 3
        assert all(0.0 <= pr <= 1.0 for pr in centrality.pagerank.values())

    def test_strongly_connected_components(self, cyclic_graph: ProgramGraph) -> None:
        """Test SCC detection on cyclic graph."""
        analyzer = GraphAnalyzer(cyclic_graph)
        cycles = analyzer.find_cycles()

        # Cyclic graph should have SCCs
        assert len(cycles.strongly_connected_components) > 0

    def test_avg_degree_calculation(self, hub_graph: ProgramGraph) -> None:
        """Test average degree calculation."""
        analyzer = GraphAnalyzer(hub_graph)
        metrics = analyzer.compute_metrics()

        # Hub has degree 4, each leaf has degree 1
        # Average = (4 + 1 + 1 + 1 + 1) / 5 = 1.6
        assert metrics.avg_degree > 0
        assert metrics.max_degree == 4

    def test_empty_graph_find_cycles(self, empty_graph: ProgramGraph) -> None:
        """Test cycle detection on empty graph."""
        analyzer = GraphAnalyzer(empty_graph)
        cycles = analyzer.find_cycles()

        assert cycles.has_cycles is False
        assert cycles.cycles == []

    def test_single_node_graph(self) -> None:
        """Test analysis of single-node graph."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)
        node = Node(id="A", kind=NodeKind.FUNCTION, name="A", qualified_name="module.A")
        graph.add_node(node)

        analyzer = GraphAnalyzer(graph)
        metrics = analyzer.compute_metrics()

        assert metrics.node_count == 1
        assert metrics.edge_count == 0
        assert metrics.max_degree == 0

    def test_self_loop(self) -> None:
        """Test graph with self-loop."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        node = Node(id="A", kind=NodeKind.FUNCTION, name="A", qualified_name="module.A")
        graph.add_node(node)

        # Add self-loop
        edge = Edge(id="e1", source_id="A", target_id="A", kind=EdgeKind.CALLS)
        graph.add_edge(edge)

        analyzer = GraphAnalyzer(graph)
        cycles = analyzer.find_cycles()

        assert cycles.has_cycles is True

    def test_disconnected_components(self) -> None:
        """Test graph with multiple disconnected components."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        # Component 1: A -> B
        node_a = Node(id="A", kind=NodeKind.FUNCTION, name="A", qualified_name="module.A")
        node_b = Node(id="B", kind=NodeKind.FUNCTION, name="B", qualified_name="module.B")
        # Component 2: C -> D
        node_c = Node(id="C", kind=NodeKind.FUNCTION, name="C", qualified_name="module.C")
        node_d = Node(id="D", kind=NodeKind.FUNCTION, name="D", qualified_name="module.D")

        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_node(node_c)
        graph.add_node(node_d)

        edge_ab = Edge(id="e1", source_id="A", target_id="B", kind=EdgeKind.CALLS)
        edge_cd = Edge(id="e2", source_id="C", target_id="D", kind=EdgeKind.CALLS)

        graph.add_edge(edge_ab)
        graph.add_edge(edge_cd)

        analyzer = GraphAnalyzer(graph)
        metrics = analyzer.compute_metrics()

        assert metrics.connected_components == 2

    def test_closeness_centrality(self, simple_dag: ProgramGraph) -> None:
        """Test closeness centrality computation."""
        analyzer = GraphAnalyzer(simple_dag)
        centrality = analyzer.compute_centrality()

        assert len(centrality.closeness_centrality) == 3
        assert all(0.0 <= c <= 1.0 for c in centrality.closeness_centrality.values())

    def test_betweenness_centrality(self, simple_dag: ProgramGraph) -> None:
        """Test betweenness centrality computation."""
        analyzer = GraphAnalyzer(simple_dag)
        centrality = analyzer.compute_centrality()

        # B is between A and C, should have non-zero betweenness
        b_betweenness = centrality.betweenness_centrality.get("B", 0.0)
        assert b_betweenness > 0.0
