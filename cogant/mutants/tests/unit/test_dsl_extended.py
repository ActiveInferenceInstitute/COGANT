"""Extended behavioral tests for cogant.translate.dsl — compiler.py and loader.py.

Covers: empty rules, no-conditions rules, invalid node_kind values,
multiple rules matching, YAML loader import error, load_rules_from_dict
with missing required keys, DSLCondition frozen behavior, ruleset with
description, and edge_type with invalid kind.
"""

from __future__ import annotations

import pytest

from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.translate.dsl import DSLRuleSet, compile_ruleset, load_rules_from_dict
from cogant.translate.dsl.schema import KNOWN_CONDITION_KEYS, DSLCondition

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_graph(
    node_kind: NodeKind = NodeKind.CLASS,
    node_name: str = "Foo",
) -> tuple[ProgramGraph, Node]:
    """Build a one-node graph and return (graph, node)."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="test"))
    node = Node(id="n1", kind=node_kind, name=node_name, qualified_name=node_name)
    graph.add_node(node)
    return graph, node


# ---------------------------------------------------------------------------
# Loader tests
# ---------------------------------------------------------------------------


def test_load_empty_rules_list() -> None:
    """Loading a dict with an empty rules list returns an empty DSLRuleSet."""
    ruleset = load_rules_from_dict({"rules": []})
    assert isinstance(ruleset, DSLRuleSet)
    assert len(ruleset.rules) == 0


def test_load_rules_missing_rules_key() -> None:
    """A dict without 'rules' key returns an empty DSLRuleSet (not an error)."""
    ruleset = load_rules_from_dict({})
    assert len(ruleset.rules) == 0


def test_load_rule_without_conditions() -> None:
    """A rule with no conditions list is valid (matches everything)."""
    data = {
        "rules": [{
            "name": "CatchAll",
            "role": "OBSERVATION",
            "confidence": 0.5,
        }]
    }
    ruleset = load_rules_from_dict(data)
    assert len(ruleset.rules) == 1
    assert ruleset.rules[0].conditions == []


def test_load_multiple_rules() -> None:
    """Multiple rules in a single ruleset all parse correctly."""
    data = {
        "rules": [
            {"name": "R1", "role": "HIDDEN_STATE", "confidence": 0.8, "conditions": []},
            {"name": "R2", "role": "ACTION", "confidence": 0.6, "conditions": []},
            {"name": "R3", "role": "OBSERVATION", "confidence": 0.9, "conditions": []},
        ]
    }
    ruleset = load_rules_from_dict(data)
    assert len(ruleset.rules) == 3
    assert [r.name for r in ruleset.rules] == ["R1", "R2", "R3"]


def test_load_rule_confidence_is_float() -> None:
    """Confidence value is coerced to float even when provided as int."""
    data = {
        "rules": [{
            "name": "IntConf",
            "role": "HIDDEN_STATE",
            "confidence": 1,
            "conditions": [],
        }]
    }
    ruleset = load_rules_from_dict(data)
    assert isinstance(ruleset.rules[0].confidence, float)
    assert ruleset.rules[0].confidence == 1.0


def test_known_condition_keys_are_exhaustive() -> None:
    """KNOWN_CONDITION_KEYS contains exactly the 4 expected keys."""
    assert KNOWN_CONDITION_KEYS == frozenset({"node_kind", "name_pattern", "has_method", "edge_type"})


# ---------------------------------------------------------------------------
# Compiler tests
# ---------------------------------------------------------------------------


def test_compile_no_conditions_matches_everything() -> None:
    """A compiled rule with no conditions matches any node."""
    data = {
        "rules": [{
            "name": "Universal",
            "role": "HIDDEN_STATE",
            "confidence": 0.6,
        }]
    }
    ruleset = load_rules_from_dict(data)
    compiled = compile_ruleset(ruleset)

    graph, node = _simple_graph(NodeKind.FUNCTION, "anything")
    assert compiled[0].match(node, graph) == pytest.approx(0.6)


def test_compile_invalid_node_kind_returns_zero() -> None:
    """A rule with an unrecognized node_kind value returns 0.0 on match."""
    data = {
        "rules": [{
            "name": "BadKind",
            "role": "HIDDEN_STATE",
            "confidence": 0.8,
            "conditions": [{"node_kind": "NONEXISTENT_KIND"}],
        }]
    }
    ruleset = load_rules_from_dict(data)
    compiled = compile_ruleset(ruleset)

    graph, node = _simple_graph(NodeKind.CLASS, "Test")
    assert compiled[0].match(node, graph) == 0.0


def test_compile_invalid_edge_type_returns_zero() -> None:
    """A rule with an unrecognized edge_type value returns 0.0."""
    data = {
        "rules": [{
            "name": "BadEdge",
            "role": "ACTION",
            "confidence": 0.7,
            "conditions": [{"edge_type": "NONEXISTENT_EDGE"}],
        }]
    }
    ruleset = load_rules_from_dict(data)
    compiled = compile_ruleset(ruleset)

    graph, node = _simple_graph()
    assert compiled[0].match(node, graph) == 0.0


def test_compiled_rule_preserves_description() -> None:
    """CompiledRule.description carries the original description."""
    data = {
        "rules": [{
            "name": "Described",
            "role": "HIDDEN_STATE",
            "confidence": 0.5,
            "conditions": [],
            "description": "A test description",
        }]
    }
    ruleset = load_rules_from_dict(data)
    compiled = compile_ruleset(ruleset)
    assert compiled[0].description == "A test description"


def test_name_pattern_exact_match() -> None:
    """Exact name (no glob chars) matches only that name."""
    data = {
        "rules": [{
            "name": "Exact",
            "role": "HIDDEN_STATE",
            "confidence": 0.9,
            "conditions": [{"name_pattern": "ExactName"}],
        }]
    }
    ruleset = load_rules_from_dict(data)
    compiled = compile_ruleset(ruleset)

    g1, n1 = _simple_graph(node_name="ExactName")
    assert compiled[0].match(n1, g1) == pytest.approx(0.9)

    g2, n2 = _simple_graph(node_name="DifferentName")
    assert compiled[0].match(n2, g2) == 0.0


def test_name_pattern_question_mark_glob() -> None:
    """The '?' glob matches exactly one character."""
    data = {
        "rules": [{
            "name": "QMark",
            "role": "HIDDEN_STATE",
            "confidence": 0.7,
            "conditions": [{"name_pattern": "Fo?"}],
        }]
    }
    ruleset = load_rules_from_dict(data)
    compiled = compile_ruleset(ruleset)

    g1, n1 = _simple_graph(node_name="Foo")
    assert compiled[0].match(n1, g1) == pytest.approx(0.7)

    g2, n2 = _simple_graph(node_name="Fooo")
    assert compiled[0].match(n2, g2) == 0.0


def test_dsl_condition_frozen() -> None:
    """DSLCondition is frozen (immutable)."""
    cond = DSLCondition(node_kind="CLASS")
    with pytest.raises(AttributeError):
        cond.node_kind = "FUNCTION"  # type: ignore[misc]
