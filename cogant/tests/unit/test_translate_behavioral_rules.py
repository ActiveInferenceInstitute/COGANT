"""Targeted unit tests for: cogant.translate.rules.behavioral.

Targets uncovered lines in ``StateMachineRule`` (the 4th rule in the
behavioral family) plus the ``apply()`` no-node guard branches that
return ``None`` for the other three rules.

Style mirrors ``test_translate_rules_behavioral.py`` — real
``ProgramGraph`` / ``Node`` / ``Edge`` objects, no mocks.
"""

from __future__ import annotations

from cogant.graph.queries import GraphQuery
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.schemas.semantic import MappingKind
from cogant.translate.rules.behavioral import (
    EventBusRule,
    OrchestratorRule,
    StateMachineRule,
    TestAssertionRule,
)

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _make_graph() -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri="test://behavioral"))


def _add_node(g: ProgramGraph, nid: str, kind: NodeKind, name: str, **kw) -> Node:
    n = Node(
        id=nid,
        kind=kind,
        name=name,
        qualified_name=kw.get("qn", name),
        **{k: v for k, v in kw.items() if k != "qn"},
    )
    g.add_node(n)
    return n


def _add_edge(g: ProgramGraph, eid: str, src: str, tgt: str, kind: EdgeKind) -> Edge:
    e = Edge(id=eid, source_id=src, target_id=tgt, kind=kind)
    g.add_edge(e)
    return e


def _run_rule(rule, graph: ProgramGraph):
    query = GraphQuery(graph)
    matches = rule.matches(graph, query)
    return [rule.apply(graph, m) for m in matches]


# --------------------------------------------------------------------------- #
# StateMachineRule — full surface
# --------------------------------------------------------------------------- #


class TestStateMachineRuleMatches:
    """Cover every branch of ``StateMachineRule.matches``."""

    def test_class_with_state_keyword_in_name_matches(self):
        """A class whose name contains 'state' triggers a match."""
        g = _make_graph()
        _add_node(g, "c1", NodeKind.CLASS, "OrderState")
        rule = StateMachineRule()
        query = GraphQuery(g)
        matches = rule.matches(g, query)
        assert len(matches) == 1
        assert matches[0]["node_id"] == "c1"

    def test_class_with_fsm_keyword_matches(self):
        g = _make_graph()
        _add_node(g, "c1", NodeKind.CLASS, "OrderFSM")
        matches = StateMachineRule().matches(g, GraphQuery(g))
        assert len(matches) == 1

    def test_class_with_transitions_keyword_matches(self):
        g = _make_graph()
        _add_node(g, "c1", NodeKind.CLASS, "MyTransitionsHandler")
        matches = StateMachineRule().matches(g, GraphQuery(g))
        assert len(matches) == 1

    def test_class_with_on_enter_method_matches_via_transition_count(self):
        """A class containing on_enter_* triggers via the transition_methods branch."""
        g = _make_graph()
        _add_node(g, "c1", NodeKind.CLASS, "Worker")
        _add_node(g, "m1", NodeKind.METHOD, "on_enter_running")
        _add_edge(g, "e1", "c1", "m1", EdgeKind.CONTAINS)
        matches = StateMachineRule().matches(g, GraphQuery(g))
        assert len(matches) == 1
        assert matches[0]["transition_count"] >= 1

    def test_class_with_on_exit_method_matches(self):
        g = _make_graph()
        _add_node(g, "c1", NodeKind.CLASS, "Worker")
        _add_node(g, "m1", NodeKind.METHOD, "on_exit_idle")
        _add_edge(g, "e1", "c1", "m1", EdgeKind.CONTAINS)
        matches = StateMachineRule().matches(g, GraphQuery(g))
        assert len(matches) == 1

    def test_class_with_state_variable_matches(self):
        """A class containing a VARIABLE whose name contains 'state'."""
        g = _make_graph()
        _add_node(g, "c1", NodeKind.CLASS, "Worker")
        _add_node(g, "v1", NodeKind.VARIABLE, "_state")
        _add_edge(g, "e1", "c1", "v1", EdgeKind.CONTAINS)
        matches = StateMachineRule().matches(g, GraphQuery(g))
        assert len(matches) == 1
        assert matches[0]["has_state_var"] is True

    def test_plain_class_does_not_match(self):
        g = _make_graph()
        _add_node(g, "c1", NodeKind.CLASS, "PlainHelper")
        _add_node(g, "m1", NodeKind.METHOD, "do_work")
        _add_edge(g, "e1", "c1", "m1", EdgeKind.CONTAINS)
        matches = StateMachineRule().matches(g, GraphQuery(g))
        assert matches == []

    def test_function_kind_is_skipped(self):
        """Only CLASS nodes are considered — FUNCTION is ignored."""
        g = _make_graph()
        _add_node(g, "f1", NodeKind.FUNCTION, "state_machine_helper")
        matches = StateMachineRule().matches(g, GraphQuery(g))
        assert matches == []


