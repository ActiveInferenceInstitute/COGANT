"""Unit tests for every concrete :class:`TranslationRule` subclass.

The pre-existing ``test_translation_rules.py`` tests operate on toy dict
structures and never instantiate the real rule classes. This module fills
that gap: every rule in ``cogant.translate.rules`` (behavioral, control,
resilience) is exercised against a deterministic, hand-built
:class:`ProgramGraph`, and we assert both the ``matches`` and ``apply``
contracts — including the mapping id prefixes that downstream
orchestration code relies on.

Each test builds only the minimal graph needed to trigger (or to
*not* trigger) the rule under test.
"""

from __future__ import annotations

import pytest

from cogant.graph.builder import ProgramGraphBuilder
from cogant.graph.queries import GraphQuery
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.semantic import ConfidenceTier, MappingKind
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


# ------------------------------------------------------------------ helpers --

def _make_builder(repo: str = "test://rule_classes") -> ProgramGraphBuilder:
    return ProgramGraphBuilder(repo_uri=repo)


def _query(builder: ProgramGraphBuilder) -> GraphQuery:
    return GraphQuery(builder.graph)


# ================================================================ behavioral =


class TestOrchestratorRule:
    """OrchestratorRule flags high-fan-out functions/classes/methods."""

    def test_matches_high_fan_out_function(self):
        b = _make_builder()
        hub = b.add_node(NodeKind.FUNCTION, "hub", "m.hub", path="m.py")
        for i in range(4):
            leaf = b.add_node(
                NodeKind.FUNCTION, f"leaf{i}", f"m.leaf{i}", path="m.py"
            )
            b.add_edge(hub.id, leaf.id, EdgeKind.CALLS)

        rule = OrchestratorRule()
        matches = rule.matches(b.graph, _query(b))

        assert len(matches) == 1
        assert matches[0]["node_id"] == hub.id
        assert matches[0]["call_count"] == 4
        assert len(matches[0]["called_node_ids"]) == 4

    def test_no_match_below_threshold(self):
        b = _make_builder()
        caller = b.add_node(NodeKind.FUNCTION, "f", "m.f", path="m.py")
        callee = b.add_node(NodeKind.FUNCTION, "g", "m.g", path="m.py")
        b.add_edge(caller.id, callee.id, EdgeKind.CALLS)

        rule = OrchestratorRule()
        assert rule.matches(b.graph, _query(b)) == []

    def test_apply_produces_orchestration_mapping(self):
        b = _make_builder()
        hub = b.add_node(NodeKind.CLASS, "Dispatcher", "m.Dispatcher", path="m.py")
        for i in range(3):
            leaf = b.add_node(NodeKind.FUNCTION, f"l{i}", f"m.l{i}", path="m.py")
            b.add_edge(hub.id, leaf.id, EdgeKind.CALLS)

        rule = OrchestratorRule()
        matches = rule.matches(b.graph, _query(b))
        mapping = rule.apply(b.graph, matches[0])

        assert mapping is not None
        assert mapping.kind == MappingKind.ORCHESTRATION
        assert mapping.id.startswith("orch_")
        assert hub.id in mapping.graph_fragment_node_ids
        assert "Orchestrator" in mapping.semantic_label
        assert mapping.confidence_score == pytest.approx(0.8)
        assert mapping.confidence_tier == ConfidenceTier.STATIC_ONLY

    def test_apply_handles_missing_node(self):
        rule = OrchestratorRule()
        b = _make_builder()
        # fabricate a match for a nonexistent node
        mapping = rule.apply(
            b.graph,
            {"node_id": "does_not_exist", "call_count": 5, "called_node_ids": []},
        )
        assert mapping is None

    def test_name_and_kind_properties(self):
        rule = OrchestratorRule()
        assert rule.name == "orchestrator"
        assert rule.mapping_kind == MappingKind.ORCHESTRATION


