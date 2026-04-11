"""Property-based tests asserting invariants of the COGANT translation pipeline.

These tests use Hypothesis to generate small-but-valid ``ProgramGraph``
instances and assert structural/numerical invariants that every
translation pass must respect, regardless of the specific node and edge
topology:

1. **No-overlap invariant** — a single node cannot simultaneously be
   assigned both ``HIDDEN_STATE`` and ``OBSERVATION`` by the
   ``TranslationEngine``. Conflict resolution must produce disjoint
   role coverage per node.

2. **Action grounding** — every node that the shipping rule set
   labels as ``ACTION`` modality must have *some* grounding signal:
   either a reachable ``POLICY`` ancestor through ``CALLS`` /
   ``DEPENDS_ON`` edges, ≥1 outgoing ``WRITES`` / ``MUTATES`` edge,
   or a name keyword that the ``ActionRule`` / ``ContainmentRule``
   recognises as an action. A node with none of these signals should
   never receive an ``ACTION`` mapping.

3. **Probability simplex** — after GNN A/B/C/D derivation, each row
   of ``A`` must sum to 1.0 (±1e-6) and the prior vector ``D`` must
   sum to 1.0 (±1e-6). This holds whenever the matrices are
   non-empty.

4. **Fixpoint termination** — for any valid graph, the
   ``TranslationEngine`` fixpoint must terminate in ≤10 iterations
   and the resulting mapping set must be stable under two extra
   iterations (idempotent convergence).

5. **Markov blanket completeness** — the ``partition_by_seeds``
   primitive must assign *every* node in the graph to exactly one of
   the four roles ``INTERNAL``, ``SENSORY``, ``ACTIVE``, ``EXTERNAL``.
   No node may be left unclassified.

Every test instantiates *real* cogant classes — no mocks, no dicts —
and uses a ``@st.composite`` graph strategy seeded with fixed
``NodeKind`` / ``EdgeKind`` values so every generated fragment is a
syntactically valid graph the translation engine can process.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from cogant.gnn.matrices import GNNMatrices
from cogant.graph.builder import ProgramGraphBuilder
from cogant.markov.blanket import BlanketRole, partition_by_seeds
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind
from cogant.statespace.compiler import StateSpaceCompiler
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

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Hypothesis strategy: generate small but syntactically valid ProgramGraphs
# ---------------------------------------------------------------------------


# Node kinds we generate. We stick to the structural kinds that the
# shipping translation rules actually pattern-match on, so the engine
# has real work to do on every generated graph.
_GEN_NODE_KINDS: tuple[NodeKind, ...] = (
    NodeKind.MODULE,
    NodeKind.CLASS,
    NodeKind.METHOD,
    NodeKind.FUNCTION,
    NodeKind.VARIABLE,
)

# Edge kinds we generate. All of these are referenced by at least one
# structural/semantic rule in ``cogant.translate.rules``.
_GEN_EDGE_KINDS: tuple[EdgeKind, ...] = (
    EdgeKind.CONTAINS,
    EdgeKind.READS,
    EdgeKind.WRITES,
    EdgeKind.MUTATES,
    EdgeKind.CALLS,
    EdgeKind.DEPENDS_ON,
    EdgeKind.INHERITS,
)

# Name pool: deliberately biased toward words the rule keyword matchers
# recognise (get/set/handle/...) so we exercise keyword-based rules too.
_GEN_NAMES: tuple[str, ...] = (
    "get_value",
    "set_value",
    "read_data",
    "write_data",
    "update_state",
    "fetch_info",
    "handle_event",
    "process_item",
    "run_loop",
    "dispatch",
    "route",
    "query_db",
    "compute",
    "helper",
    "store",
    "controller",
    "manager",
    "handler",
    "Service",
    "Store",
    "Repo",
    "AbstractBase",
    "BaseRouter",
    "value",
    "config",
    "state",
    "counter",
    "buffer",
    "event_bus",
)


@st.composite
def program_graphs(draw, min_nodes: int = 3, max_nodes: int = 20) -> ProgramGraph:
    """Build a small but well-formed ``ProgramGraph`` from random parts.

    The strategy guarantees:

    * Every node has a unique ``qualified_name`` so the identity
      resolver assigns stable, distinct IDs.
    * Every edge references two nodes that already exist in the
      builder — the underlying ``add_edge`` would silently drop dangling
      edges anyway, but we enforce the contract in the generator to
      keep example shrinking deterministic.
    * At least one ``MODULE`` exists so ``ReadOnlyInputRule`` and
      friends have potential matches on a non-trivial fraction of
      examples.
    """
    n = draw(st.integers(min_value=min_nodes, max_value=max_nodes))
    builder = ProgramGraphBuilder(repo_uri="hypothesis://prop")

    # Always seed one module so top-level rules have a candidate.
    module = builder.add_node(
        kind=NodeKind.MODULE,
        name="root_module",
        qualified_name="hypothesis_root_module",
        path="root.py",
        language="python",
    )
    nodes = [module]

    for i in range(n - 1):
        kind = draw(st.sampled_from(_GEN_NODE_KINDS))
        base_name = draw(st.sampled_from(_GEN_NAMES))
        # Unique qualified_name avoids idempotent node merging that would
        # otherwise collapse the generator's intended node count.
        qname = f"{base_name}_{i}"
        node = builder.add_node(
            kind=kind,
            name=base_name,
            qualified_name=qname,
            path=f"gen_{i}.py",
            language="python",
        )
        nodes.append(node)

    # Generate up to 2*n edges. Fewer is fine — the invariants should
    # hold on sparse graphs too.
    n_edges = draw(st.integers(min_value=0, max_value=2 * n))
    for _ in range(n_edges):
        src = draw(st.sampled_from(nodes))
        tgt = draw(st.sampled_from(nodes))
        if src.id == tgt.id:
            continue
        edge_kind = draw(st.sampled_from(_GEN_EDGE_KINDS))
        builder.add_edge(src.id, tgt.id, edge_kind)

    return builder.finalize()


def _make_engine() -> TranslationEngine:
    """Build a ``TranslationEngine`` with the shipping structural/semantic rules."""
    engine = TranslationEngine()
    engine.register_rule(ReadOnlyInputRule())
    engine.register_rule(MutatingSubsystemRule())
    engine.register_rule(ObservationRule())
    engine.register_rule(ActionRule())
    engine.register_rule(PolicyRule())
    engine.register_rule(InheritanceRule())
    engine.register_rule(ContainmentRule())
    return engine


# ---------------------------------------------------------------------------
# 1. No-overlap invariant: HIDDEN_STATE ∩ OBSERVATION == ∅
# ---------------------------------------------------------------------------


@given(graph=program_graphs())
@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_hidden_state_and_observation_are_disjoint(graph: ProgramGraph) -> None:
    """A node must never carry both HIDDEN_STATE and OBSERVATION mappings.

    The ``TranslationEngine``'s conflict resolver is supposed to strip
    overlapping mappings; this property verifies the contract from the
    outside by looking at the per-node union.
    """
    engine = _make_engine()
    mappings = engine.translate(graph)

    hidden_ids = {
        nid
        for m in mappings
        if m.kind == MappingKind.HIDDEN_STATE
        for nid in m.graph_fragment_node_ids
    }
    observation_ids = {
        nid
        for m in mappings
        if m.kind == MappingKind.OBSERVATION
        for nid in m.graph_fragment_node_ids
    }
    assert hidden_ids.isdisjoint(observation_ids), (
        f"Node(s) {hidden_ids & observation_ids} received both "
        f"HIDDEN_STATE and OBSERVATION mappings"
    )


# ---------------------------------------------------------------------------
# 2. Action grounding: every ACTION has causal grounding OR a name signal
# ---------------------------------------------------------------------------


# Keywords that ``ActionRule`` / ``ContainmentRule`` use to flag a node as
# an action by name alone. If any of these appear in a node's lowercased
# name, the rule will emit an ACTION mapping even without outgoing
# WRITES/MUTATES edges. The invariant therefore accepts "name keyword"
# as a valid grounding signal alongside structural evidence.
_ACTION_NAME_KEYWORDS: tuple[str, ...] = (
    "set",
    "update",
    "create",
    "delete",
    "send",
    "push",
    "execute",
    "run",
    "process",
    "handle",
    "dispatch",
    "encode",
    "decode",
    "dump",
    "load",
)


def _has_outgoing_mutation(graph: ProgramGraph, node_id: str) -> bool:
    """Return True if ``node_id`` has an outgoing WRITES or MUTATES edge."""
    return any(
        e.kind in (EdgeKind.WRITES, EdgeKind.MUTATES)
        for e in graph.get_edges_from(node_id)
    )


def _reachable_from_policy(
    graph: ProgramGraph, node_id: str, policy_ids: set
) -> bool:
    """Return True if ``node_id`` is reachable from any node in ``policy_ids``.

    Reachability uses ``CALLS`` and ``DEPENDS_ON`` edges exclusively,
    which matches the "invocation or dependency" relation the action
    reachability invariant cares about.
    """
    if node_id in policy_ids:
        return True
    visited: set = set()
    stack: list[str] = list(policy_ids)
    allowed = (EdgeKind.CALLS, EdgeKind.DEPENDS_ON)
    while stack:
        cur = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        for edge in graph.get_edges_from(cur):
            if edge.kind not in allowed:
                continue
            if edge.target_id == node_id:
                return True
            if edge.target_id not in visited:
                stack.append(edge.target_id)
    return False


def _has_action_keyword(graph: ProgramGraph, node_id: str) -> bool:
    """Return True if the node's name contains an action-family keyword."""
    node = graph.get_node(node_id)
    if node is None:
        return False
    name_lower = node.name.lower()
    return any(kw in name_lower for kw in _ACTION_NAME_KEYWORDS)


