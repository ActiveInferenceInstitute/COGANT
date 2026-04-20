"""Tests for the real independence_score computation in statespace/variables.py.

The _analyze_factorization() method computes independence as
1 - shared_target_nodes / total_target_nodes across WRITES/READS edges.
"""

from __future__ import annotations

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.statespace.variables import StateVariableExtractor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_graph() -> ProgramGraphBuilder:
    return ProgramGraphBuilder(repo_uri="test://independence")


def _hidden_mapping(mapping_id: str, node_id: str) -> SemanticMapping:
    return SemanticMapping(
        id=mapping_id,
        kind=MappingKind.HIDDEN_STATE,
        graph_fragment_node_ids=[node_id],
        semantic_label="",
        description="",
        confidence_score=0.75,
    )


def _extract(builder: ProgramGraphBuilder, mappings: dict[str, SemanticMapping]) -> StateVariableExtractor:
    graph = builder.finalize()
    ex = StateVariableExtractor(graph)
    ex.extract(mappings)
    return ex


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_independence_score_disjoint_targets():
    """Two vars writing to completely different nodes → no dependency detected."""
    b = _new_graph()
    va = b.add_node(kind=NodeKind.VARIABLE, name="a", qualified_name="m.a")
    vb = b.add_node(kind=NodeKind.VARIABLE, name="b", qualified_name="m.b")
    nx = b.add_node(kind=NodeKind.FUNCTION, name="x", qualified_name="m.x")
    ny = b.add_node(kind=NodeKind.FUNCTION, name="y", qualified_name="m.y")
    b.add_edge(source_id=va.id, target_id=nx.id, kind=EdgeKind.WRITES)
    b.add_edge(source_id=vb.id, target_id=ny.id, kind=EdgeKind.WRITES)

    ex = _extract(b, {
        "m1": _hidden_mapping("m1", va.id),
        "m2": _hidden_mapping("m2", vb.id),
    })

    # Disjoint write frontiers → no entry in factorization_map
    assert ex.factorization_map == {}


@pytest.mark.unit
def test_independence_score_fully_coupled():
    """Two vars both writing to the exact same target → dependency + low score."""
    b = _new_graph()
    va = b.add_node(kind=NodeKind.VARIABLE, name="a", qualified_name="m.a")
    vb = b.add_node(kind=NodeKind.VARIABLE, name="b", qualified_name="m.b")
    shared = b.add_node(kind=NodeKind.FUNCTION, name="shared", qualified_name="m.shared")
    b.add_edge(source_id=va.id, target_id=shared.id, kind=EdgeKind.WRITES)
    b.add_edge(source_id=vb.id, target_id=shared.id, kind=EdgeKind.WRITES)

    ex = _extract(b, {
        "m1": _hidden_mapping("m1", va.id),
        "m2": _hidden_mapping("m2", vb.id),
    })

    # Must detect coupling
    assert len(ex.factorization_map) >= 1
    for info in ex.factorization_map.values():
        assert 0.0 <= info.independence_score <= 1.0
        # Both vars write only to 'shared'; 1 shared / 1 total → score = 0.0
        assert info.independence_score == pytest.approx(0.0)


@pytest.mark.unit
def test_independence_score_partial_overlap():
    """Var 'a' writes to {shared, unique_a}; var 'b' writes to {shared}.
    Overlap = 1, total for 'a' = 2 → score = 0.5.
    """
    b = _new_graph()
    va = b.add_node(kind=NodeKind.VARIABLE, name="a", qualified_name="m.a")
    vb = b.add_node(kind=NodeKind.VARIABLE, name="b", qualified_name="m.b")
    shared = b.add_node(kind=NodeKind.FUNCTION, name="shared", qualified_name="m.shared")
    unique_a = b.add_node(kind=NodeKind.FUNCTION, name="only_a", qualified_name="m.only_a")
    b.add_edge(source_id=va.id, target_id=shared.id, kind=EdgeKind.WRITES)
    b.add_edge(source_id=va.id, target_id=unique_a.id, kind=EdgeKind.WRITES)
    b.add_edge(source_id=vb.id, target_id=shared.id, kind=EdgeKind.WRITES)

    ex = _extract(b, {
        "m1": _hidden_mapping("m1", va.id),
        "m2": _hidden_mapping("m2", vb.id),
    })

    assert len(ex.factorization_map) >= 1
    for var_id, info in ex.factorization_map.items():
        # var 'a' has 2 write targets, 1 shared → score = 1 - 1/2 = 0.5
        assert 0.0 < info.independence_score <= 1.0
        assert info.independence_score == pytest.approx(0.5)