class TestTestAssertionRule:
    """TestAssertionRule converts test functions into constraint mappings."""

    def test_matches_test_function_with_assertions(self):
        b = _make_builder()
        test_func = b.add_node(
            NodeKind.FUNCTION, "test_add", "tests.test_add", path="tests/t.py"
        )
        helper = b.add_node(NodeKind.FUNCTION, "assert_eq", "std.assert_eq")
        b.add_edge(test_func.id, helper.id, EdgeKind.CALLS)

        rule = TestAssertionRule()
        matches = rule.matches(b.graph, _query(b))
        assert len(matches) == 1
        assert matches[0]["node_id"] == test_func.id
        assert matches[0]["assertion_count"] == 1

    def test_ignores_non_test_functions(self):
        b = _make_builder()
        regular = b.add_node(NodeKind.FUNCTION, "compute", "m.compute", path="m.py")
        inner = b.add_node(NodeKind.FUNCTION, "helper", "m.helper", path="m.py")
        b.add_edge(regular.id, inner.id, EdgeKind.CALLS)

        rule = TestAssertionRule()
        assert rule.matches(b.graph, _query(b)) == []

    def test_ignores_test_without_assertions(self):
        b = _make_builder()
        b.add_node(NodeKind.FUNCTION, "test_noop", "tests.test_noop", path="t.py")
        rule = TestAssertionRule()
        assert rule.matches(b.graph, _query(b)) == []

    def test_apply_produces_constraint_mapping(self):
        b = _make_builder()
        tf = b.add_node(NodeKind.FUNCTION, "test_x", "tests.test_x", path="t.py")
        h = b.add_node(NodeKind.FUNCTION, "assert_eq", "std.assert_eq")
        b.add_edge(tf.id, h.id, EdgeKind.CALLS)

        rule = TestAssertionRule()
        mapping = rule.apply(b.graph, rule.matches(b.graph, _query(b))[0])

        assert mapping is not None
        assert mapping.kind == MappingKind.CONSTRAINT
        assert mapping.id.startswith("const_")
        assert mapping.confidence_score == pytest.approx(0.85)
        assert rule.name == "test_assertion"

    def test_apply_missing_node_is_none(self):
        b = _make_builder()
        rule = TestAssertionRule()
        assert rule.apply(b.graph, {"node_id": "ghost", "assertion_count": 1}) is None


class TestEventBusRule:
    """EventBusRule detects EVENT nodes and maps them to OBSERVATION."""

    def test_matches_event_with_triggers(self):
        b = _make_builder()
        ev = b.add_node(NodeKind.EVENT, "UserCreated", "events.UserCreated")
        sub = b.add_node(NodeKind.FUNCTION, "handler", "m.handler")
        b.add_edge(ev.id, sub.id, EdgeKind.TRIGGERS)

        rule = EventBusRule()
        matches = rule.matches(b.graph, _query(b))
        assert len(matches) == 1
        assert matches[0]["subscriber_count"] == 1

    def test_ignores_isolated_event(self):
        b = _make_builder()
        b.add_node(NodeKind.EVENT, "Lonely", "events.Lonely")
        rule = EventBusRule()
        assert rule.matches(b.graph, _query(b)) == []

    def test_apply_produces_observation_mapping(self):
        b = _make_builder()
        ev = b.add_node(NodeKind.EVENT, "OrderPlaced", "events.OrderPlaced")
        sub = b.add_node(NodeKind.FUNCTION, "on_order", "m.on_order")
        b.add_edge(ev.id, sub.id, EdgeKind.TRIGGERS)

        rule = EventBusRule()
        mapping = rule.apply(b.graph, rule.matches(b.graph, _query(b))[0])

        assert mapping is not None
        assert mapping.kind == MappingKind.OBSERVATION
        assert mapping.id.startswith("event_")
        assert mapping.confidence_tier == ConfidenceTier.STATIC_PLUS_RUNTIME
        assert rule.name == "event_bus"


# =================================================================== control =


