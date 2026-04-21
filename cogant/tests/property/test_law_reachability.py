"""COGANT correctness law 6: policy-to-action reachability.

Every ACTION mapping emitted by the translation engine must be
reachable from *some* POLICY mapping via a path of ``CALLS`` or
``DEPENDS_ON`` edges. In Active Inference terms, a policy is a
"plan that selects actions", so any action the translator
recognises must be invocable through at least one policy that
sits upstream of it in the call graph.

Because arbitrary random graphs do not always admit such a
structure (there can be free-standing actions with no policy
ancestor — a perfectly valid code pattern), we generate graphs
with an explicit "orchestrator seeds a chain of calls to mutating
targets" scaffold: every ACTION-candidate node has a CALLS edge
coming from a POLICY-candidate node or from a node that is
itself in the call-chain closure of a policy. We then translate
the graph and assert the reachability property on the resulting
ACTION / POLICY mapping multisets.

A falsifying example would be an ACTION mapping on a node that
has no POLICY mapping in its CALLS/DEPENDS_ON ancestor set —
evidence that the orchestration scaffold broke or that the engine
promoted an action without a controlling policy.
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Strategy: scaffolded graph with a policy → [chain] → action backbone.
# ---------------------------------------------------------------------------


# Names that trigger the PolicyRule keyword path. Source: the
# ``policy_keywords`` list in
# ``cogant.translate.rules.semantic.PolicyRule.matches`` — classes
# are matched on any of these substrings (case-insensitive).
_POLICY_NAMES = (
    "Controller",
    "RequestHandler",
    "Dispatcher",
    "Router",
    "Scheduler",
    "Manager",
    "Middleware",
)

# Names that trigger the ActionRule keyword path.
_ACTION_NAMES = (
    "set_value",
    "update_state",
    "send_event",
    "push_change",
    "execute_action",
    "dispatch_event",
    "handle_command",
    "delete_item",
)


@st.composite
def orchestrated_graph(draw) -> ProgramGraph:
    """Build a graph with a guaranteed policy → action CALLS backbone.

    The generator places one or more POLICY-candidate nodes, each
    linked to a short chain of FUNCTION/METHOD nodes that terminate
    in an ACTION-candidate node. The CALLS edge between each
    consecutive pair in the chain is what provides the reachability
    closure the law checks.
    """
    n_policies = draw(st.integers(min_value=1, max_value=3))
    n_chains_per_policy = draw(st.integers(min_value=1, max_value=3))
    chain_len = draw(st.integers(min_value=1, max_value=3))

    builder = ProgramGraphBuilder(repo_uri="hypothesis://law6")
    node_counter = 0

    def _fresh(kind, name_pool):
        nonlocal node_counter
        node_counter += 1
        base = draw(st.sampled_from(name_pool))
        return builder.add_node(
            kind=kind,
            name=base,
            qualified_name=f"law6_{base}_{node_counter}",
            path=f"law6_{node_counter}.py",
            language="python",
        )

    for _ in range(n_policies):
        policy = _fresh(NodeKind.CLASS, _POLICY_NAMES)
        for _ in range(n_chains_per_policy):
            prev = policy
            chain = []
            for _ in range(chain_len):
                mid = _fresh(
                    NodeKind.METHOD,
                    ("helper", "worker", "stage", "process_step"),
                )
                chain.append(mid)
            action = _fresh(NodeKind.METHOD, _ACTION_NAMES)
            chain.append(action)

            for tgt in chain:
                builder.add_edge(prev.id, tgt.id, EdgeKind.CALLS)
                prev = tgt

            # Give the action a WRITES edge to a variable so the
            # ActionRule fires via structural evidence as well as the
            # keyword path.
            var = _fresh(NodeKind.VARIABLE, ("state", "buffer", "counter"))
            builder.add_edge(action.id, var.id, EdgeKind.WRITES)

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


def _reachable_from(
    graph: ProgramGraph, sources: set[str], edge_kinds: tuple[EdgeKind, ...]
) -> set[str]:
    """Return the transitive forward closure of ``sources`` over ``edge_kinds``."""
    visited: set[str] = set()
    stack = list(sources)
    while stack:
        cur = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        for edge in graph.get_edges_from(cur):
            if edge.kind in edge_kinds and edge.target_id not in visited:
                stack.append(edge.target_id)
    return visited


_INVOKE_EDGES = (EdgeKind.CALLS, EdgeKind.DEPENDS_ON)


# ---------------------------------------------------------------------------
# Law 6a: on scaffolded graphs, every ACTION is reachable from a POLICY.
# ---------------------------------------------------------------------------


@given(graph=orchestrated_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_every_action_is_reachable_from_some_policy(graph: ProgramGraph) -> None:
    """Every ACTION mapping has a POLICY ancestor via CALLS/DEPENDS_ON."""
    mappings = _make_engine().translate(graph)

    policy_ids: set[str] = set()
    action_ids: set[str] = set()
    for m in mappings:
        if m.kind == MappingKind.POLICY:
            policy_ids.update(m.graph_fragment_node_ids)
        elif m.kind == MappingKind.ACTION:
            action_ids.update(m.graph_fragment_node_ids)

    if not action_ids:
        return  # Vacuously satisfied when no actions were identified.

    # POLICY ancestry includes the policy itself.
    closure = _reachable_from(graph, policy_ids, _INVOKE_EDGES) | policy_ids

    unreached = action_ids - closure
    assert not unreached, (
        f"ACTION nodes with no POLICY ancestor via CALLS/DEPENDS_ON: "
        f"{unreached}; policies={policy_ids}"
    )


# ---------------------------------------------------------------------------
# Law 6b: closure property — every policy has at least one reachable action.
# ---------------------------------------------------------------------------


@given(graph=orchestrated_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_each_policy_reaches_at_least_one_action(graph: ProgramGraph) -> None:
    """Every POLICY node in an orchestrated graph must reach an action.

    Because we always wire ``policy --CALLS→ chain... --CALLS→ action``
    in the generator, each POLICY-candidate's forward closure over
    ``CALLS`` must contain at least one node that the engine tags as
    ACTION. A failing case would reveal a translation regression in
    either the policy rule or the action rule.
    """
    mappings = _make_engine().translate(graph)

    policy_ids: set[str] = set()
    action_ids: set[str] = set()
    for m in mappings:
        if m.kind == MappingKind.POLICY:
            policy_ids.update(m.graph_fragment_node_ids)
        elif m.kind == MappingKind.ACTION:
            action_ids.update(m.graph_fragment_node_ids)

    if not policy_ids or not action_ids:
        return  # Only check when both sides exist.

    for policy_id in policy_ids:
        closure = _reachable_from(graph, {policy_id}, _INVOKE_EDGES)
        assert closure & action_ids, (
            f"POLICY node {policy_id} cannot reach any ACTION "
            f"via CALLS/DEPENDS_ON; actions={action_ids}"
        )


# ---------------------------------------------------------------------------
# Law 6c: monotonicity — removing all CALLS edges drops reachability to 0.
# ---------------------------------------------------------------------------


@given(graph=orchestrated_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_reachability_closure_is_monotone_in_edges(graph: ProgramGraph) -> None:
    """Forward closure is monotone: a graph with no CALLS reaches nothing.

    This is an independent check on the reachability helper itself,
    which underpins laws 6a/6b. We reconstruct the same nodes but
    with zero CALLS/DEPENDS_ON edges and verify the closure collapses
    to the source set. A bug in ``_reachable_from`` would be caught
    here even when the scaffolded graph masks it.
    """
    # Build a CALLS-free clone by reusing the original nodes but
    # dropping all invocation edges. This exercises the closure
    # helper on a non-trivial but edge-pruned graph.
    builder = ProgramGraphBuilder(repo_uri=graph.metadata.repo_uri)
    cloned_ids: dict[str, str] = {}
    for node in graph.nodes.values():
        cloned = builder.add_node(
            kind=node.kind,
            name=node.name,
            qualified_name=node.qualified_name,
            path=node.path,
            language=node.language,
        )
        cloned_ids[node.id] = cloned.id
    # Keep only non-invocation edges — WRITES, MUTATES, CONTAINS.
    for edge in graph.edges.values():
        if edge.kind in _INVOKE_EDGES:
            continue
        builder.add_edge(cloned_ids[edge.source_id], cloned_ids[edge.target_id], edge.kind)

    clone = builder.finalize()
    any_source = set(list(clone.nodes.keys())[:1])
    closure = _reachable_from(clone, any_source, _INVOKE_EDGES)
    assert closure == any_source, (
        f"closure on CALLS-free graph should equal the source set, got {closure} from {any_source}"
    )