@given(graph=program_graphs())
@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_action_has_policy_ancestor_or_mutation_or_keyword(
    graph: ProgramGraph,
) -> None:
    """Every ACTION-mapped node must have *some* grounding signal.

    The translation rules accept three kinds of evidence for an action:

      * ≥1 outgoing WRITES / MUTATES edge (structural grounding), OR
      * Reachable from a POLICY-mapped ancestor via CALLS / DEPENDS_ON
        (behavioural grounding), OR
      * A name keyword that the ``ActionRule`` / ``ContainmentRule``
        recognises (naming grounding).

    A node with none of these signals should never receive an ACTION
    mapping. This invariant certifies that the rule set never produces
    spurious action labels from noise alone.
    """
    engine = _make_engine()
    mappings = engine.translate(graph)

    policy_ids = {
        nid
        for m in mappings
        if m.kind == MappingKind.POLICY
        for nid in m.graph_fragment_node_ids
    }
    action_ids = {
        nid
        for m in mappings
        if m.kind == MappingKind.ACTION
        for nid in m.graph_fragment_node_ids
    }

    for act_id in action_ids:
        has_mutation = _has_outgoing_mutation(graph, act_id)
        has_policy_ancestor = _reachable_from_policy(graph, act_id, policy_ids)
        has_name_signal = _has_action_keyword(graph, act_id)
        assert has_mutation or has_policy_ancestor or has_name_signal, (
            f"ACTION node {act_id} has no grounding signal — "
            f"no mutation edges, no policy ancestry, no action keyword"
        )