class TestConfigRule:
    """ConfigRule turns CONFIGURATION nodes into CONTEXT mappings."""

    def test_matches_every_config_node(self):
        b = _make_builder()
        c1 = b.add_node(NodeKind.CONFIGURATION, "settings", "cfg.settings")
        c2 = b.add_node(NodeKind.CONFIGURATION, "defaults", "cfg.defaults")
        b.add_node(NodeKind.FUNCTION, "f", "m.f")  # noise

        rule = ConfigRule()
        matches = rule.matches(b.graph, _query(b))
        assert {m["node_id"] for m in matches} == {c1.id, c2.id}

    def test_apply_produces_context_mapping(self):
        b = _make_builder()
        cfg = b.add_node(NodeKind.CONFIGURATION, "db_url", "cfg.db_url")
        rule = ConfigRule()
        mapping = rule.apply(b.graph, {"node_id": cfg.id})
        assert mapping is not None
        assert mapping.kind == MappingKind.CONTEXT
        assert mapping.id.startswith("ctx_")
        assert mapping.confidence_score == pytest.approx(0.9)
        assert rule.name == "config"


class TestFeatureFlagRule:
    """FeatureFlagRule converts FEATURE_FLAG nodes to CONTEXT mappings."""

    def test_matches_feature_flags(self):
        b = _make_builder()
        f = b.add_node(NodeKind.FEATURE_FLAG, "new_ui", "flags.new_ui")
        b.add_node(NodeKind.FUNCTION, "noise", "m.noise")

        rule = FeatureFlagRule()
        matches = rule.matches(b.graph, _query(b))
        assert [m["node_id"] for m in matches] == [f.id]

    def test_apply_produces_selector_mapping(self):
        b = _make_builder()
        flag = b.add_node(NodeKind.FEATURE_FLAG, "beta_path", "flags.beta_path")
        rule = FeatureFlagRule()
        mapping = rule.apply(b.graph, {"node_id": flag.id})
        assert mapping is not None
        assert mapping.id.startswith("fflag_")
        assert mapping.kind == MappingKind.CONTEXT
        assert rule.name == "feature_flag"


# ================================================================ resilience =


class TestRetryPatternRule:
    """RetryPatternRule keyword-scans function names."""

    @pytest.mark.parametrize(
        "fname",
        ["retry_once", "do_backoff", "CircuitBreaker", "TimeoutGuard", "fallback_fn"],
    )
    def test_matches_keyword_names(self, fname):
        b = _make_builder()
        fn = b.add_node(NodeKind.FUNCTION, fname, f"m.{fname}", path="m.py")
        rule = RetryPatternRule()
        matches = rule.matches(b.graph, _query(b))
        assert len(matches) == 1
        assert matches[0]["node_id"] == fn.id

    def test_ignores_plain_names(self):
        b = _make_builder()
        b.add_node(NodeKind.FUNCTION, "compute", "m.compute", path="m.py")
        rule = RetryPatternRule()
        assert rule.matches(b.graph, _query(b)) == []

    def test_apply_produces_policy_mapping(self):
        b = _make_builder()
        fn = b.add_node(NodeKind.METHOD, "do_retry", "m.C.do_retry", path="m.py")
        rule = RetryPatternRule()
        mapping = rule.apply(b.graph, rule.matches(b.graph, _query(b))[0])
        assert mapping is not None
        assert mapping.id.startswith("policy_")
        assert mapping.kind == MappingKind.POLICY
        assert mapping.confidence_score == pytest.approx(0.7)
        assert rule.name == "retry_pattern"