class TestStateMachineRuleApply:
    """Cover ``StateMachineRule.apply`` happy and not-found paths."""

    def test_apply_keyword_class_returns_policy_mapping(self):
        g = _make_graph()
        _add_node(g, "c1", NodeKind.CLASS, "OrderState")
        results = _run_rule(StateMachineRule(), g)
        assert len(results) == 1
        m = results[0]
        assert m is not None
        assert m.kind == MappingKind.POLICY
        # Confidence and parser_certainty match the rule docstring
        assert m.confidence_score == 0.80
        assert m.parser_certainty == 0.85
        # graph_fragment_node_ids contains the class id
        assert "c1" in m.graph_fragment_node_ids
        # Description references the class name
        assert "OrderState" in m.description
        # Provenance records source and metadata
        assert m.provenance[0].source == "static_analysis"
        assert "transition_count" in m.provenance[0].metadata
        assert "has_state_var" in m.provenance[0].metadata

    def test_apply_with_transitions_records_count(self):
        g = _make_graph()
        _add_node(g, "c1", NodeKind.CLASS, "Worker")
        for i in range(3):
            _add_node(g, f"m{i}", NodeKind.METHOD, f"on_enter_state_{i}")
            _add_edge(g, f"e{i}", "c1", f"m{i}", EdgeKind.CONTAINS)
        results = _run_rule(StateMachineRule(), g)
        assert len(results) == 1
        assert results[0].provenance[0].metadata["transition_count"] == 3

    def test_apply_returns_none_when_node_missing(self):
        """If the matched node has been removed from the graph, apply returns None."""
        g = _make_graph()
        _add_node(g, "c1", NodeKind.CLASS, "OrderState")
        rule = StateMachineRule()
        matches = rule.matches(g, GraphQuery(g))
        assert len(matches) == 1
        # Now remove the node — apply should return None
        g.remove_node("c1")
        result = rule.apply(g, matches[0])
        assert result is None


class TestStateMachineRuleProperties:
    def test_name_is_state_machine(self):
        assert StateMachineRule().name == "state_machine"

    def test_mapping_kind_is_policy(self):
        assert StateMachineRule().mapping_kind == MappingKind.POLICY


# --------------------------------------------------------------------------- #
# Other rules — apply() returns None when node has been removed
# --------------------------------------------------------------------------- #


class TestOrchestratorRuleApplyNoneGuard:
    def test_apply_returns_none_when_node_removed(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "orchestrate")
        for i in range(3):
            _add_node(g, f"t{i}", NodeKind.FUNCTION, f"step_{i}")
            _add_edge(g, f"e{i}", "fn1", f"t{i}", EdgeKind.CALLS)
        rule = OrchestratorRule()
        matches = rule.matches(g, GraphQuery(g))
        assert len(matches) == 1
        # Remove the orchestrator node
        g.remove_node("fn1")
        assert rule.apply(g, matches[0]) is None

    def test_orchestrator_apply_class_kind_description(self):
        """Class orchestrator description path is exercised when node.kind == CLASS."""
        g = _make_graph()
        _add_node(g, "c1", NodeKind.CLASS, "PipelineRunner")
        for i in range(3):
            _add_node(g, f"t{i}", NodeKind.FUNCTION, f"step_{i}")
            _add_edge(g, f"e{i}", "c1", f"t{i}", EdgeKind.CALLS)
        results = _run_rule(OrchestratorRule(), g)
        assert len(results) == 1
        assert "Class" in results[0].description


class TestTestAssertionRuleApplyNoneGuard:
    def test_apply_returns_none_when_node_removed(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "test_x")
        _add_node(g, "fn2", NodeKind.FUNCTION, "assertEqual")
        _add_edge(g, "e1", "fn1", "fn2", EdgeKind.CALLS)
        rule = TestAssertionRule()
        matches = rule.matches(g, GraphQuery(g))
        assert len(matches) == 1
        g.remove_node("fn1")
        assert rule.apply(g, matches[0]) is None


class TestEventBusRuleApplyNoneGuard:
    def test_apply_returns_none_when_node_removed(self):
        g = _make_graph()
        _add_node(g, "ev1", NodeKind.EVENT, "user_event")
        _add_node(g, "fn1", NodeKind.FUNCTION, "subscriber")
        _add_edge(g, "e1", "ev1", "fn1", EdgeKind.TRIGGERS)
        rule = EventBusRule()
        matches = rule.matches(g, GraphQuery(g))
        assert len(matches) == 1
        g.remove_node("ev1")
        assert rule.apply(g, matches[0]) is None

    def test_event_with_only_incoming_edges_still_matches(self):
        """Event with only incoming triggers (no outgoing) still matches."""
        g = _make_graph()
        _add_node(g, "ev1", NodeKind.EVENT, "lifecycle_event")
        _add_node(g, "fn1", NodeKind.FUNCTION, "publisher")
        _add_edge(g, "e1", "fn1", "ev1", EdgeKind.TRIGGERS)
        results = _run_rule(EventBusRule(), g)
        assert len(results) == 1
        # subscriber_count is computed from outgoing TRIGGERS only
        assert results[0].provenance[0].confidence == 0.75


# --------------------------------------------------------------------------- #
# Property smoke tests — name and mapping_kind on every rule
# --------------------------------------------------------------------------- #


class TestRuleNamesAndKinds:
    def test_orchestrator_name_and_kind(self):
        r = OrchestratorRule()
        assert r.name == "orchestrator"
        assert r.mapping_kind == MappingKind.ORCHESTRATION

    def test_test_assertion_name_and_kind(self):
        r = TestAssertionRule()
        assert r.name == "test_assertion"
        assert r.mapping_kind == MappingKind.CONSTRAINT

    def test_event_bus_name_and_kind(self):
        r = EventBusRule()
        assert r.name == "event_bus"
        assert r.mapping_kind == MappingKind.OBSERVATION
