"""Unit tests for :class:`cogant.graph.builder.ProgramGraphBuilder`.

These tests exercise the real ``ProgramGraphBuilder`` class rather than
operating on toy ``dict`` structures. They cover construction, node/edge
addition (including idempotent re-adds), lookup, neighbor/path queries,
subgraph extraction, connected components, cycle finding, statistics,
and finalization.

The graphs here are built by hand so the expected node/edge counts are
deterministic — there is no I/O or randomness, and every assertion
exercises a concrete method on the ``ProgramGraphBuilder`` or
``ProgramGraph`` instance.
"""

from __future__ import annotations

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, Node, NodeKind
from cogant.schemas.graph import ProgramGraph

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- fixtures


@pytest.fixture
def builder() -> ProgramGraphBuilder:
    """Fresh builder seeded with a known repo URI."""
    return ProgramGraphBuilder(repo_uri="test://unit-repo")


@pytest.fixture
def populated_builder() -> ProgramGraphBuilder:
    """Builder pre-populated with a small module/class/function graph."""
    b = ProgramGraphBuilder(repo_uri="test://populated")
    module = b.add_node(
        kind=NodeKind.MODULE,
        name="app",
        qualified_name="app",
        path="app.py",
        language="python",
    )
    cls = b.add_node(
        kind=NodeKind.CLASS,
        name="Service",
        qualified_name="app.Service",
        path="app.py",
        language="python",
    )
    fn = b.add_node(
        kind=NodeKind.FUNCTION,
        name="run",
        qualified_name="app.Service.run",
        path="app.py",
        language="python",
    )
    b.add_edge(module.id, cls.id, EdgeKind.CONTAINS)
    b.add_edge(cls.id, fn.id, EdgeKind.CONTAINS)
    return b


# ------------------------------------------------------------------ construction


class TestProgramGraphBuilderConstruction:
    """Tests for ProgramGraphBuilder construction and initial state."""

    def test_builder_constructs_empty_graph(self, builder: ProgramGraphBuilder) -> None:
        assert isinstance(builder.graph, ProgramGraph)
        assert builder.graph.node_count() == 0
        assert builder.graph.edge_count() == 0

    def test_builder_stores_repo_uri(self, builder: ProgramGraphBuilder) -> None:
        assert builder.repo_uri == "test://unit-repo"
        assert builder.graph.metadata.repo_uri == "test://unit-repo"

    def test_builder_has_identity_resolver(self, builder: ProgramGraphBuilder) -> None:
        assert builder.identity_resolver is not None


# --------------------------------------------------------------------- add_node


class TestAddNode:
    """Tests for the ``add_node`` happy path and idempotency."""

    def test_add_node_returns_node_with_stable_id(self, builder: ProgramGraphBuilder) -> None:
        node = builder.add_node(
            kind=NodeKind.FUNCTION,
            name="calculate",
            qualified_name="math_utils.calculate",
            path="math_utils.py",
            language="python",
        )
        assert isinstance(node, Node)
        assert node.kind is NodeKind.FUNCTION
        assert node.name == "calculate"
        assert node.language == "python"
        assert node.id  # non-empty stable id
        assert builder.graph.get_node(node.id) is node

    def test_add_node_is_idempotent_by_identity(self, builder: ProgramGraphBuilder) -> None:
        first = builder.add_node(
            kind=NodeKind.CLASS,
            name="User",
            qualified_name="app.User",
            path="app.py",
            language="python",
        )
        second = builder.add_node(
            kind=NodeKind.CLASS,
            name="User",
            qualified_name="app.User",
            path="app.py",
            language="python",
        )
        assert first.id == second.id
        assert builder.graph.node_count() == 1

    def test_languages_tracked_in_metadata(self, builder: ProgramGraphBuilder) -> None:
        builder.add_node(
            kind=NodeKind.MODULE,
            name="m",
            qualified_name="m",
            language="python",
        )
        builder.add_node(
            kind=NodeKind.MODULE,
            name="t",
            qualified_name="t",
            language="typescript",
        )
        assert "python" in builder.graph.metadata.languages
        assert "typescript" in builder.graph.metadata.languages


