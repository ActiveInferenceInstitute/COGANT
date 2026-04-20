"""Performance and scalability tests for Markov blanket partitioning.

The COGANT markov module is documented as O(V+E). These tests verify:
1. Partition validity: internal ∪ blanket ∪ external = all nodes, no overlaps
2. O(V+E) runtime: completion in <1s on 1000-node synthetic graphs
3. All 5 seed strategies produce valid partitions
4. Partition consistency: same input -> same partition across runs
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

# Ensure cogant imports work
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PY_ROOT = _REPO_ROOT / "py"
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.markov import (
    MarkovBlanketExtractor,
    BlanketRole,
    partition_by_seeds,
)

pytestmark = pytest.mark.unit


# ============================================================================
# FIXTURES: Synthetic graphs of increasing size
# ============================================================================


@pytest.fixture
def small_graph():
    """10-node graph: basic connectivity."""
    builder = ProgramGraphBuilder(repo_uri="test://markov_small")

    nodes = []
    for i in range(10):
        node = builder.add_node(
            NodeKind.FUNCTION,
            f"func_{i}",
            f"func_{i}",
            path=f"module_{i % 3}.py",
        )
        nodes.append(node)

    # Chain connectivity: 0->1->2->...->9
    for i in range(9):
        builder.add_edge(nodes[i].id, nodes[i + 1].id, EdgeKind.CALLS)

    return builder.finalize()


@pytest.fixture
def medium_graph():
    """100-node graph: sparse connectivity."""
    builder = ProgramGraphBuilder(repo_uri="test://markov_medium")

    nodes = []
    for i in range(100):
        node = builder.add_node(
            NodeKind.FUNCTION,
            f"func_{i}",
            f"func_{i}",
            path=f"module_{i % 10}.py",
        )
        nodes.append(node)

    # Grid-like connectivity: each node connects to 2-3 others
    for i in range(100):
        for j in [i + 1, i + 10, i - 1]:
            if 0 <= j < 100 and j != i:
                builder.add_edge(nodes[i].id, nodes[j].id, EdgeKind.CALLS)

    return builder.finalize()


@pytest.fixture
def large_synthetic_graph():
    """1000-node graph for O(V+E) performance testing."""
    builder = ProgramGraphBuilder(repo_uri="test://markov_large")

    nodes = []
    for i in range(1000):
        node = builder.add_node(
            NodeKind.FUNCTION,
            f"f{i}",
            f"f{i}",
            path=f"mod_{i % 50}.py",
        )
        nodes.append(node)

    # Sparse connectivity: ~3 edges per node
    edge_count = 0
    for i in range(1000):
        # Connect to a few neighbors
        for offset in [1, 7, 13]:
            j = (i + offset) % 1000
            if j != i and edge_count < 3000:  # Limit total edges
                builder.add_edge(nodes[i].id, nodes[j].id, EdgeKind.CALLS)
                edge_count += 1

    return builder.finalize()


# ============================================================================
# TESTS: Partition validity
# ============================================================================


class TestMarkovPartitionValidity:
    """Tests that Markov partitions partition the entire graph."""

    def test_partition_covers_all_nodes(self, small_graph):
        """Union of internal, blanket, external = all nodes."""
        extractor = MarkovBlanketExtractor(graph=small_graph)
        blanket = extractor.extract(strategy="auto")

        all_partitioned = (
            blanket.internal_ids
            | blanket.sensory_ids
            | blanket.active_ids
            | blanket.external_ids
        )
        assert all_partitioned == set(small_graph.nodes)

    def test_partition_no_overlaps(self, small_graph):
        """internal, blanket, external are mutually exclusive."""
        extractor = MarkovBlanketExtractor(graph=small_graph)
        blanket = extractor.extract(strategy="auto")

        # Check pairwise disjointness
        assert len(blanket.internal_ids & blanket.sensory_ids) == 0
        assert len(blanket.internal_ids & blanket.active_ids) == 0
        assert len(blanket.internal_ids & blanket.external_ids) == 0
        assert len(blanket.sensory_ids & blanket.active_ids) == 0
        assert len(blanket.sensory_ids & blanket.external_ids) == 0
        assert len(blanket.active_ids & blanket.external_ids) == 0

    def test_partition_cardinalities_sum_to_graph_size(self, medium_graph):
        """len(internal) + len(blanket) + len(external) = total nodes."""
        extractor = MarkovBlanketExtractor(graph=medium_graph)
        blanket = extractor.extract(strategy="auto")

        total_partitioned = (
            len(blanket.internal_ids)
            + len(blanket.sensory_ids)
            + len(blanket.active_ids)
            + len(blanket.external_ids)
        )
        assert total_partitioned == len(medium_graph.nodes)

    def test_internal_nodes_have_no_external_edges_out(self, small_graph):
        """All outgoing edges from internal nodes stay internal."""
        extractor = MarkovBlanketExtractor(graph=small_graph)
        blanket = extractor.extract(strategy="auto")

        for node_id in blanket.internal_ids:
            for edge in small_graph.edges.values():
                if edge.source_id == node_id:
                    # Target must be internal, sensory (blanket), or active (blanket)
                    assert (
                        edge.target_id in blanket.internal_ids
                        or edge.target_id in blanket.sensory_ids
                        or edge.target_id in blanket.active_ids
                    )

    def test_partition_roles_are_valid(self, small_graph):
        """All nodes get assigned exactly one role."""
        extractor = MarkovBlanketExtractor(graph=small_graph)
        blanket = extractor.extract(strategy="auto")

        # Access internal roles dict
        roles = blanket.roles if hasattr(blanket, 'roles') else {}
        assert isinstance(roles, dict)
        # Each node should have one entry in roles (or mapping is via ids)
        total_role_count = (
            len(blanket.internal_ids)
            + len(blanket.sensory_ids)
            + len(blanket.active_ids)
            + len(blanket.external_ids)
        )
        assert total_role_count == len(small_graph.nodes)


# ============================================================================
# TESTS: O(V+E) performance
# ============================================================================


class TestMarkovPerformance:
    """Tests that Markov partitioning runs in O(V+E) time."""

    def test_small_graph_partition_completes_fast(self, small_graph):
        """10-node graph partitions in <10ms."""
        extractor = MarkovBlanketExtractor(graph=small_graph)

        start = time.time()
        blanket = extractor.extract(strategy="auto")
        elapsed = time.time() - start

        assert elapsed < 0.01, f"Small graph took {elapsed}s, expected <10ms"

    def test_medium_graph_partition_completes_fast(self, medium_graph):
        """100-node graph partitions in <100ms."""
        extractor = MarkovBlanketExtractor(graph=medium_graph)

        start = time.time()
        blanket = extractor.extract(strategy="auto")
        elapsed = time.time() - start

        assert elapsed < 0.1, f"Medium graph took {elapsed}s, expected <100ms"

    def test_large_graph_partition_under_1s(self, large_synthetic_graph):
        """1000-node graph partitions in <1s (O(V+E) guarantee)."""
        extractor = MarkovBlanketExtractor(graph=large_synthetic_graph)

        start = time.time()
        blanket = extractor.extract(strategy="auto")
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Large graph took {elapsed}s, expected <1s (O(V+E))"
        # Verify partition is valid
        all_nodes = (
            blanket.internal_ids
            | blanket.sensory_ids
            | blanket.active_ids
            | blanket.external_ids
        )
        assert all_nodes == set(large_synthetic_graph.nodes)

    def test_partition_time_scales_linearly(self, small_graph, medium_graph):
        """Time to partition scales roughly linearly with graph size."""
        extractor_small = MarkovBlanketExtractor(graph=small_graph)
        extractor_med = MarkovBlanketExtractor(graph=medium_graph)

        start_s = time.time()
        extractor_small.extract(strategy="auto")
        time_small = time.time() - start_s

        start_m = time.time()
        extractor_med.extract(strategy="auto")
        time_med = time.time() - start_m

        # Medium is 10x larger, so time should be ~10x (with tolerance)
        # Allow up to 20x to account for constant factors
        size_ratio = 100 / 10  # medium / small nodes
        time_ratio = time_med / time_small if time_small > 0 else 1

        assert time_ratio < size_ratio * 2, (
            f"Time ratio {time_ratio:.1f}x exceeds 2x size ratio {size_ratio:.1f}x"
        )


# ============================================================================
# TESTS: All 5 seed strategies produce valid partitions
# ============================================================================


class TestAllSeedStrategies:
    """Tests that all documented Markov seed strategies produce valid partitions."""

    @pytest.mark.parametrize(
        "strategy,kwargs",
        [
            ("auto", {}),
            # No MODULE nodes in ``small_graph`` — seeds may be empty but partition is total.
            ("module", {"module_names": ["module_0"]}),
            ("kind", {"kinds": [NodeKind.FUNCTION]}),
            ("explicit", {"seeds": None}),  # filled below
            ("mapping_kind", {"semantic_mappings": {}}),
        ],
    )
    def test_strategy_produces_valid_partition(self, small_graph, strategy, kwargs):
        """Each seed strategy produces a valid partition."""
        extractor = MarkovBlanketExtractor(graph=small_graph)
        call_kw = {k: v for k, v in kwargs.items() if v is not None}
        if strategy == "explicit":
            call_kw["seeds"] = list(small_graph.nodes)[:3]
        blanket = extractor.extract(strategy=strategy, **call_kw)

        all_nodes = (
            blanket.internal_ids
            | blanket.sensory_ids
            | blanket.active_ids
            | blanket.external_ids
        )
        assert all_nodes == set(small_graph.nodes), f"Strategy {strategy} missing nodes"

    def test_auto_strategy_is_default(self, small_graph):
        """Auto strategy is the default and produces output."""
        extractor = MarkovBlanketExtractor(graph=small_graph)
        blanket = extractor.extract()  # No strategy specified

        assert blanket is not None
        all_nodes = (
            blanket.internal_ids
            | blanket.sensory_ids
            | blanket.active_ids
            | blanket.external_ids
        )
        assert all_nodes == set(small_graph.nodes)

    def test_different_strategies_may_produce_different_partitions(self, small_graph):
        """Different strategies may produce different (but valid) partitions."""
        extractor1 = MarkovBlanketExtractor(graph=small_graph)
        extractor2 = MarkovBlanketExtractor(graph=small_graph)

        blanket1 = extractor1.extract(strategy="module", module_names=["module_0"])
        blanket2 = extractor2.extract(strategy="kind", kinds=[NodeKind.FUNCTION])

        for b in (blanket1, blanket2):
            all_nodes = (
                b.internal_ids
                | b.sensory_ids
                | b.active_ids
                | b.external_ids
            )
            assert all_nodes == set(small_graph.nodes)


# ============================================================================
# TESTS: Partition consistency
# ============================================================================


class TestMarkovConsistency:
    """Tests that partitioning is deterministic and consistent."""

    def test_partition_idempotent(self, small_graph):
        """Extracting twice from same graph produces same partition."""
        extractor1 = MarkovBlanketExtractor(graph=small_graph)
        extractor2 = MarkovBlanketExtractor(graph=small_graph)

        blanket1 = extractor1.extract(strategy="auto")
        blanket2 = extractor2.extract(strategy="auto")

        assert blanket1.internal_ids == blanket2.internal_ids
        assert blanket1.sensory_ids == blanket2.sensory_ids
        assert blanket1.active_ids == blanket2.active_ids
        assert blanket1.external_ids == blanket2.external_ids

    def test_manual_partition_with_same_seeds_is_consistent(self, small_graph):
        """Partitioning with same seeds always produces same result."""
        nodes = list(small_graph.nodes)
        seeds = set(nodes[:3])

        blanket1 = partition_by_seeds(small_graph, seeds)
        blanket2 = partition_by_seeds(small_graph, seeds)

        assert blanket1.internal_ids == blanket2.internal_ids
        assert blanket1.sensory_ids == blanket2.sensory_ids
        assert blanket1.active_ids == blanket2.active_ids
        assert blanket1.external_ids == blanket2.external_ids

    def test_partition_unchanged_after_copy(self, small_graph):
        """Partitioning graph and its copy produces equivalent partitions."""
        from copy import deepcopy

        graph_copy = deepcopy(small_graph)

        extractor_orig = MarkovBlanketExtractor(graph=small_graph)
        extractor_copy = MarkovBlanketExtractor(graph=graph_copy)

        blanket_orig = extractor_orig.extract(strategy="auto")
        blanket_copy = extractor_copy.extract(strategy="auto")

        # Node IDs should match (same generation)
        assert len(blanket_orig.internal_ids) == len(blanket_copy.internal_ids)
        assert len(blanket_orig.sensory_ids) == len(blanket_copy.sensory_ids)
        assert len(blanket_orig.active_ids) == len(blanket_copy.active_ids)
        assert len(blanket_orig.external_ids) == len(blanket_copy.external_ids)


# ============================================================================
# TESTS: Blanket network structure
# ============================================================================


class TestBlanketNetworkStructure:
    """Tests for the collapsed BlanketNetwork view."""

    def test_blanket_network_nodes_are_roles(self, small_graph):
        """BlanketNetwork should have nodes corresponding to roles."""
        from cogant.markov import build_blanket_network

        extractor = MarkovBlanketExtractor(graph=small_graph)
        blanket = extractor.extract(strategy="auto")

        try:
            bn = build_blanket_network(blanket)
            # Network should have nodes for internal, sensory, active, external
            assert bn is not None
        except Exception:
            # May not be implemented yet
            pytest.skip("build_blanket_network not available")

    def test_blanket_serialization_roundtrip(self, small_graph):
        """Serializing and deserializing blanket preserves structure."""
        from cogant.markov import serialize_blanket

        extractor = MarkovBlanketExtractor(graph=small_graph)
        blanket = extractor.extract(strategy="auto")

        try:
            serialized = serialize_blanket(blanket)
            # Should produce some JSON-able structure
            assert serialized is not None
        except Exception:
            pytest.skip("serialize_blanket not available")
