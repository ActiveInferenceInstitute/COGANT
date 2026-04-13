"""Comprehensive tests for all 5 translate rule families + engine + DSL integration.

Covers structural, semantic, behavioral, control, and resilience rules
with real ProgramGraph / Node / Edge objects. No mocks.
"""

from __future__ import annotations

import pytest

from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.schemas.semantic import MappingKind

# -- Rule imports (all 5 families) --
from cogant.translate.rules.structural import (
    ContainmentRule,
    DataPipelineRule,
    InheritanceRule,
    MutatingSubsystemRule,
    ReadOnlyInputRule,
)
from cogant.translate.rules.semantic import (
    ActionRule,
    ContextRule,
    ObservationRule,
    PolicyRule,
    PreferenceRule,
)
from cogant.translate.rules.behavioral import (
    EventBusRule,
    OrchestratorRule,
    TestAssertionRule,
)
from cogant.translate.rules.control import ConfigRule, FeatureFlagRule
from cogant.translate.rules.resilience import (
    CircuitBreakerRule,
    ErrorBoundaryRule,
    RetryPatternRule,
    SingletonAccessRule,
)

# -- Engine and DSL --
from cogant.translate.engine import TranslationEngine
from cogant.translate.dsl.compiler import compile_ruleset
from cogant.translate.dsl.loader import load_rules_from_dict
from cogant.graph.queries import GraphQuery


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _make_graph() -> ProgramGraph:
    return ProgramGraph(metadata=GraphMetadata(repo_uri="test://rules"))


def _add_node(g: ProgramGraph, nid: str, kind: NodeKind, name: str, **kw) -> Node:
    node = Node(id=nid, kind=kind, name=name, qualified_name=kw.get("qn", name), **{k: v for k, v in kw.items() if k != "qn"})
    g.add_node(node)
    return node


def _add_edge(g: ProgramGraph, eid: str, src: str, tgt: str, kind: EdgeKind) -> Edge:
    edge = Edge(id=eid, source_id=src, target_id=tgt, kind=kind)
    g.add_edge(edge)
    return edge


def _run_rule(rule, graph: ProgramGraph):
    """Return list of SemanticMapping produced by rule on graph."""
    query = GraphQuery(graph)
    matches = rule.matches(graph, query)
    mappings = []
    for m in matches:
        sm = rule.apply(graph, m)
        if sm is not None:
            mappings.append(sm)
    return mappings


# ================================================================== #
# 1. STRUCTURAL FAMILY
# ================================================================== #