# ---------------------------------------------------------------------------
# 3. Probability simplex: A rows and D vector sum to 1.0
# ---------------------------------------------------------------------------


@given(graph=program_graphs(min_nodes=4, max_nodes=15))
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_gnn_matrices_lie_on_probability_simplex(graph: ProgramGraph) -> None:
    """GNN A rows and D vector must sum to 1.0 (within 1e-6).

    The ``GNNMatrices`` class normalises every row/vector at derivation
    time; this property certifies that derivation against arbitrary
    graphs. When the matrices are empty (no mappings → zero-dim),
    the invariant is vacuously true and we skip the row checks.
    """
    engine = _make_engine()
    mappings = engine.translate(graph)

    compiler = StateSpaceCompiler(graph, "prop_test")
    ss = compiler.compile({m.id: m for m in mappings})

    gnn = GNNMatrices(graph, {m.id: m for m in mappings}, ss)
    A = gnn.compute_A()
    D = gnn.compute_D()

    if A:
        for i, row in enumerate(A):
            if not row:
                continue
            row_sum = sum(row)
            assert math.isclose(row_sum, 1.0, abs_tol=1e-6), (
                f"A row {i} does not sum to 1 (sum={row_sum:.8f})"
            )

    if D:
        d_sum = sum(D)
        assert math.isclose(d_sum, 1.0, abs_tol=1e-6), (
            f"D vector does not sum to 1 (sum={d_sum:.8f})"
        )


