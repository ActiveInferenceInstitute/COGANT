"""Tests for the YAML rule DSL compiler.

Covers loading, validation, and compiled-rule matching logic.
"""

from __future__ import annotations

import pytest

from cogant.translate.dsl import DSLRule, DSLRuleSet, load_rules_from_dict, compile_ruleset
from cogant.translate.dsl.schema import DSLCondition
from cogant.schemas.core import Node, NodeKind, EdgeKind, Edge
from cogant.schemas.graph import GraphMetadata, ProgramGraph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_graph_with_node(
    node_id: str = "n1",
    kind: NodeKind = NodeKind.CLASS,
    name: str = "UserService",
    children: list[tuple[str, NodeKind, str]] | None = None,
    outgoing_edge_kinds: list[EdgeKind] | None = None,
) -> ProgramGraph:
    """Build a minimal ProgramGraph for matcher tests."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="test"))
    node = Node(id=node_id, kind=kind, name=name, qualified_name=name)
    graph.add_node(node)

    if children:
        for child_id, child_kind, child_name in children:
            child = Node(id=child_id, kind=child_kind, name=child_name, qualified_name=child_name)
            graph.add_node(child)
            edge = Edge(
                id=f"e_{node_id}_{child_id}",
                source_id=node_id,
                target_id=child_id,
                kind=EdgeKind.CONTAINS,
            )
            graph.add_edge(edge)

    if outgoing_edge_kinds:
        for i, ek in enumerate(outgoing_edge_kinds):
            target_id = f"target_{i}"
            target = Node(id=target_id, kind=NodeKind.VARIABLE, name=f"var_{i}", qualified_name=f"var_{i}")
            graph.add_node(target)
            edge = Edge(
                id=f"e_{node_id}_{target_id}",
                source_id=node_id,
                target_id=target_id,
                kind=ek,
            )
            graph.add_edge(edge)

    return graph


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoadRulesFromDict:
    """Tests for load_rules_from_dict."""

    def test_load_rules_from_dict_minimal(self) -> None:
        """Single rule with a node_kind condition parses correctly."""
        data = {
            "rules": [
                {
                    "name": "ClassRule",
                    "role": "HIDDEN_STATE",
                    "confidence": 0.8,
                    "conditions": [{"node_kind": "CLASS"}],
                }
            ]
        }
        ruleset = load_rules_from_dict(data)
        assert len(ruleset.rules) == 1
        assert ruleset.rules[0].name == "ClassRule"

    def test_dsl_rule_has_expected_fields(self) -> None:
        """DSLRule exposes name, role, confidence, conditions, and description."""
        data = {
            "rules": [
                {
                    "name": "TestRule",
                    "role": "ACTION",
                    "confidence": 0.65,
                    "conditions": [{"node_kind": "FUNCTION"}],
                    "description": "A test rule",
                }
            ]
        }
        ruleset = load_rules_from_dict(data)
        rule = ruleset.rules[0]
        assert rule.name == "TestRule"
        assert rule.role == "ACTION"
        assert rule.confidence == pytest.approx(0.65)
        assert len(rule.conditions) == 1
        assert rule.description == "A test rule"

    def test_unknown_condition_key_raises(self) -> None:
        """A condition dict with an unrecognised key raises ValueError."""
        data = {
            "rules": [
                {
                    "name": "Bad",
                    "role": "HIDDEN_STATE",
                    "confidence": 0.5,
                    "conditions": [{"bad_key": "x"}],
                }
            ]
        }
        with pytest.raises(ValueError, match="Unknown condition key.*bad_key"):
            load_rules_from_dict(data)


class TestCompileRuleset:
    """Tests for compile_ruleset and CompiledRule.match."""

    def test_compile_ruleset_empty(self) -> None:
        """Empty ruleset compiles to empty list (no error)."""
        ruleset = DSLRuleSet(rules=[])
        compiled = compile_ruleset(ruleset)
        assert compiled == []

    def test_compiled_rule_matches_node_kind(self) -> None:
        """CompiledRule.match returns confidence when node kind matches."""
        data = {
            "rules": [
                {
                    "name": "ClassMatcher",
                    "role": "HIDDEN_STATE",
                    "confidence": 0.75,
                    "conditions": [{"node_kind": "CLASS"}],
                }
            ]
        }
        ruleset = load_rules_from_dict(data)
        compiled = compile_ruleset(ruleset)
        assert len(compiled) == 1

        graph = _make_graph_with_node(kind=NodeKind.CLASS)
        node = graph.get_node("n1")
        score = compiled[0].match(node, graph)
        assert score == pytest.approx(0.75)

    def test_compiled_rule_no_match_returns_zero(self) -> None:
        """Wrong node kind returns 0.0."""
        data = {
            "rules": [
                {
                    "name": "ClassOnly",
                    "role": "HIDDEN_STATE",
                    "confidence": 0.75,
                    "conditions": [{"node_kind": "CLASS"}],
                }
            ]
        }
        ruleset = load_rules_from_dict(data)
        compiled = compile_ruleset(ruleset)

        graph = _make_graph_with_node(kind=NodeKind.FUNCTION, name="my_func")
        node = graph.get_node("n1")
        score = compiled[0].match(node, graph)
        assert score == 0.0

    def test_name_pattern_glob(self) -> None:
        """Glob pattern '*Service' matches 'UserService' but not 'ServiceHelper'."""
        data = {
            "rules": [
                {
                    "name": "ServiceRule",
                    "role": "HIDDEN_STATE",
                    "confidence": 0.7,
                    "conditions": [{"name_pattern": "*Service"}],
                }
            ]
        }
        ruleset = load_rules_from_dict(data)
        compiled = compile_ruleset(ruleset)

        # Should match
        g1 = _make_graph_with_node(name="UserService")
        assert compiled[0].match(g1.get_node("n1"), g1) == pytest.approx(0.7)

        # Should NOT match
        g2 = _make_graph_with_node(name="ServiceHelper")
        assert compiled[0].match(g2.get_node("n1"), g2) == 0.0

    def test_has_method_condition(self) -> None:
        """has_method: update matches a class containing a method named 'update'."""
        data = {
            "rules": [
                {
                    "name": "UpdatableClass",
                    "role": "HIDDEN_STATE",
                    "confidence": 0.8,
                    "conditions": [
                        {"node_kind": "CLASS"},
                        {"has_method": "update"},
                    ],
                }
            ]
        }
        ruleset = load_rules_from_dict(data)
        compiled = compile_ruleset(ruleset)

        # Class with update method -- should match
        g_match = _make_graph_with_node(
            kind=NodeKind.CLASS,
            name="StateManager",
            children=[("m1", NodeKind.METHOD, "update"), ("m2", NodeKind.METHOD, "reset")],
        )
        assert compiled[0].match(g_match.get_node("n1"), g_match) == pytest.approx(0.8)

        # Class without update method -- no match
        g_no = _make_graph_with_node(
            kind=NodeKind.CLASS,
            name="Reader",
            children=[("m1", NodeKind.METHOD, "read")],
        )
        assert compiled[0].match(g_no.get_node("n1"), g_no) == 0.0

    def test_edge_type_condition(self) -> None:
        """edge_type: WRITES matches node with at least one outgoing WRITES edge."""
        data = {
            "rules": [
                {
                    "name": "Writer",
                    "role": "ACTION",
                    "confidence": 0.65,
                    "conditions": [{"edge_type": "WRITES"}],
                }
            ]
        }
        ruleset = load_rules_from_dict(data)
        compiled = compile_ruleset(ruleset)

        g_yes = _make_graph_with_node(outgoing_edge_kinds=[EdgeKind.WRITES])
        assert compiled[0].match(g_yes.get_node("n1"), g_yes) == pytest.approx(0.65)

        g_no = _make_graph_with_node(outgoing_edge_kinds=[EdgeKind.READS])
        assert compiled[0].match(g_no.get_node("n1"), g_no) == 0.0

    def test_multiple_conditions_all_must_match(self) -> None:
        """When a rule has multiple conditions, ALL must match for confidence > 0."""
        data = {
            "rules": [
                {
                    "name": "Combo",
                    "role": "ACTION",
                    "confidence": 0.9,
                    "conditions": [
                        {"node_kind": "CLASS"},
                        {"name_pattern": "*Service"},
                    ],
                }
            ]
        }
        ruleset = load_rules_from_dict(data)
        compiled = compile_ruleset(ruleset)

        # Both match
        g1 = _make_graph_with_node(kind=NodeKind.CLASS, name="UserService")
        assert compiled[0].match(g1.get_node("n1"), g1) == pytest.approx(0.9)

        # Kind matches but name doesn't
        g2 = _make_graph_with_node(kind=NodeKind.CLASS, name="UserController")
        assert compiled[0].match(g2.get_node("n1"), g2) == 0.0

        # Name matches but kind doesn't
        g3 = _make_graph_with_node(kind=NodeKind.FUNCTION, name="UserService")
        assert compiled[0].match(g3.get_node("n1"), g3) == 0.0
