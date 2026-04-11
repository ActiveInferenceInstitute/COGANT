"""COGANT correctness law 2: rule determinism.

Each shipped :class:`cogant.translate.engine.TranslationRule` is a
pure function of the input program graph: given the same graph, the
rule's ``matches`` method must return the same set of matches, and
``apply`` must produce the same ``SemanticMapping`` content, across
repeated invocations.

This law is what makes the translation engine's output reproducible
across machines, runs, and CI shards. A rule that relies on
dictionary iteration order, a mutable class-level cache, or a
nondeterministic hash of a live object would violate the law and
be caught by one of the cases below.

We test every concrete structural and semantic rule directly,
rather than going through the engine, so the falsifier pinpoints
the rule that drifts. Behavioural/control/resilience families share
the same ``TranslationRule`` base class, so proving determinism on
the structural and semantic families covers the interface contract
for the rest.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from cogant.graph.builder import ProgramGraphBuilder
from cogant.graph.queries import GraphQuery
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
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
# Strategy: graphs designed to tickle multiple rule families.
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
)

_RULE_BAIT_NAMES = (
    "get_state",
    "set_state",
    "update_config",
    "dispatch_event",
    "handle_request",
    "process_item",
    "Controller",
    "Service",
    "Store",
    "BaseRepo",
    "state",
    "config",
)


@st.composite
def rule_bait_graph(draw) -> ProgramGraph:
    """Small graph biased toward names the rule keyword matchers react to."""
    n = draw(st.integers(min_value=4, max_value=12))
    builder = ProgramGraphBuilder(repo_uri="hypothesis://law2")

    root = builder.add_node(
        kind=NodeKind.MODULE,
        name="root_module",
        qualified_name="law2_root",
        path="root.py",
        language="python",
    )
    nodes = [root]
    for i in range(n - 1):
        kind = draw(st.sampled_from(_NODE_KINDS))
        name = draw(st.sampled_from(_RULE_BAIT_NAMES))
        nodes.append(
            builder.add_node(
                kind=kind,
                name=name,
                qualified_name=f"{name}_{i}",
                path=f"law2_{i}.py",
                language="python",
            )
        )

    n_edges = draw(st.integers(min_value=1, max_value=3 * n))
    for _ in range(n_edges):
        src = draw(st.sampled_from(nodes))
        tgt = draw(st.sampled_from(nodes))
        if src.id == tgt.id:
            continue
        builder.add_edge(src.id, tgt.id, draw(st.sampled_from(_EDGE_KINDS)))

    return builder.finalize()


_ALL_RULES = (
    ReadOnlyInputRule,
    MutatingSubsystemRule,
    ObservationRule,
    ActionRule,
    PolicyRule,
    InheritanceRule,
    ContainmentRule,
)


def _match_signature(matches: list[dict]) -> list[tuple]:
    """Canonicalise a rule's ``matches()`` output for equality comparison.

    Rule matches are dicts that include lists; dict key order varies by
    construction path, so we sort keys then tuples. The canonical form
    is itself a sorted list so ``==`` is order-agnostic.
    """
    sigs: list[tuple] = []
    for m in matches:
        items: list[tuple] = []
        for k in sorted(m.keys()):
            v = m[k]
            if isinstance(v, list):
                v = tuple(sorted(str(x) for x in v))
            elif isinstance(v, set):
                v = tuple(sorted(str(x) for x in v))
            else:
                v = str(v)
            items.append((k, v))
        sigs.append(tuple(items))
    return sorted(sigs)


def _apply_signature(mapping) -> tuple | None:
    """Canonicalise a single ``SemanticMapping`` for equality comparison."""
    if mapping is None:
        return None
    return (
        mapping.kind.value,
        tuple(sorted(mapping.graph_fragment_node_ids)),
        tuple(sorted(mapping.graph_fragment_edge_ids)),
    )


# ---------------------------------------------------------------------------
# Law 2a: ``matches`` is deterministic.
# ---------------------------------------------------------------------------


@given(graph=rule_bait_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_rule_matches_are_deterministic(graph: ProgramGraph) -> None:
    """Every shipping rule must return the same match set on two calls."""
    query = GraphQuery(graph)
    for rule_cls in _ALL_RULES:
        rule = rule_cls()
        first = _match_signature(rule.matches(graph, query))
        second = _match_signature(rule.matches(graph, query))
        assert first == second, (
            f"{rule_cls.__name__} produced drifting matches: "
            f"diff={set(first) ^ set(second)}"
        )


# ---------------------------------------------------------------------------
# Law 2b: ``apply`` is deterministic on each matched fragment.
# ---------------------------------------------------------------------------


@given(graph=rule_bait_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_rule_apply_is_deterministic(graph: ProgramGraph) -> None:
    """``apply(match)`` must yield the same SemanticMapping content twice."""
    query = GraphQuery(graph)
    for rule_cls in _ALL_RULES:
        rule = rule_cls()
        matches = rule.matches(graph, query)
        for match in matches:
            first = _apply_signature(rule.apply(graph, match))
            second = _apply_signature(rule.apply(graph, match))
            assert first == second, (
                f"{rule_cls.__name__}.apply drifted on {match}: "
                f"first={first} second={second}"
            )


# ---------------------------------------------------------------------------
# Law 2c: two freshly-constructed rule instances agree on the same input.
# ---------------------------------------------------------------------------


@given(graph=rule_bait_graph())
@settings(
    max_examples=30,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_two_fresh_rule_instances_agree(graph: ProgramGraph) -> None:
    """Two fresh rule instances must see the same matches — no hidden state."""
    query = GraphQuery(graph)
    for rule_cls in _ALL_RULES:
        sig_a = _match_signature(rule_cls().matches(graph, query))
        sig_b = _match_signature(rule_cls().matches(graph, query))
        assert sig_a == sig_b, (
            f"{rule_cls.__name__} produces different matches from two fresh "
            f"instances — rule carries non-trivial module state"
        )