# ---------------------------------------------------------------------------
# 4. Fixpoint termination: engine stabilises in ≤10 iterations
# ---------------------------------------------------------------------------


@given(graph=program_graphs())
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_translate_fixpoint_is_stable_and_bounded(graph: ProgramGraph) -> None:
    """The engine must terminate at fixpoint, and two extra runs must not
    change the mapping set (idempotent convergence)."""
    engine = _make_engine()
    assert engine.max_iterations == 10

    first = engine.translate(graph)
    first_ids = {m.id for m in first}

    # Examine the match log to confirm we did not hit the "max iterations
    # reached without convergence" warning path. The engine logs an
    # ``iteration_complete`` entry per pass and bails out of the loop as
    # soon as a pass produces zero new mappings. If the final pass
    # produced zero new mappings, we converged cleanly.
    log = engine.get_match_log()
    iter_events = [e for e in log if e["event_type"] == "iteration_complete"]
    assert iter_events, "engine must record at least one iteration_complete event"
    last = iter_events[-1]["detail"]
    # Detail string format: "iteration=<n> new_mappings=<k>"
    assert "new_mappings=0" in last, (
        f"engine did not converge — last iteration detail: {last}"
    )
    assert len(iter_events) <= 10, (
        f"engine ran {len(iter_events)} > 10 iterations without convergence"
    )

    # Re-running the engine on the same graph (two more passes) must
    # produce the same final mapping set. A fresh engine is used each
    # time because ``translate`` clears internal state on entry.
    second = _make_engine().translate(graph)
    third = _make_engine().translate(graph)
    assert {m.id for m in second} == first_ids
    assert {m.id for m in third} == first_ids


# ---------------------------------------------------------------------------
# 5. Markov blanket completeness: every node has exactly one role
# ---------------------------------------------------------------------------


@given(graph=program_graphs(min_nodes=3, max_nodes=15), seed_frac=st.floats(0.1, 0.9))
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_markov_blanket_partitions_every_node_exactly_once(
    graph: ProgramGraph, seed_frac: float
) -> None:
    """partition_by_seeds must yield a complete, mutually exclusive partition.

    Every node id in ``graph.nodes`` must appear in exactly one of
    ``internal_ids``, ``sensory_ids``, ``active_ids``, or
    ``external_ids``. The seeds are a deterministic prefix of the
    sorted node list so the test remains reproducible.
    """
    all_ids = sorted(graph.nodes.keys())
    if not all_ids:
        return  # vacuous

    cut = max(1, int(len(all_ids) * seed_frac))
    seeds = set(all_ids[:cut])

    blanket = partition_by_seeds(graph, seeds)

    roles = (
        blanket.internal_ids,
        blanket.sensory_ids,
        blanket.active_ids,
        blanket.external_ids,
    )

    # Mutual exclusivity: pairwise empty intersections.
    for i in range(len(roles)):
        for j in range(i + 1, len(roles)):
            assert roles[i].isdisjoint(roles[j]), (
                f"roles {i} and {j} overlap on {roles[i] & roles[j]}"
            )

    # Completeness: union equals the full node set.
    covered = set().union(*roles)
    assert covered == set(all_ids), (
        f"unclassified nodes: {set(all_ids) - covered}"
    )

    # Every node id in the roles dict agrees with the per-role sets.
    for nid in all_ids:
        role = blanket.role_of(nid)
        assert role in (
            BlanketRole.INTERNAL,
            BlanketRole.SENSORY,
            BlanketRole.ACTIVE,
            BlanketRole.EXTERNAL,
        )
        assert nid in blanket.ids_by_role(role), (
            f"node {nid} has role {role.value} but is not in the "
            f"corresponding per-role id set"
        )
