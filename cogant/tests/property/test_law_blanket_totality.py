"""COGANT correctness law 4: Markov blanket totality.

Every node in a program graph must be classified into *exactly one*
of the four Active-Inference roles — ``INTERNAL`` (μ), ``SENSORY``
(s), ``ACTIVE`` (a), or ``EXTERNAL`` (η) — by the
:func:`cogant.markov.blanket.partition_by_seeds` primitive. No node
may go unclassified; no node may carry two roles. This is the
formal "totality" property of the blanket partition.

The law also asserts coverage stability under seed-set perturbation:
every seed set, from empty to the full node set, yields a complete
partition. At the extremes:

* ``seeds = ∅`` → every node is EXTERNAL (no system of interest)
* ``seeds = nodes`` → every node is INTERNAL (no external environment)

with sensory/active states only appearing when the seed set is a
strict subset whose boundary touches non-seed nodes.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from cogant.graph.builder import ProgramGraphBuilder
from cogant.markov.blanket import BlanketRole, partition_by_seeds
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph

pytestmark = pytest.mark.property


# ---------------------------------------------------------------------------
# Strategy: arbitrary small program graphs — partitioning is defined for all.
# ---------------------------------------------------------------------------


_NODE_KINDS = (
    NodeKind.MODULE,
    NodeKind.CLASS,
    NodeKind.METHOD,
    NodeKind.FUNCTION,
    NodeKind.VARIABLE,
)

_EDGE_KINDS = (
    EdgeKind.CONTAINS,
    EdgeKind.CALLS,
    EdgeKind.READS,
    EdgeKind.WRITES,
    EdgeKind.DEPENDS_ON,
)


@st.composite
def program_graph_any(draw, min_nodes: int = 2, max_nodes: int = 15) -> ProgramGraph:
    """Build a small graph; partition must work on any shape we give it."""
    n = draw(st.integers(min_value=min_nodes, max_value=max_nodes))
    builder = ProgramGraphBuilder(repo_uri="hypothesis://law4")
    nodes = []
    for i in range(n):
        kind = draw(st.sampled_from(_NODE_KINDS))
        nodes.append(
            builder.add_node(
                kind=kind,
                name=f"node_{i}",
                qualified_name=f"law4_node_{i}",
                path=f"law4_{i}.py",
                language="python",
            )
        )

    n_edges = draw(st.integers(min_value=0, max_value=3 * n))
    for _ in range(n_edges):
        src = draw(st.sampled_from(nodes))
        tgt = draw(st.sampled_from(nodes))
        if src.id == tgt.id:
            continue
        builder.add_edge(src.id, tgt.id, draw(st.sampled_from(_EDGE_KINDS)))

    return builder.finalize()


def _classified_ids(blanket) -> set[str]:
    return blanket.internal_ids | blanket.sensory_ids | blanket.active_ids | blanket.external_ids


def _role_count_for(blanket, node_id: str) -> int:
    """Count how many of the four buckets this node id appears in."""
    return sum(
        1
        for bucket in (
            blanket.internal_ids,
            blanket.sensory_ids,
            blanket.active_ids,
            blanket.external_ids,
        )
        if node_id in bucket
    )


# ---------------------------------------------------------------------------
# Law 4a: every node is classified exactly once under any seed choice.
# ---------------------------------------------------------------------------


@given(
    graph=program_graph_any(),
    seed_frac=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_every_node_classified_exactly_once(graph: ProgramGraph, seed_frac: float) -> None:
    """Every node id must appear in exactly one of the four role buckets."""
    all_ids = sorted(graph.nodes.keys())
    cut = int(round(len(all_ids) * seed_frac))
    seeds = set(all_ids[:cut])

    blanket = partition_by_seeds(graph, seeds)

    classified = _classified_ids(blanket)
    assert classified == set(all_ids), (
        f"unclassified: {set(all_ids) - classified}, spurious: {classified - set(all_ids)}"
    )
    for node_id in all_ids:
        count = _role_count_for(blanket, node_id)
        assert count == 1, f"node {node_id} classified into {count} roles (expected 1)"


# ---------------------------------------------------------------------------
# Law 4b: empty seed set → everything EXTERNAL.
# ---------------------------------------------------------------------------


@given(graph=program_graph_any())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_empty_seed_set_makes_everything_external(graph: ProgramGraph) -> None:
    """With no system-of-interest seeds, every node must be EXTERNAL."""
    blanket = partition_by_seeds(graph, seeds=set())

    assert blanket.internal_ids == set()
    assert blanket.sensory_ids == set()
    assert blanket.active_ids == set()
    assert blanket.external_ids == set(graph.nodes.keys())
    for node_id in graph.nodes:
        assert blanket.role_of(node_id) == BlanketRole.EXTERNAL


# ---------------------------------------------------------------------------
# Law 4c: full seed set → everything INTERNAL (no boundary, no external).
# ---------------------------------------------------------------------------


@given(graph=program_graph_any(min_nodes=2, max_nodes=10))
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_full_seed_set_makes_everything_internal(graph: ProgramGraph) -> None:
    """When the seeds cover every node, no node has an external neighbour."""
    all_ids = set(graph.nodes.keys())
    blanket = partition_by_seeds(graph, seeds=all_ids)

    assert blanket.internal_ids == all_ids
    assert blanket.sensory_ids == set()
    assert blanket.active_ids == set()
    assert blanket.external_ids == set()
    # Stats must agree with the buckets.
    assert blanket.stats["internal_count"] == len(all_ids)
    assert blanket.stats["external_count"] == 0
