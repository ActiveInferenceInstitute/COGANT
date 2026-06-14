"""COGANT correctness law 3: role exclusivity.

The four primary Active-Inference roles — ``HIDDEN_STATE``,
``OBSERVATION``, ``ACTION``, and ``POLICY`` — are mutually exclusive
at the node level. A node in the program graph cannot simultaneously
represent *a hidden state* and *an observation* of that state, nor
can it be *an action* and *a policy that chooses that action*, and
so on. The ``TranslationEngine``'s conflict resolver is responsible
for stripping overlapping mappings after the fixpoint converges.

This law is stronger than the (HIDDEN_STATE ⊥ OBSERVATION) check
asserted in ``tests/property/test_translation_invariants.py``: we
require all ``C(4, 2) = 6`` pairs to be disjoint.

A single failing case — one node with two contradictory AI role
mappings after conflict resolution — would falsify the law.
"""

from __future__ import annotations

from itertools import combinations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind
from cogant.translate.engine import TranslationEngine
from cogant.translate.rules import (
    ActionRule,
    ContainmentRule,
    InheritanceRule,
    MutatingSubsystemRule,
    ObservationRule,
    PolicyRule,
    ReadOnlyInputRule,
)

pytestmark = pytest.mark.property


# The four primary AI roles any node may carry at most one of.
_AI_ROLES = (
    MappingKind.HIDDEN_STATE,
    MappingKind.OBSERVATION,
    MappingKind.ACTION,
    MappingKind.POLICY,
)


# ---------------------------------------------------------------------------
# Strategy: graphs with enough structural variety to trip every AI rule.
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
    EdgeKind.READS,
    EdgeKind.WRITES,
    EdgeKind.MUTATES,
    EdgeKind.CALLS,
    EdgeKind.DEPENDS_ON,
    EdgeKind.INHERITS,
    EdgeKind.OBSERVES,
)

_MIXED_NAMES = (
    "get_value",
    "set_value",
    "handle_event",
    "dispatch",
    "process_item",
    "compute",
    "policy",
    "orchestrator",
    "Controller",
    "Service",
    "Store",
    "state",
    "config",
    "observer",
)


@st.composite
def ai_bait_graph(draw) -> ProgramGraph:
    """Build a graph heavy on structural features the AI rules care about."""
    n = draw(st.integers(min_value=5, max_value=14))
    builder = ProgramGraphBuilder(repo_uri="hypothesis://law3")

    root = builder.add_node(
        kind=NodeKind.MODULE,
        name="root_module",
        qualified_name="law3_root",
        path="root.py",
        language="python",
    )
    nodes = [root]
    for i in range(n - 1):
        kind = draw(st.sampled_from(_NODE_KINDS))
        name = draw(st.sampled_from(_MIXED_NAMES))
        nodes.append(
            builder.add_node(
                kind=kind,
                name=name,
                qualified_name=f"{name}_{i}",
                path=f"law3_{i}.py",
                language="python",
            )
        )

    # Generate many edges — role conflicts only surface on non-trivial
    # graphs where multiple rules fire on the same node.
    n_edges = draw(st.integers(min_value=2, max_value=3 * n))
    for _ in range(n_edges):
        src = draw(st.sampled_from(nodes))
        tgt = draw(st.sampled_from(nodes))
        if src.id == tgt.id:
            continue
        builder.add_edge(src.id, tgt.id, draw(st.sampled_from(_EDGE_KINDS)))

    return builder.finalize()


def _make_engine() -> TranslationEngine:
    engine = TranslationEngine()
    engine.register_rule(ReadOnlyInputRule())
    engine.register_rule(MutatingSubsystemRule())
    engine.register_rule(ObservationRule())
    engine.register_rule(ActionRule())
    engine.register_rule(PolicyRule())
    engine.register_rule(InheritanceRule())
    engine.register_rule(ContainmentRule())
    return engine


def _ids_per_ai_role(mappings) -> dict[MappingKind, set[str]]:
    """Group fragment node ids by primary AI role."""
    per_role: dict[MappingKind, set[str]] = {role: set() for role in _AI_ROLES}
    for m in mappings:
        if m.kind in per_role:
            per_role[m.kind].update(m.graph_fragment_node_ids)
    return per_role


# ---------------------------------------------------------------------------
# Law 3: every pairwise AI-role intersection must be empty.
# ---------------------------------------------------------------------------


@given(graph=ai_bait_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_ai_roles_are_pairwise_disjoint(graph: ProgramGraph) -> None:
    """No node carries two distinct primary AI roles after conflict resolution."""
    mappings = _make_engine().translate(graph)
    per_role = _ids_per_ai_role(mappings)

    for role_a, role_b in combinations(_AI_ROLES, 2):
        overlap = per_role[role_a] & per_role[role_b]
        assert not overlap, f"nodes {overlap} carry both {role_a.value} and {role_b.value}"


@given(graph=ai_bait_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_no_node_has_more_than_one_ai_role(graph: ProgramGraph) -> None:
    """Each fragment node id appears in at most one AI-role bucket.

    An independent framing of the same law: we count, per node, how
    many of the four AI roles it is assigned to. The maximum must be
    ≤ 1. This catches a failure mode where three roles overlap on the
    same node but no pair exhausts the overlap, which the pairwise
    test alone could in principle miss.
    """
    mappings = _make_engine().translate(graph)
    per_role = _ids_per_ai_role(mappings)

    role_count: dict[str, int] = {}
    for _role, ids in per_role.items():
        for nid in ids:
            role_count[nid] = role_count.get(nid, 0) + 1

    offenders = {nid: c for nid, c in role_count.items() if c > 1}
    assert not offenders, f"nodes with multiple AI roles: {offenders}"


@given(graph=ai_bait_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_hidden_state_action_are_disjoint(graph: ProgramGraph) -> None:
    """HIDDEN_STATE ∩ ACTION must be empty — a dedicated regression guard.

    The HIDDEN_STATE/ACTION conflict is the one that the ``mutating``
    and ``action`` rule families have recordedly fought over, so we
    pin it as its own falsifier alongside the generic pairwise test.
    """
    mappings = _make_engine().translate(graph)
    per_role = _ids_per_ai_role(mappings)
    conflict = per_role[MappingKind.HIDDEN_STATE] & per_role[MappingKind.ACTION]
    assert not conflict, f"HIDDEN_STATE ∩ ACTION = {conflict}"
