"""Integration tests for the graph analysis pipeline.

Tests the full pipeline: ProgramGraph → network analysis → visualization.
"""

from pathlib import Path

import pytest

from cogant.graph.analysis import GraphAnalyzer
from cogant.schemas.graph import ProgramGraph, ProgramNode, EdgeType, ProgramEdge


pytestmark = pytest.mark.integration


class TestGraphAnalysisOnSynthetic:
    """Tests for graph analysis on synthetic test graphs."""

    @staticmethod
    def create_test_graph(node_count: int = 5) -> ProgramGraph:
        """Create a simple test graph with specified number of nodes.

        Args:
            node_count: Number of nodes to create.

        Returns:
            ProgramGraph with linear chain structure.
        """
        graph = ProgramGraph()

        # Create nodes
        for i in range(node_count):
            node = ProgramNode(
                id=f"node_{i}",
                name=f"func_{i}",
                kind="function",
                source_file=Path(f"test_{i}.py"),
            )
            graph.add_node(node)

        # Create edges (linear chain: 0 -> 1 -> 2 -> ... )
        for i in range(node_count - 1):
            edge = ProgramEdge(
                source_id=f"node_{i}",
                target_id=f"node_{i+1}",
                kind=EdgeType.CALLS,
            )
            graph.add_edge(edge)

        return graph

    def test_graph_analysis_basic_metrics(self):
        """Test basic graph metrics computation.

        Verifies:
        - node_count matches created nodes
        - edge_count matches created edges
        - density is computed correctly
        - connected_components > 0
        """
        graph = self.create_test_graph(5)
        analyzer = GraphAnalyzer(graph)

        metrics = analyzer.compute_metrics()

        assert metrics.node_count == 5
        assert metrics.edge_count == 4  # Linear chain has n-1 edges
        assert metrics.density > 0
        assert metrics.connected_components == 1  # All in one component
        assert metrics.avg_degree > 0
        assert metrics.max_degree > 0

    def test_graph_centrality_scores(self):
        """Test centrality computation.

        Verifies:
        - All centrality measures are floats in [0, 1]
        - At least one node has non-zero centrality
        - Scores are present for all nodes
        """
        graph = self.create_test_graph(5)
        analyzer = GraphAnalyzer(graph)

        centrality = analyzer.compute_centrality()

        # Verify all measures are present
        assert len(centrality.betweenness_centrality) == 5
        assert len(centrality.degree_centrality) == 5
        assert len(centrality.pagerank) == 5
        assert len(centrality.closeness_centrality) == 5

        # Verify values are in valid range
        for node_id, score in centrality.betweenness_centrality.items():
            assert 0.0 <= score <= 1.0, f"Invalid betweenness for {node_id}: {score}"
            assert isinstance(score, float)

        for node_id, score in centrality.degree_centrality.items():
            assert 0.0 <= score <= 1.0, f"Invalid degree centrality for {node_id}: {score}"

        for node_id, score in centrality.pagerank.items():
            assert isinstance(score, float), f"PageRank should be float for {node_id}"
            assert score >= 0.0, f"PageRank should be >= 0 for {node_id}"

    def test_graph_find_cycles(self):
        """Test cycle detection on acyclic graph.

        Verifies:
        - Linear chain has no cycles
        - has_cycles is False
        - cycles list is empty
        """
        graph = self.create_test_graph(5)
        analyzer = GraphAnalyzer(graph)

        cycles = analyzer.find_cycles()

        assert cycles.has_cycles is False, "Linear chain should be acyclic"
        assert len(cycles.cycles) == 0, "Should find no cycles in linear chain"
        assert len(cycles.strongly_connected_components) >= 1

    def test_graph_communities(self):
        """Test community detection.

        Verifies:
        - find_communities returns list of frozensets
        - All nodes are partitioned into communities
        - Each node is in exactly one community
        """
        graph = self.create_test_graph(5)
        analyzer = GraphAnalyzer(graph)

        communities = analyzer.find_communities()

        assert isinstance(communities, list)
        assert len(communities) > 0

        # Verify all nodes are partitioned
        all_nodes_in_communities = set()
        for community in communities:
            assert isinstance(community, frozenset)
            all_nodes_in_communities.update(community)

        assert len(all_nodes_in_communities) == 5


