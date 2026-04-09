"""Comprehensive tests for COGANT schema validation."""

import pytest
from datetime import datetime, timezone

from cogant.schemas.core import Node, Edge, NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph, GraphMetadata


class TestNodeSchema:
    """Tests for Node schema validation."""

    def test_node_creation_with_minimal_fields(self):
        """Test creating a node with minimal required fields."""
        node = Node(
            id="test:node1",
            kind=NodeKind.MODULE,
            name="module1",
            qualified_name="test.module1"
        )

        assert node.id == "test:node1"
        assert node.kind == NodeKind.MODULE
        assert node.name == "module1"
        assert node.qualified_name == "test.module1"

    def test_node_with_all_fields(self):
        """Test node with all attributes."""
        node = Node(
            id="test:func1",
            kind=NodeKind.FUNCTION,
            name="my_func",
            qualified_name="test.MyClass.my_func",
            path="test.py",
            language="python",
            source_range={"start": 10, "end": 20, "column": 0},
            metadata={"is_public": True, "decorators": ["@decorator"]}
        )

        assert node.id == "test:func1"
        assert node.kind == NodeKind.FUNCTION
        assert node.name == "my_func"
        assert node.path == "test.py"
        assert node.language == "python"
        assert node.source_range["start"] == 10
        assert node.metadata["is_public"] is True

    def test_node_kinds_enumeration(self):
        """Test all NodeKind enumeration values."""
        expected_kinds = {
            NodeKind.REPO, NodeKind.MODULE, NodeKind.FILE, NodeKind.CLASS,
            NodeKind.FUNCTION, NodeKind.METHOD, NodeKind.VARIABLE,
            NodeKind.ENDPOINT, NodeKind.EVENT, NodeKind.PARAMETER,
            NodeKind.RETURN_VALUE, NodeKind.DATA_STRUCTURE,
            NodeKind.CONFIGURATION, NodeKind.FEATURE_FLAG, NodeKind.TEST,
            NodeKind.ASSERTION, NodeKind.POLICY, NodeKind.ACTION
        }

        actual_kinds = set(NodeKind)
        assert len(actual_kinds) >= 18
        assert expected_kinds.issubset(actual_kinds)

    def test_node_equality(self):
        """Test node equality based on ID."""
        node1 = Node(
            id="test:node1",
            kind=NodeKind.CLASS,
            name="MyClass",
            qualified_name="test.MyClass"
        )
        node2 = Node(
            id="test:node1",
            kind=NodeKind.CLASS,
            name="MyClass",
            qualified_name="test.MyClass"
        )
        node3 = Node(
            id="test:node2",
            kind=NodeKind.CLASS,
            name="OtherClass",
            qualified_name="test.OtherClass"
        )

        assert node1 == node2
        assert node1 != node3

    def test_node_hashing(self):
        """Test node can be used in sets/dicts."""
        node1 = Node(
            id="test:node1",
            kind=NodeKind.FUNCTION,
            name="func",
            qualified_name="test.func"
        )
        node2 = Node(
            id="test:node2",
            kind=NodeKind.FUNCTION,
            name="func2",
            qualified_name="test.func2"
        )

        node_set = {node1, node2}
        assert len(node_set) == 2
        assert node1 in node_set

    def test_node_created_at_timestamp(self):
        """Test node has creation timestamp."""
        before = datetime.now(timezone.utc)
        node = Node(
            id="test:node1",
            kind=NodeKind.MODULE,
            name="test",
            qualified_name="test"
        )
        after = datetime.now(timezone.utc)

        assert before <= node.created_at <= after

    def test_node_with_metadata(self):
        """Test node metadata handling."""
        metadata = {
            "visibility": "public",
            "decorators": ["@cached", "@property"],
            "custom": {"level": 5}
        }
        node = Node(
            id="test:node1",
            kind=NodeKind.FUNCTION,
            name="func",
            qualified_name="test.func",
            metadata=metadata
        )

        assert node.metadata["visibility"] == "public"
        assert len(node.metadata["decorators"]) == 2
        assert node.metadata["custom"]["level"] == 5