class TestErrorBoundaryRule:
    """ErrorBoundaryRule tracks CATCHES/THROWS edges."""

    def test_matches_catches_edge(self):
        b = _make_builder()
        fn = b.add_node(NodeKind.FUNCTION, "safe_div", "m.safe_div", path="m.py")
        exc = b.add_node(NodeKind.CLASS, "ZeroDivErr", "exc.ZDE", path="exc.py")
        b.add_edge(fn.id, exc.id, EdgeKind.CATCHES)

        rule = ErrorBoundaryRule()
        matches = rule.matches(b.graph, _query(b))
        assert len(matches) == 1
        assert matches[0]["catches_count"] == 1
        assert matches[0]["throws_count"] == 0
        assert exc.id in matches[0]["caught_node_ids"]

    def test_matches_throws_edge(self):
        b = _make_builder()
        fn = b.add_node(NodeKind.FUNCTION, "validate", "m.validate", path="m.py")
        exc = b.add_node(NodeKind.CLASS, "InvalidError", "exc.IE", path="exc.py")
        b.add_edge(fn.id, exc.id, EdgeKind.THROWS)

        rule = ErrorBoundaryRule()
        matches = rule.matches(b.graph, _query(b))
        assert len(matches) == 1
        assert matches[0]["throws_count"] == 1

    def test_ignores_plain_function(self):
        b = _make_builder()
        b.add_node(NodeKind.FUNCTION, "plain", "m.plain", path="m.py")
        rule = ErrorBoundaryRule()
        assert rule.matches(b.graph, _query(b)) == []

    def test_apply_produces_error_handling_mapping(self):
        b = _make_builder()
        fn = b.add_node(NodeKind.FUNCTION, "guarded", "m.guarded", path="m.py")
        exc = b.add_node(NodeKind.CLASS, "E", "exc.E", path="exc.py")
        b.add_edge(fn.id, exc.id, EdgeKind.CATCHES)

        rule = ErrorBoundaryRule()
        mapping = rule.apply(b.graph, rule.matches(b.graph, _query(b))[0])
        assert mapping is not None
        assert mapping.id.startswith("errbnd_")
        assert mapping.kind == MappingKind.ERROR_HANDLING
        assert fn.id in mapping.graph_fragment_node_ids
        assert exc.id in mapping.graph_fragment_node_ids
        assert rule.name == "error_boundary"


class TestSingletonAccessRule:
    """SingletonAccessRule requires 3+ readers from 3+ distinct modules."""

    def test_matches_cross_module_readers(self):
        b = _make_builder()
        target = b.add_node(
            NodeKind.VARIABLE, "GLOBAL", "core.GLOBAL", path="core/state.py"
        )
        for i, mod in enumerate(["a", "b", "c"]):
            reader = b.add_node(
                NodeKind.FUNCTION,
                f"read_{i}",
                f"{mod}.read_{i}",
                path=f"{mod}/mod.py",
            )
            b.add_edge(reader.id, target.id, EdgeKind.READS)

        rule = SingletonAccessRule()
        matches = rule.matches(b.graph, _query(b))
        assert len(matches) == 1
        assert matches[0]["module_count"] == 3
        assert matches[0]["reader_count"] == 3

    def test_ignores_single_module_readers(self):
        b = _make_builder()
        tgt = b.add_node(NodeKind.VARIABLE, "LOCAL", "m.LOCAL", path="m.py")
        for i in range(3):
            r = b.add_node(NodeKind.FUNCTION, f"r{i}", f"m.r{i}", path="m.py")
            b.add_edge(r.id, tgt.id, EdgeKind.READS)

        rule = SingletonAccessRule()
        # All readers live in the same module → below diversity threshold
        assert rule.matches(b.graph, _query(b)) == []

    def test_apply_produces_context_mapping(self):
        b = _make_builder()
        tgt = b.add_node(NodeKind.CLASS, "Registry", "core.Registry", path="core/r.py")
        for i, mod in enumerate(["a", "b", "c"]):
            reader = b.add_node(
                NodeKind.FUNCTION, f"f{i}", f"{mod}.f{i}", path=f"{mod}/x.py"
            )
            b.add_edge(reader.id, tgt.id, EdgeKind.READS)

        rule = SingletonAccessRule()
        mapping = rule.apply(b.graph, rule.matches(b.graph, _query(b))[0])
        assert mapping is not None
        assert mapping.id.startswith("single_")
        assert mapping.kind == MappingKind.CONTEXT
        assert rule.name == "singleton_access"