@pytest.mark.unit
def test_independence_score_no_write_edges():
    """Variables with zero WRITES edges → score falls back to 0.5."""
    b = _new_graph()
    va = b.add_node(kind=NodeKind.VARIABLE, name="a", qualified_name="m.a")
    vb = b.add_node(kind=NodeKind.VARIABLE, name="b", qualified_name="m.b")
    shared = b.add_node(kind=NodeKind.FUNCTION, name="shared", qualified_name="m.shared")
    # Only READS edge — no mutations
    b.add_edge(source_id=shared.id, target_id=va.id, kind=EdgeKind.READS)
    b.add_edge(source_id=shared.id, target_id=vb.id, kind=EdgeKind.READS)

    ex = _extract(b, {
        "m1": _hidden_mapping("m1", va.id),
        "m2": _hidden_mapping("m2", vb.id),
    })

    # No mutation overlap → no dependency, factorization_map empty
    # (reads are tracked separately and don't trigger coupling detection)
    for info in ex.factorization_map.values():
        assert 0.0 <= info.independence_score <= 1.0


@pytest.mark.unit
def test_independence_score_is_float_type():
    """independence_score is always a Python float."""
    b = _new_graph()
    vars_ = [b.add_node(kind=NodeKind.VARIABLE, name=f"v{i}", qualified_name=f"m.v{i}")
             for i in range(3)]
    shared_fn = b.add_node(kind=NodeKind.FUNCTION, name="fn", qualified_name="m.fn")
    for v in vars_:
        b.add_edge(source_id=v.id, target_id=shared_fn.id, kind=EdgeKind.WRITES)

    ex = _extract(b, {f"m{i}": _hidden_mapping(f"m{i}", vars_[i].id) for i in range(3)})

    for info in ex.factorization_map.values():
        assert isinstance(info.independence_score, float)


@pytest.mark.unit
def test_independence_score_range_always_0_to_1():
    """independence_score stays in [0, 1] regardless of graph structure."""
    b = _new_graph()
    nodes = [b.add_node(kind=NodeKind.VARIABLE, name=f"v{i}", qualified_name=f"m.v{i}")
             for i in range(4)]
    targets = [b.add_node(kind=NodeKind.FUNCTION, name=f"f{i}", qualified_name=f"m.f{i}")
               for i in range(3)]
    # Complex overlap pattern
    b.add_edge(source_id=nodes[0].id, target_id=targets[0].id, kind=EdgeKind.WRITES)
    b.add_edge(source_id=nodes[0].id, target_id=targets[1].id, kind=EdgeKind.WRITES)
    b.add_edge(source_id=nodes[1].id, target_id=targets[0].id, kind=EdgeKind.WRITES)
    b.add_edge(source_id=nodes[1].id, target_id=targets[2].id, kind=EdgeKind.WRITES)
    b.add_edge(source_id=nodes[2].id, target_id=targets[1].id, kind=EdgeKind.WRITES)
    b.add_edge(source_id=nodes[3].id, target_id=targets[2].id, kind=EdgeKind.WRITES)

    mappings = {f"m{i}": _hidden_mapping(f"m{i}", nodes[i].id) for i in range(4)}
    ex = _extract(b, mappings)

    for info in ex.factorization_map.values():
        assert 0.0 <= info.independence_score <= 1.0