class TestEdgeSchema:
    """Tests for Edge schema validation."""

    def test_edge_creation_with_minimal_fields(self):
        """Test creating an edge with minimal required fields."""
        edge = Edge(
            id="edge1",
            source_id="node1",
            target_id="node2",
            kind=EdgeKind.CALLS
        )

        assert edge.id == "edge1"
        assert edge.source_id == "node1"
        assert edge.target_id == "node2"
        assert edge.kind == EdgeKind.CALLS
        assert edge.weight == 1.0

    def test_edge_with_all_fields(self):
        """Test edge with all attributes."""
        edge = Edge(
            id="edge1",
            source_id="func1",
            target_id="func2",
            kind=EdgeKind.CALLS,
            weight=0.85,
            metadata={"call_count": 5},
            evidence_sources=["static_analysis", "dynamic_trace"]
        )

        assert edge.weight == 0.85
        assert edge.metadata["call_count"] == 5
        assert len(edge.evidence_sources) == 2

    def test_edge_kinds_enumeration(self):
        """Test all EdgeKind enumeration values."""
        expected_kinds = {
            EdgeKind.CONTAINS, EdgeKind.IMPORTS, EdgeKind.INHERITS,
            EdgeKind.IMPLEMENTS, EdgeKind.DEPENDS_ON, EdgeKind.READS,
            EdgeKind.WRITES, EdgeKind.RETURNS, EdgeKind.CALLS,
            EdgeKind.THROWS, EdgeKind.CATCHES, EdgeKind.YIELDS,
            EdgeKind.OBSERVES, EdgeKind.MUTATES, EdgeKind.GUARDS,
            EdgeKind.TRIGGERS, EdgeKind.EVIDENCE_FROM_STATIC,
            EdgeKind.EVIDENCE_FROM_DYNAMIC
        }

        actual_kinds = set(EdgeKind)
        assert len(actual_kinds) >= 18
        assert expected_kinds.issubset(actual_kinds)

    def test_edge_equality(self):
        """Test edge equality based on ID."""
        edge1 = Edge(
            id="edge1",
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.CALLS
        )
        edge2 = Edge(
            id="edge1",
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.CALLS
        )
        edge3 = Edge(
            id="edge2",
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.CALLS
        )

        assert edge1 == edge2
        assert edge1 != edge3

    def test_edge_hashing(self):
        """Test edge can be used in sets/dicts."""
        edge1 = Edge(
            id="edge1",
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.CALLS
        )
        edge2 = Edge(
            id="edge2",
            source_id="n2",
            target_id="n3",
            kind=EdgeKind.CALLS
        )

        edge_set = {edge1, edge2}
        assert len(edge_set) == 2
        assert edge1 in edge_set

    def test_edge_created_at_timestamp(self):
        """Test edge has creation timestamp."""
        before = datetime.now(timezone.utc)
        edge = Edge(
            id="edge1",
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.CONTAINS
        )
        after = datetime.now(timezone.utc)

        assert before <= edge.created_at <= after

    def test_edge_weight_default(self):
        """Test edge weight defaults to 1.0."""
        edge = Edge(
            id="e1",
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.CALLS
        )
        assert edge.weight == 1.0

    def test_edge_evidence_sources(self):
        """Test edge evidence sources tracking."""
        edge = Edge(
            id="e1",
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.CALLS,
            evidence_sources=["static", "dynamic"]
        )
        assert len(edge.evidence_sources) == 2
        assert "static" in edge.evidence_sources