class TestCircuitBreakerRule:
    """CircuitBreakerRule needs GUARDS edge + keyword/metadata hint."""

    def test_matches_keyword_and_guards(self):
        b = _make_builder()
        cb = b.add_node(
            NodeKind.FUNCTION, "retry_guard", "m.retry_guard", path="m.py"
        )
        tgt = b.add_node(NodeKind.FUNCTION, "leaf", "m.leaf", path="m.py")
        b.add_edge(cb.id, tgt.id, EdgeKind.GUARDS)

        rule = CircuitBreakerRule()
        matches = rule.matches(b.graph, _query(b))
        assert len(matches) == 1
        assert matches[0]["keyword_match"] is True

    def test_matches_metadata_hint(self):
        b = _make_builder()
        cb = b.add_node(
            NodeKind.CLASS,
            "Watcher",
            "m.Watcher",
            path="m.py",
            metadata={"pattern": "fallback_wrapper"},
        )
        tgt = b.add_node(NodeKind.FUNCTION, "leaf", "m.leaf", path="m.py")
        b.add_edge(cb.id, tgt.id, EdgeKind.GUARDS)

        rule = CircuitBreakerRule()
        matches = rule.matches(b.graph, _query(b))
        assert len(matches) == 1
        assert matches[0]["metadata_match"] is True

    def test_no_match_without_guards_edge(self):
        b = _make_builder()
        b.add_node(NodeKind.FUNCTION, "retry_me", "m.retry_me", path="m.py")
        rule = CircuitBreakerRule()
        assert rule.matches(b.graph, _query(b)) == []

    def test_no_match_without_keyword(self):
        b = _make_builder()
        fn = b.add_node(NodeKind.FUNCTION, "plain", "m.plain", path="m.py")
        tgt = b.add_node(NodeKind.FUNCTION, "leaf", "m.leaf", path="m.py")
        b.add_edge(fn.id, tgt.id, EdgeKind.GUARDS)
        rule = CircuitBreakerRule()
        assert rule.matches(b.graph, _query(b)) == []

    def test_apply_produces_circuit_breaker_mapping(self):
        b = _make_builder()
        cb = b.add_node(NodeKind.FUNCTION, "fallback_call", "m.fallback_call", path="m.py")
        t1 = b.add_node(NodeKind.FUNCTION, "t1", "m.t1", path="m.py")
        t2 = b.add_node(NodeKind.FUNCTION, "t2", "m.t2", path="m.py")
        b.add_edge(cb.id, t1.id, EdgeKind.GUARDS)
        b.add_edge(cb.id, t2.id, EdgeKind.GUARDS)

        rule = CircuitBreakerRule()
        mapping = rule.apply(b.graph, rule.matches(b.graph, _query(b))[0])
        assert mapping is not None
        assert mapping.id.startswith("cb_")
        assert mapping.kind == MappingKind.CIRCUIT_BREAKER
        assert mapping.confidence_score == pytest.approx(0.80)
        assert t1.id in mapping.graph_fragment_node_ids
        assert t2.id in mapping.graph_fragment_node_ids
        assert rule.name == "circuit_breaker"


# ================================================================ determinism =


class TestDeterminism:
    """Same graph → same matches and same mapping ids across runs."""

    def test_orchestrator_deterministic(self):
        def _build():
            b = _make_builder("test://det")
            h = b.add_node(NodeKind.FUNCTION, "h", "m.h", path="m.py")
            for i in range(3):
                leaf = b.add_node(NodeKind.FUNCTION, f"l{i}", f"m.l{i}", path="m.py")
                b.add_edge(h.id, leaf.id, EdgeKind.CALLS)
            return b

        r = OrchestratorRule()
        a = _build()
        bb = _build()
        ma = r.apply(a.graph, r.matches(a.graph, _query(a))[0])
        mb = r.apply(bb.graph, r.matches(bb.graph, _query(bb))[0])
        assert ma is not None and mb is not None
        assert ma.id == mb.id

    def test_error_boundary_deterministic(self):
        def _build():
            b = _make_builder("test://det_err")
            fn = b.add_node(NodeKind.FUNCTION, "f", "m.f", path="m.py")
            exc = b.add_node(NodeKind.CLASS, "E", "exc.E", path="exc.py")
            b.add_edge(fn.id, exc.id, EdgeKind.CATCHES)
            return b

        r = ErrorBoundaryRule()
        a = _build()
        bb = _build()
        ma = r.apply(a.graph, r.matches(a.graph, _query(a))[0])
        mb = r.apply(bb.graph, r.matches(bb.graph, _query(bb))[0])
        assert ma is not None and mb is not None
        assert ma.id == mb.id