# --------------------------------------------------------------------- add_edge


class TestAddEdge:
    """Tests for the ``add_edge`` method."""

    def test_add_edge_connects_existing_nodes(self, populated_builder: ProgramGraphBuilder) -> None:
        assert populated_builder.graph.edge_count() == 2
        # All edges must reference existing nodes
        for edge in populated_builder.graph.edges.values():
            assert populated_builder.graph.get_node(edge.source_id) is not None
            assert populated_builder.graph.get_node(edge.target_id) is not None

    def test_add_edge_rejects_missing_source(self, builder: ProgramGraphBuilder) -> None:
        target = builder.add_node(kind=NodeKind.CLASS, name="C", qualified_name="C")
        result = builder.add_edge(
            source_id="nonexistent", target_id=target.id, kind=EdgeKind.CONTAINS
        )
        assert result is None
        assert builder.graph.edge_count() == 0

    def test_add_edge_rejects_missing_target(self, builder: ProgramGraphBuilder) -> None:
        source = builder.add_node(kind=NodeKind.MODULE, name="m", qualified_name="m")
        result = builder.add_edge(
            source_id=source.id, target_id="nonexistent", kind=EdgeKind.CONTAINS
        )
        assert result is None
        assert builder.graph.edge_count() == 0

    def test_add_edge_dedupes_and_merges_evidence(self, builder: ProgramGraphBuilder) -> None:
        a = builder.add_node(kind=NodeKind.MODULE, name="a", qualified_name="a")
        b = builder.add_node(kind=NodeKind.MODULE, name="b", qualified_name="b")

        first = builder.add_edge(
            a.id,
            b.id,
            EdgeKind.IMPORTS,
            weight=0.5,
            evidence_sources=["static"],
        )
        second = builder.add_edge(
            a.id,
            b.id,
            EdgeKind.IMPORTS,
            weight=0.9,
            evidence_sources=["dynamic"],
        )
        assert first is not None and second is not None
        assert first.id == second.id
        assert builder.graph.edge_count() == 1
        assert first.weight == 0.9  # max(0.5, 0.9)
        assert set(first.evidence_sources) == {"static", "dynamic"}


# -------------------------------------------------------------- queries & paths


class TestQueries:
    """Tests for queries exposed by the builder."""

    def test_get_node_by_id(self, populated_builder: ProgramGraphBuilder) -> None:
        # Grab any known node id
        any_id = next(iter(populated_builder.graph.nodes))
        fetched = populated_builder.get_node(any_id)
        assert fetched is not None
        assert fetched.id == any_id

    def test_get_node_returns_none_for_missing(
        self, populated_builder: ProgramGraphBuilder
    ) -> None:
        assert populated_builder.get_node("nope") is None

    def test_get_neighbors_returns_connected(self, populated_builder: ProgramGraphBuilder) -> None:
        module_id = next(
            n.id for n in populated_builder.graph.nodes.values() if n.kind is NodeKind.MODULE
        )
        neighbors = populated_builder.get_neighbors(module_id)
        names = {n.name for n in neighbors}
        assert "Service" in names

    def test_find_path_same_node(self, populated_builder: ProgramGraphBuilder) -> None:
        node_id = next(iter(populated_builder.graph.nodes))
        assert populated_builder.find_path(node_id, node_id) == [node_id]

    def test_find_path_transitive(self, populated_builder: ProgramGraphBuilder) -> None:
        module_id = next(
            n.id for n in populated_builder.graph.nodes.values() if n.kind is NodeKind.MODULE
        )
        function_id = next(
            n.id for n in populated_builder.graph.nodes.values() if n.kind is NodeKind.FUNCTION
        )
        path = populated_builder.find_path(module_id, function_id)
        assert path is not None
        assert path[0] == module_id
        assert path[-1] == function_id
        assert len(path) == 3  # module -> class -> function


# --------------------------------------------------------------------- subgraph