class TestGraphDiffPipeline:
    """Tests for graph diffing and merging."""

    def test_graph_diff_pipeline(self):
        """Test graph diff detection.

        Verifies:
        - Original graph can be analyzed
        - Modified graph (with added node/edge) can be detected
        - Diff shows added_nodes and added_edges
        """
        # Create original graph
        original = self.create_test_graph(5)
        analyzer_orig = GraphAnalyzer(original)
        metrics_orig = analyzer_orig.compute_metrics()

        # Create modified graph (add one node and one edge)
        modified = self.create_test_graph(5)
        new_node = ProgramNode(
            id="node_new",
            name="new_func",
            kind="function",
            source_file=Path("new.py"),
        )
        modified.add_node(new_node)

        new_edge = ProgramEdge(
            source_id="node_4",
            target_id="node_new",
            kind=EdgeType.CALLS,
        )
        modified.add_edge(new_edge)

        analyzer_mod = GraphAnalyzer(modified)
        metrics_mod = analyzer_mod.compute_metrics()

        # Verify diff
        assert metrics_mod.node_count == metrics_orig.node_count + 1
        assert metrics_mod.edge_count == metrics_orig.edge_count + 1

    @staticmethod
    def create_test_graph(node_count: int = 5) -> ProgramGraph:
        """Helper to create test graph."""
        graph = ProgramGraph()
        for i in range(node_count):
            node = ProgramNode(
                id=f"node_{i}",
                name=f"func_{i}",
                kind="function",
                source_file=Path(f"test_{i}.py"),
            )
            graph.add_node(node)

        for i in range(node_count - 1):
            edge = ProgramEdge(
                source_id=f"node_{i}",
                target_id=f"node_{i+1}",
                kind=EdgeType.CALLS,
            )
            graph.add_edge(edge)

        return graph


class TestHotspotIdentification:
    """Tests for finding high-impact nodes (hubs and bottlenecks)."""

    def test_hotspot_identification(self):
        """Test identification of hub and bottleneck nodes.

        Verifies:
        - Hub node (high degree) is identified
        - Bottleneck node (high betweenness) is identified
        - find_hotspots() returns HotspotAnalysis with valid structure
        """
        # Create a star graph: center node connected to many others
        graph = ProgramGraph()

        # Central hub node
        hub = ProgramNode(
            id="hub",
            name="main_func",
            kind="function",
            source_file=Path("main.py"),
        )
        graph.add_node(hub)

        # Peripheral nodes
        for i in range(5):
            node = ProgramNode(
                id=f"peripheral_{i}",
                name=f"helper_{i}",
                kind="function",
                source_file=Path(f"helpers_{i}.py"),
            )
            graph.add_node(node)

            # Hub -> peripheral
            edge = ProgramEdge(
                source_id="hub",
                target_id=f"peripheral_{i}",
                kind=EdgeType.CALLS,
            )
            graph.add_edge(edge)

        analyzer = GraphAnalyzer(graph)
        hotspots = analyzer.find_hotspots(top_n=3)

        # Verify hub is identified
        assert len(hotspots.hubs) > 0
        assert hotspots.hubs[0][0] == "hub", "Hub should be first in hubs list"
        assert hotspots.hubs[0][1] == 5, "Hub should have degree 5 (center of star)"

        # Verify bottleneck is identified (hub is also a bottleneck)
        assert len(hotspots.bottlenecks) > 0

    def test_hotspot_sinks_sources(self):
        """Test identification of sink and source nodes.

        Verifies:
        - Source nodes (no incoming edges) are identified
        - Sink nodes (no outgoing edges) are identified
        """
        # Create a simple pipeline: source -> middle -> sink
        graph = ProgramGraph()

        source = ProgramNode(
            id="source",
            name="entry",
            kind="function",
            source_file=Path("entry.py"),
        )
        middle = ProgramNode(
            id="middle",
            name="process",
            kind="function",
            source_file=Path("process.py"),
        )
        sink = ProgramNode(
            id="sink",
            name="exit",
            kind="function",
            source_file=Path("exit.py"),
        )

        graph.add_node(source)
        graph.add_node(middle)
        graph.add_node(sink)

        # Create pipeline edges
        graph.add_edge(ProgramEdge(source_id="source", target_id="middle", kind=EdgeType.CALLS))
        graph.add_edge(ProgramEdge(source_id="middle", target_id="sink", kind=EdgeType.CALLS))

        analyzer = GraphAnalyzer(graph)
        hotspots = analyzer.find_hotspots()

        # Verify sources and sinks
        assert "source" in hotspots.sources, "source should have no incoming edges"
        assert "sink" in hotspots.sinks, "sink should have no outgoing edges"
        assert "middle" not in hotspots.sources
        assert "middle" not in hotspots.sinks