class TestReadOnlyInputRule:
    """Module with READS edges and no WRITES -> observation."""

    def test_module_with_reads_only(self):
        g = _make_graph()
        _add_node(g, "mod1", NodeKind.MODULE, "data_loader")
        _add_node(g, "var1", NodeKind.VARIABLE, "source")
        _add_edge(g, "e1", "mod1", "var1", EdgeKind.READS)

        mappings = _run_rule(ReadOnlyInputRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.OBSERVATION
        assert mappings[0].confidence_score >= 0.7

    def test_module_with_writes_does_not_match(self):
        g = _make_graph()
        _add_node(g, "mod1", NodeKind.MODULE, "writer")
        _add_node(g, "var1", NodeKind.VARIABLE, "target")
        _add_edge(g, "e1", "mod1", "var1", EdgeKind.WRITES)

        mappings = _run_rule(ReadOnlyInputRule(), g)
        assert len(mappings) == 0


class TestInheritanceRule:
    """Class with INHERITS edge -> policy or hidden_state."""

    def test_abstract_base_maps_to_policy(self):
        g = _make_graph()
        _add_node(g, "cls1", NodeKind.CLASS, "AbstractAgent")
        _add_node(g, "cls2", NodeKind.CLASS, "BaseClass")
        _add_edge(g, "e1", "cls1", "cls2", EdgeKind.INHERITS)

        mappings = _run_rule(InheritanceRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.POLICY
        assert mappings[0].confidence_score >= 0.7

    def test_handler_base_maps_to_policy(self):
        g = _make_graph()
        _add_node(g, "child", NodeKind.CLASS, "MyChild")
        _add_node(g, "base", NodeKind.CLASS, "RequestHandler")
        _add_edge(g, "e1", "child", "base", EdgeKind.INHERITS)

        mappings = _run_rule(InheritanceRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.POLICY


class TestMutatingSubsystemRule:
    """Class with WRITES/MUTATES edge -> hidden_state."""

    def test_class_with_writes_edge(self):
        g = _make_graph()
        _add_node(g, "cls1", NodeKind.CLASS, "StateHolder")
        _add_node(g, "var1", NodeKind.VARIABLE, "counter")
        _add_edge(g, "e1", "cls1", "var1", EdgeKind.WRITES)

        mappings = _run_rule(MutatingSubsystemRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.HIDDEN_STATE
        assert mappings[0].confidence_score >= 0.75


class TestDataPipelineRule:
    """Function with READS from A and WRITES to B (A != B) -> data_flow."""

    def test_transform_function(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "transform_data")
        _add_node(g, "src", NodeKind.VARIABLE, "raw_input")
        _add_node(g, "dst", NodeKind.VARIABLE, "processed_output")
        _add_edge(g, "e1", "fn1", "src", EdgeKind.READS)
        _add_edge(g, "e2", "fn1", "dst", EdgeKind.WRITES)

        mappings = _run_rule(DataPipelineRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.DATA_FLOW
        assert mappings[0].confidence_score >= 0.75


# ================================================================== #
# 2. SEMANTIC FAMILY
# ================================================================== #

class TestObservationRule:
    """Getter / read-only function -> observation."""

    def test_keyword_match_get_status(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "get_status")

        mappings = _run_rule(ObservationRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.OBSERVATION
        assert mappings[0].confidence_score >= 0.85  # keyword band

    def test_read_only_pattern_no_keyword(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "compute_hash")
        _add_node(g, "var1", NodeKind.VARIABLE, "data")
        _add_edge(g, "e1", "fn1", "var1", EdgeKind.READS)

        mappings = _run_rule(ObservationRule(), g)
        assert len(mappings) == 1
        assert mappings[0].confidence_score >= 0.7  # fallback band


class TestActionRule:
    """Setter / mutator function -> action."""

    def test_keyword_match_update(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "update_state")

        mappings = _run_rule(ActionRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.ACTION
        assert mappings[0].confidence_score >= 0.8

    def test_writes_edge_fallback(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "apply_changes")
        _add_node(g, "var1", NodeKind.VARIABLE, "buffer")
        _add_edge(g, "e1", "fn1", "var1", EdgeKind.WRITES)

        mappings = _run_rule(ActionRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.ACTION


class TestPolicyRule:
    """Controller / handler class -> policy."""

    def test_handler_class(self):
        g = _make_graph()
        _add_node(g, "cls1", NodeKind.CLASS, "RequestHandler")

        mappings = _run_rule(PolicyRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.POLICY
        assert mappings[0].confidence_score >= 0.8

    def test_dispatch_function(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "dispatch_event")

        mappings = _run_rule(PolicyRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.POLICY


class TestPreferenceRule:
    """Validator / test function -> constraint."""

    def test_validate_function(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "validate_input")

        mappings = _run_rule(PreferenceRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.CONSTRAINT
        assert mappings[0].confidence_score >= 0.85

    def test_checker_class(self):
        g = _make_graph()
        _add_node(g, "cls1", NodeKind.CLASS, "SchemaChecker")

        mappings = _run_rule(PreferenceRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.CONSTRAINT


class TestContextRule:
    """Config / settings class -> context."""

    def test_settings_class(self):
        g = _make_graph()
        _add_node(g, "cls1", NodeKind.CLASS, "AppSettings")

        mappings = _run_rule(ContextRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.CONTEXT
        assert mappings[0].confidence_score >= 0.8


# ================================================================== #
# 3. BEHAVIORAL FAMILY
# ================================================================== #

class TestOrchestratorRule:
    """Function with 3+ CALLS edges -> orchestration."""

    def test_high_fanout_function(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "run_pipeline")
        for i in range(4):
            _add_node(g, f"target_{i}", NodeKind.FUNCTION, f"step_{i}")
            _add_edge(g, f"e_{i}", "fn1", f"target_{i}", EdgeKind.CALLS)

        mappings = _run_rule(OrchestratorRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.ORCHESTRATION
        assert mappings[0].confidence_score >= 0.8

    def test_low_fanout_does_not_match(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "simple_call")
        _add_node(g, "fn2", NodeKind.FUNCTION, "helper")
        _add_edge(g, "e1", "fn1", "fn2", EdgeKind.CALLS)

        mappings = _run_rule(OrchestratorRule(), g)
        assert len(mappings) == 0


class TestTestAssertionRule:
    """Test function with CALLS edges -> constraint."""

    def test_test_function_with_assertions(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "test_addition")
        _add_node(g, "fn2", NodeKind.FUNCTION, "assertEqual")
        _add_edge(g, "e1", "fn1", "fn2", EdgeKind.CALLS)

        mappings = _run_rule(TestAssertionRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.CONSTRAINT
        assert mappings[0].confidence_score >= 0.85


class TestEventBusRule:
    """EVENT node with edges -> observation."""

    def test_event_with_triggers(self):
        g = _make_graph()
        _add_node(g, "ev1", NodeKind.EVENT, "user_created")
        _add_node(g, "fn1", NodeKind.FUNCTION, "notify_admin")
        _add_edge(g, "e1", "ev1", "fn1", EdgeKind.TRIGGERS)

        mappings = _run_rule(EventBusRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.OBSERVATION
        assert mappings[0].confidence_score >= 0.75


# ================================================================== #
# 4. CONTROL FAMILY
# ================================================================== #

class TestConfigRule:
    """CONFIGURATION node -> context with high confidence."""

    def test_config_node(self):
        g = _make_graph()
        _add_node(g, "cfg1", NodeKind.CONFIGURATION, "database_config")

        mappings = _run_rule(ConfigRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.CONTEXT
        assert mappings[0].confidence_score >= 0.9


class TestFeatureFlagRule:
    """FEATURE_FLAG node -> context."""

    def test_feature_flag_node(self):
        g = _make_graph()
        _add_node(g, "ff1", NodeKind.FEATURE_FLAG, "dark_mode_enabled")

        mappings = _run_rule(FeatureFlagRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.CONTEXT
        assert mappings[0].confidence_score >= 0.85


# ================================================================== #
# 5. RESILIENCE FAMILY
# ================================================================== #

class TestRetryPatternRule:
    """Function with retry/backoff keyword -> policy."""

    def test_retry_function(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "retry_with_backoff")

        mappings = _run_rule(RetryPatternRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.POLICY
        assert mappings[0].confidence_score >= 0.7


class TestErrorBoundaryRule:
    """Function with CATCHES/THROWS edges -> error_handling."""

    def test_catches_edge(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "safe_parse")
        _add_node(g, "exc1", NodeKind.CLASS, "ValueError")
        _add_edge(g, "e1", "fn1", "exc1", EdgeKind.CATCHES)

        mappings = _run_rule(ErrorBoundaryRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.ERROR_HANDLING
        assert mappings[0].confidence_score >= 0.7

    def test_throws_edge(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.METHOD, "validate")
        _add_node(g, "exc1", NodeKind.CLASS, "ValidationError")
        _add_edge(g, "e1", "fn1", "exc1", EdgeKind.THROWS)

        mappings = _run_rule(ErrorBoundaryRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.ERROR_HANDLING


class TestCircuitBreakerRule:
    """Function with GUARDS edge + retry keyword -> circuit_breaker."""

    def test_guards_plus_keyword(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "retry_with_circuit")
        _add_node(g, "fn2", NodeKind.FUNCTION, "external_call")
        _add_edge(g, "e1", "fn1", "fn2", EdgeKind.GUARDS)

        mappings = _run_rule(CircuitBreakerRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.CIRCUIT_BREAKER
        assert mappings[0].confidence_score >= 0.8

    def test_guards_without_keyword_no_match(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "check_health")
        _add_node(g, "fn2", NodeKind.FUNCTION, "api_call")
        _add_edge(g, "e1", "fn1", "fn2", EdgeKind.GUARDS)

        mappings = _run_rule(CircuitBreakerRule(), g)
        assert len(mappings) == 0


class TestSingletonAccessRule:
    """Variable read by 3+ modules from 3+ paths -> context."""

    def test_widely_read_variable(self):
        g = _make_graph()
        _add_node(g, "var1", NodeKind.VARIABLE, "GLOBAL_CONFIG")
        for i in range(4):
            nid = f"reader_{i}"
            _add_node(g, nid, NodeKind.FUNCTION, f"use_config_{i}", path=f"pkg{i}/mod.py")
            _add_edge(g, f"e_{i}", nid, "var1", EdgeKind.READS)

        mappings = _run_rule(SingletonAccessRule(), g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.CONTEXT
        assert mappings[0].confidence_score >= 0.65


# ================================================================== #
# 6. TRANSLATION ENGINE — full pipeline
# ================================================================== #

class TestTranslationEngine:
    """Engine with real rules on a synthetic graph."""

    def test_engine_produces_mappings_with_correct_structure(self):
        g = _make_graph()
        # observation function
        _add_node(g, "fn_obs", NodeKind.FUNCTION, "get_temperature")
        # action function
        _add_node(g, "fn_act", NodeKind.FUNCTION, "set_temperature")
        # config node
        _add_node(g, "cfg", NodeKind.CONFIGURATION, "thermostat_config")

        engine = TranslationEngine()
        engine.register_rule(ObservationRule())
        engine.register_rule(ActionRule())
        engine.register_rule(ConfigRule())

        mappings = engine.translate(g)
        assert len(mappings) >= 1

        for m in mappings:
            assert m.id is not None
            assert m.kind is not None
            assert m.confidence_score > 0
            assert len(m.graph_fragment_node_ids) >= 1

    def test_rule_filter_restricts_applied_rules(self):
        g = _make_graph()
        _add_node(g, "fn1", NodeKind.FUNCTION, "get_data")
        _add_node(g, "fn2", NodeKind.FUNCTION, "update_data")

        engine = TranslationEngine()
        engine.register_rule(ObservationRule())
        engine.register_rule(ActionRule())

        mappings = engine.translate(g, rule_filter=["observation"])
        kinds = {m.kind for m in mappings}
        assert MappingKind.ACTION not in kinds


# ================================================================== #
# 7. RULE COMPOSITION — conflict resolution
# ================================================================== #

class TestRuleComposition:
    """Two rules matching same node; higher confidence wins."""

    def test_higher_confidence_wins_conflict(self):
        g = _make_graph()
        # "dispatch_event" triggers both PolicyRule (0.80) and ActionRule (0.80)
        # plus ObservationRule won't fire (no observation keyword / read-only)
        # We set up a node that both action and policy match
        _add_node(g, "fn1", NodeKind.FUNCTION, "handle_request")

        engine = TranslationEngine()
        engine.register_rule(PolicyRule())
        engine.register_rule(ActionRule())

        mappings = engine.translate(g)
        # After conflict resolution only one mapping should survive
        node_mappings = [m for m in mappings if "fn1" in m.graph_fragment_node_ids]
        assert len(node_mappings) == 1


# ================================================================== #
# 8. EDGE CASES
# ================================================================== #

class TestEdgeCases:
    """Empty graph, isolated nodes, MODULE-only graph."""

    def test_empty_graph_yields_no_mappings(self):
        g = _make_graph()
        engine = TranslationEngine()
        engine.register_rule(ObservationRule())
        engine.register_rule(ActionRule())
        engine.register_rule(ConfigRule())

        mappings = engine.translate(g)
        assert len(mappings) == 0

    def test_isolated_nodes_no_structural_mappings(self):
        g = _make_graph()
        _add_node(g, "n1", NodeKind.VARIABLE, "x")
        _add_node(g, "n2", NodeKind.VARIABLE, "y")
        # No edges at all

        engine = TranslationEngine()
        engine.register_rule(ReadOnlyInputRule())
        engine.register_rule(MutatingSubsystemRule())
        engine.register_rule(DataPipelineRule())
        engine.register_rule(InheritanceRule())

        mappings = engine.translate(g)
        assert len(mappings) == 0

    def test_module_only_graph_yields_module_roles(self):
        g = _make_graph()
        _add_node(g, "mod1", NodeKind.MODULE, "reader_module")
        _add_node(g, "var1", NodeKind.VARIABLE, "external_source")
        _add_edge(g, "e1", "mod1", "var1", EdgeKind.READS)

        engine = TranslationEngine()
        engine.register_rule(ReadOnlyInputRule())

        mappings = engine.translate(g)
        assert len(mappings) == 1
        assert mappings[0].kind == MappingKind.OBSERVATION


# ================================================================== #
# 9. DSL INTEGRATION
# ================================================================== #

class TestDSLIntegration:
    """Define a YAML-like rule via dict, compile, and run alongside Python rules."""

    def test_dsl_rule_fires_on_matching_node(self):
        dsl_data = {
            "rules": [
                {
                    "name": "state_machine_class",
                    "role": "HIDDEN_STATE",
                    "confidence": 0.82,
                    "description": "Classes with 'update' method are state machines",
                    "conditions": [
                        {"node_kind": "CLASS"},
                        {"has_method": "update"},
                    ],
                }
            ]
        }
        ruleset = load_rules_from_dict(dsl_data)
        compiled = compile_ruleset(ruleset)
        assert len(compiled) == 1

        g = _make_graph()
        _add_node(g, "cls1", NodeKind.CLASS, "StateMachine")
        _add_node(g, "m1", NodeKind.METHOD, "update")
        _add_edge(g, "e1", "cls1", "m1", EdgeKind.CONTAINS)

        score = compiled[0].match(g.get_node("cls1"), g)
        assert score == pytest.approx(0.82)

    def test_dsl_rule_does_not_fire_on_wrong_kind(self):
        dsl_data = {
            "rules": [
                {
                    "name": "observer_func",
                    "role": "OBSERVATION",
                    "confidence": 0.75,
                    "conditions": [
                        {"node_kind": "FUNCTION"},
                        {"name_pattern": "get_*"},
                    ],
                }
            ]
        }
        ruleset = load_rules_from_dict(dsl_data)
        compiled = compile_ruleset(ruleset)

        g = _make_graph()
        _add_node(g, "cls1", NodeKind.CLASS, "get_handler")

        score = compiled[0].match(g.get_node("cls1"), g)
        assert score == 0.0  # CLASS != FUNCTION

    def test_dsl_and_python_rules_both_fire(self):
        """DSL rule and Python rule can both produce mappings on the same graph."""
        dsl_data = {
            "rules": [
                {
                    "name": "custom_action_detector",
                    "role": "ACTION",
                    "confidence": 0.78,
                    "conditions": [
                        {"node_kind": "METHOD"},
                        {"edge_type": "writes"},
                    ],
                }
            ]
        }
        ruleset = load_rules_from_dict(dsl_data)
        compiled = compile_ruleset(ruleset)

        g = _make_graph()
        _add_node(g, "cls1", NodeKind.CLASS, "Worker")
        _add_node(g, "m1", NodeKind.METHOD, "do_work")
        _add_node(g, "var1", NodeKind.VARIABLE, "output")
        _add_edge(g, "e1", "cls1", "m1", EdgeKind.CONTAINS)
        _add_edge(g, "e2", "m1", "var1", EdgeKind.WRITES)

        # DSL fires on method node
        dsl_score = compiled[0].match(g.get_node("m1"), g)
        assert dsl_score == pytest.approx(0.78)

        # Python ActionRule fires on same method (keyword or writes edge)
        python_mappings = _run_rule(ActionRule(), g)
        assert len(python_mappings) >= 1
        assert python_mappings[0].kind == MappingKind.ACTION


# ================================================================== #
# 10. EXPLAIN API
# ================================================================== #

class TestExplainAPI:
    """TranslationRule.explain returns RuleExplanation."""

    def test_observation_explain_fires(self):
        g = _make_graph()
        node = _add_node(g, "fn1", NodeKind.FUNCTION, "get_sensor_data")
        query = GraphQuery(g)

        explanation = ObservationRule().explain(node, g, query)
        assert explanation.fired is True
        assert explanation.rule_name == "observation"
        assert explanation.mapping_kind == MappingKind.OBSERVATION.value

    def test_mutating_subsystem_explain_not_fired(self):
        g = _make_graph()
        node = _add_node(g, "fn1", NodeKind.FUNCTION, "helper")
        query = GraphQuery(g)

        explanation = MutatingSubsystemRule().explain(node, g, query)
        assert explanation.fired is False