class TestProgramGraph:
    """Tests for ProgramGraph schema."""

    def test_graph_creation(self):
        """Test creating a program graph."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        assert graph.metadata.repo_uri == "test://repo"
        assert graph.node_count() == 0
        assert graph.edge_count() == 0

    def test_add_node(self):
        """Test adding nodes to graph."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        node = Node(
            id="n1",
            kind=NodeKind.MODULE,
            name="mod",
            qualified_name="test.mod"
        )
        graph.add_node(node)

        assert graph.node_count() == 1
        assert graph.get_node("n1") == node

    def test_add_multiple_nodes(self):
        """Test adding multiple nodes."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        for i in range(5):
            node = Node(
                id=f"n{i}",
                kind=NodeKind.FUNCTION,
                name=f"func{i}",
                qualified_name=f"test.func{i}"
            )
            graph.add_node(node)

        assert graph.node_count() == 5

    def test_get_node(self):
        """Test retrieving a node by ID."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        node = Node(
            id="test_node",
            kind=NodeKind.CLASS,
            name="TestClass",
            qualified_name="test.TestClass"
        )
        graph.add_node(node)

        retrieved = graph.get_node("test_node")
        assert retrieved == node

    def test_get_nonexistent_node(self):
        """Test retrieving nonexistent node returns None."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        assert graph.get_node("nonexistent") is None

    def test_get_nodes_by_kind(self):
        """Test retrieving nodes by kind."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        # Add nodes of different kinds
        kinds = [NodeKind.MODULE, NodeKind.CLASS, NodeKind.CLASS]
        for i, kind in enumerate(kinds):
            node = Node(
                id=f"node_{kind.value}_{i}",
                kind=kind,
                name=f"name_{kind.value}_{i}",
                qualified_name=f"test.name_{kind.value}_{i}"
            )
            graph.add_node(node)

        classes = graph.get_nodes_by_kind(NodeKind.CLASS)
        assert len(classes) == 2
        assert all(n.kind == NodeKind.CLASS for n in classes)

    def test_add_edge(self):
        """Test adding edges to graph."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        # Add nodes first
        for i in range(2):
            node = Node(
                id=f"n{i}",
                kind=NodeKind.FUNCTION,
                name=f"func{i}",
                qualified_name=f"test.func{i}"
            )
            graph.add_node(node)

        # Add edge
        edge = Edge(
            id="e1",
            source_id="n0",
            target_id="n1",
            kind=EdgeKind.CALLS
        )
        graph.add_edge(edge)

        assert graph.edge_count() == 1

    def test_add_edge_without_nodes_fails(self):
        """Test adding edge with nonexistent nodes."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        edge = Edge(
            id="e1",
            source_id="nonexistent1",
            target_id="nonexistent2",
            kind=EdgeKind.CALLS
        )
        graph.add_edge(edge)

        # Edge should not be added
        assert graph.edge_count() == 0

    def test_get_edges_from(self):
        """Test getting outgoing edges from a node."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        # Setup nodes
        for i in range(3):
            graph.add_node(Node(
                id=f"n{i}",
                kind=NodeKind.FUNCTION,
                name=f"f{i}",
                qualified_name=f"test.f{i}"
            ))

        # Add edges from n0
        graph.add_edge(Edge(
            id="e1",
            source_id="n0",
            target_id="n1",
            kind=EdgeKind.CALLS
        ))
        graph.add_edge(Edge(
            id="e2",
            source_id="n0",
            target_id="n2",
            kind=EdgeKind.CALLS
        ))

        outgoing = graph.get_edges_from("n0")
        assert len(outgoing) == 2
        assert all(e.source_id == "n0" for e in outgoing)

    def test_get_edges_to(self):
        """Test getting incoming edges to a node."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        # Setup nodes
        for i in range(3):
            graph.add_node(Node(
                id=f"n{i}",
                kind=NodeKind.FUNCTION,
                name=f"f{i}",
                qualified_name=f"test.f{i}"
            ))

        # Add edges to n2
        graph.add_edge(Edge(
            id="e1",
            source_id="n0",
            target_id="n2",
            kind=EdgeKind.CALLS
        ))
        graph.add_edge(Edge(
            id="e2",
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.CALLS
        ))

        incoming = graph.get_edges_to("n2")
        assert len(incoming) == 2
        assert all(e.target_id == "n2" for e in incoming)

    def test_get_edges_by_kind(self):
        """Test retrieving edges by kind."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        # Setup
        for i in range(3):
            graph.add_node(Node(
                id=f"n{i}",
                kind=NodeKind.FUNCTION,
                name=f"f{i}",
                qualified_name=f"test.f{i}"
            ))

        # Add different edge types
        graph.add_edge(Edge(
            id="e1",
            source_id="n0",
            target_id="n1",
            kind=EdgeKind.CALLS
        ))
        graph.add_edge(Edge(
            id="e2",
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.CALLS
        ))
        graph.add_edge(Edge(
            id="e3",
            source_id="n0",
            target_id="n2",
            kind=EdgeKind.READS
        ))

        call_edges = graph.get_edges_by_kind(EdgeKind.CALLS)
        assert len(call_edges) == 2
        assert all(e.kind == EdgeKind.CALLS for e in call_edges)

    def test_remove_node(self):
        """Test removing a node also removes associated edges."""
        metadata = GraphMetadata(repo_uri="test://repo")
        graph = ProgramGraph(metadata=metadata)

        # Setup
        for i in range(3):
            graph.add_node(Node(
                id=f"n{i}",
                kind=NodeKind.FUNCTION,
                name=f"f{i}",
                qualified_name=f"test.f{i}"
            ))

        # Add edges
        graph.add_edge(Edge(
            id="e1",
            source_id="n0",
            target_id="n1",
            kind=EdgeKind.CALLS
        ))
        graph.add_edge(Edge(
            id="e2",
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.CALLS
        ))

        # Remove node
        graph.remove_node("n1")

        assert graph.node_count() == 2
        assert graph.edge_count() == 0

    def test_graph_statistics(self):
        """Test graph statistics methods."""
        metadata = GraphMetadata(repo_uri="test://repo", languages={"python"})
        graph = ProgramGraph(metadata=metadata)

        # Add multiple nodes and edges
        for i in range(5):
            graph.add_node(Node(
                id=f"n{i}",
                kind=NodeKind.FUNCTION if i % 2 == 0 else NodeKind.CLASS,
                name=f"item{i}",
                qualified_name=f"test.item{i}"
            ))

        for i in range(4):
            graph.add_edge(Edge(
                id=f"e{i}",
                source_id=f"n{i}",
                target_id=f"n{i+1}",
                kind=EdgeKind.CALLS
            ))

        assert graph.node_count() == 5
        assert graph.edge_count() == 4