class TestSubgraph:
    """Tests for ``get_subgraph``."""

    def test_subgraph_contains_only_requested_nodes(
        self, populated_builder: ProgramGraphBuilder
    ) -> None:
        some_id = next(iter(populated_builder.graph.nodes))
        sub = populated_builder.get_subgraph([some_id], include_neighbors=False)
        assert sub.node_count() == 1
        assert some_id in sub.nodes

    def test_subgraph_includes_neighbors_when_asked(
        self, populated_builder: ProgramGraphBuilder
    ) -> None:
        module_id = next(
            n.id for n in populated_builder.graph.nodes.values() if n.kind is NodeKind.MODULE
        )
        sub = populated_builder.get_subgraph([module_id], include_neighbors=True)
        assert sub.node_count() >= 2  # module + at least its class


# ------------------------------------------------------- components & analytics


class TestGraphAnalytics:
    """Tests for connected-component, cycle, and statistics helpers."""

    def test_connected_components_single(self, populated_builder: ProgramGraphBuilder) -> None:
        components = populated_builder.get_connected_components()
        assert len(components) == 1
        assert len(components[0]) == 3

    def test_connected_components_multiple(self, builder: ProgramGraphBuilder) -> None:
        m1 = builder.add_node(kind=NodeKind.MODULE, name="m1", qualified_name="m1")
        m2 = builder.add_node(kind=NodeKind.MODULE, name="m2", qualified_name="m2")
        m3 = builder.add_node(kind=NodeKind.MODULE, name="m3", qualified_name="m3")
        builder.add_edge(m1.id, m2.id, EdgeKind.IMPORTS)
        # m3 isolated
        _ = m3
        components = builder.get_connected_components()
        assert len(components) == 2
        sizes = sorted(len(c) for c in components)
        assert sizes == [1, 2]

    def test_find_cycles_empty_for_isolated_nodes(self, builder: ProgramGraphBuilder) -> None:
        # No edges → no cycles regardless of undirected traversal semantics.
        builder.add_node(kind=NodeKind.FUNCTION, name="solo", qualified_name="solo")
        assert builder.find_cycles() == []

    def test_find_cycles_detects_triangle(self, builder: ProgramGraphBuilder) -> None:
        a = builder.add_node(kind=NodeKind.FUNCTION, name="a", qualified_name="a")
        b = builder.add_node(kind=NodeKind.FUNCTION, name="b", qualified_name="b")
        c = builder.add_node(kind=NodeKind.FUNCTION, name="c", qualified_name="c")
        builder.add_edge(a.id, b.id, EdgeKind.CALLS)
        builder.add_edge(b.id, c.id, EdgeKind.CALLS)
        builder.add_edge(c.id, a.id, EdgeKind.CALLS)
        cycles = builder.find_cycles()
        assert cycles  # at least one detected

    def test_get_statistics_reports_correct_counts(
        self, populated_builder: ProgramGraphBuilder
    ) -> None:
        stats = populated_builder.get_statistics()
        assert stats["total_nodes"] == 3
        assert stats["total_edges"] == 2
        assert stats["connected_components"] == 1
        assert stats["nodes_by_kind"]["module"] == 1
        assert stats["nodes_by_kind"]["class"] == 1
        assert stats["nodes_by_kind"]["function"] == 1
        assert stats["edges_by_kind"]["contains"] == 2
        assert "python" in stats["languages"]


# -------------------------------------------------------------------- finalize


class TestFinalize:
    """Tests for ``finalize``."""

    def test_finalize_returns_program_graph(self, populated_builder: ProgramGraphBuilder) -> None:
        graph = populated_builder.finalize()
        assert isinstance(graph, ProgramGraph)
        assert graph.node_count() == 3
        assert graph.edge_count() == 2

    def test_finalize_updates_timestamp(self, populated_builder: ProgramGraphBuilder) -> None:
        before = populated_builder.graph.metadata.updated_at
        graph = populated_builder.finalize()
        assert graph.metadata.updated_at >= before