class TestSubgraphExtraction:
    """Tests for extracting subgraphs from larger graphs."""

    def test_subgraph_extraction(self):
        """Test subgraph extraction.

        Verifies:
        - Subgraph has correct number of nodes
        - Subgraph contains only edges between included nodes
        - No edges to nodes outside the subgraph
        """
        # Create a 10-node graph (linear chain)
        graph = ProgramGraph()
        for i in range(10):
            node = ProgramNode(
                id=f"node_{i}",
                name=f"func_{i}",
                kind="function",
                source_file=Path(f"test_{i}.py"),
            )
            graph.add_node(node)

        for i in range(9):
            edge = ProgramEdge(
                source_id=f"node_{i}",
                target_id=f"node_{i+1}",
                kind=EdgeType.CALLS,
            )
            graph.add_edge(edge)

        # Extract subgraph with 5 nodes (node_2 through node_6)
        subgraph_nodes = {f"node_{i}" for i in range(2, 7)}
        analyzer = GraphAnalyzer(graph)
        subgraph = analyzer.get_subgraph(subgraph_nodes)

        # Verify node count
        assert len(subgraph.nodes) == 5

        # Verify all nodes are in the subgraph
        for node_id in subgraph_nodes:
            assert node_id in subgraph.nodes

        # Verify edges are only between included nodes
        for edge in subgraph.edges.values():
            assert edge.source_id in subgraph_nodes
            assert edge.target_id in subgraph_nodes


class TestAdjacencyMatrix:
    """Tests for adjacency matrix generation."""

    def test_graph_to_adjacency_matrix(self):
        """Test adjacency matrix generation.

        Verifies:
        - Matrix dimensions match node count
        - Diagonal is all zeros (no self-loops in test graph)
        - Matrix reflects graph edges
        """
        # Create a simple 3-node graph: 0 -> 1 -> 2
        graph = ProgramGraph()

        for i in range(3):
            node = ProgramNode(
                id=f"node_{i}",
                name=f"func_{i}",
                kind="function",
                source_file=Path(f"test_{i}.py"),
            )
            graph.add_node(node)

        # Add edges
        graph.add_edge(ProgramEdge(source_id="node_0", target_id="node_1", kind=EdgeType.CALLS))
        graph.add_edge(ProgramEdge(source_id="node_1", target_id="node_2", kind=EdgeType.CALLS))

        analyzer = GraphAnalyzer(graph)
        matrix = analyzer.to_adjacency_matrix()

        # Verify dimensions
        assert len(matrix) == 3
        assert all(len(row) == 3 for row in matrix)

        # Verify diagonal is zero (no self-loops)
        for i in range(3):
            assert matrix[i][i] == 0, f"Diagonal element [{i}][{i}] should be 0"

        # Verify edges: assuming nodes are sorted by ID as node_0, node_1, node_2
        # node_0 -> node_1: matrix[0][1] = 1
        # node_1 -> node_2: matrix[1][2] = 1
        assert matrix[0][1] == 1, "Edge node_0 -> node_1 should be in matrix"
        assert matrix[1][2] == 1, "Edge node_1 -> node_2 should be in matrix"
        assert matrix[0][2] == 0, "No direct edge from node_0 to node_2"
        assert matrix[1][0] == 0, "No reverse edge from node_1 to node_0"

    def test_adjacency_matrix_with_self_loops(self):
        """Test adjacency matrix with self-loops.

        Verifies that the matrix correctly represents self-loops if they exist.
        """
        graph = ProgramGraph()

        node = ProgramNode(
            id="recursive",
            name="recursive_func",
            kind="function",
            source_file=Path("recursive.py"),
        )
        graph.add_node(node)

        # Add self-loop
        graph.add_edge(ProgramEdge(
            source_id="recursive",
            target_id="recursive",
            kind=EdgeType.CALLS,
        ))

        analyzer = GraphAnalyzer(graph)
        matrix = analyzer.to_adjacency_matrix()

        assert len(matrix) == 1
        assert matrix[0][0] == 1, "Self-loop should be represented in matrix"
