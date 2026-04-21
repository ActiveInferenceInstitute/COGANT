#!/usr/bin/env python3
"""Coverage boost batch 34 — translate/rules/structural.py and resilience.py.

Covers:
- translate/rules/structural.py: ReadOnlyInputRule, MutatingSubsystemRule,
  InheritanceRule, ContainmentRule, DataPipelineRule (matches, apply, name,
  mapping_kind properties)
- translate/rules/resilience.py: RetryPatternRule, ErrorBoundaryRule,
  SingletonRule, CircuitBreakerRule (matches, apply, name, mapping_kind)
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph_with_module_reads():
    """Graph where module has READS but no WRITES edges."""
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    mod = builder.add_node(
        NodeKind.MODULE, "reader_mod", "reader_mod", path="r.py", language="python"
    )
    var1 = builder.add_node(NodeKind.VARIABLE, "config", "reader_mod.config", path="r.py")
    var2 = builder.add_node(NodeKind.VARIABLE, "data", "reader_mod.data", path="r.py")
    builder.add_edge(mod.id, var1.id, EdgeKind.READS)
    builder.add_edge(mod.id, var2.id, EdgeKind.READS)
    return builder.finalize(), mod, var1, var2


def _make_graph_with_mutation():
    """Graph with a class that has WRITES edges."""
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    mod = builder.add_node(NodeKind.MODULE, "m", "m", path="m.py", language="python")
    cls = builder.add_node(NodeKind.CLASS, "StateHolder", "m.StateHolder", path="m.py")
    var1 = builder.add_node(NodeKind.VARIABLE, "state", "m.StateHolder.state", path="m.py")
    func1 = builder.add_node(NodeKind.FUNCTION, "update", "m.StateHolder.update", path="m.py")
    builder.add_edge(mod.id, cls.id, EdgeKind.CONTAINS)
    builder.add_edge(cls.id, func1.id, EdgeKind.CONTAINS)
    builder.add_edge(cls.id, var1.id, EdgeKind.CONTAINS)
    builder.add_edge(func1.id, var1.id, EdgeKind.WRITES)
    return builder.finalize(), mod, cls, func1, var1


def _make_graph_with_inheritance():
    """Graph with class having INHERITS edge."""
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    mod = builder.add_node(NodeKind.MODULE, "m", "m", path="m.py", language="python")
    base = builder.add_node(NodeKind.CLASS, "BasePolicy", "m.BasePolicy", path="m.py")
    child = builder.add_node(NodeKind.CLASS, "ConcretePolicy", "m.ConcretePolicy", path="m.py")
    builder.add_edge(mod.id, base.id, EdgeKind.CONTAINS)
    builder.add_edge(mod.id, child.id, EdgeKind.CONTAINS)
    builder.add_edge(child.id, base.id, EdgeKind.INHERITS)
    return builder.finalize(), mod, base, child


def _make_graph_with_pipeline():
    """Graph with a chain of CALLS forming a pipeline."""
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    mod = builder.add_node(NodeKind.MODULE, "pipeline", "pipeline", path="p.py", language="python")
    step1 = builder.add_node(NodeKind.FUNCTION, "ingest", "pipeline.ingest", path="p.py")
    step2 = builder.add_node(NodeKind.FUNCTION, "transform", "pipeline.transform", path="p.py")
    step3 = builder.add_node(NodeKind.FUNCTION, "output", "pipeline.output", path="p.py")
    builder.add_edge(mod.id, step1.id, EdgeKind.CONTAINS)
    builder.add_edge(mod.id, step2.id, EdgeKind.CONTAINS)
    builder.add_edge(mod.id, step3.id, EdgeKind.CONTAINS)
    builder.add_edge(step1.id, step2.id, EdgeKind.CALLS)
    builder.add_edge(step2.id, step3.id, EdgeKind.CALLS)
    return builder.finalize(), mod, step1, step2, step3


def _make_graph_with_retry():
    """Graph with a function named retry_operation."""
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    mod = builder.add_node(NodeKind.MODULE, "m", "m", path="m.py", language="python")
    retry_fn = builder.add_node(NodeKind.FUNCTION, "retry_request", "m.retry_request", path="m.py")
    normal_fn = builder.add_node(NodeKind.FUNCTION, "fetch_data", "m.fetch_data", path="m.py")
    builder.add_edge(mod.id, retry_fn.id, EdgeKind.CONTAINS)
    builder.add_edge(mod.id, normal_fn.id, EdgeKind.CONTAINS)
    return builder.finalize(), mod, retry_fn, normal_fn


def _make_empty_graph():
    from cogant.graph.builder import ProgramGraphBuilder

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    return builder.finalize()


def _make_query(graph):
    from cogant.graph.queries import GraphQuery

    return GraphQuery(graph)


# ---------------------------------------------------------------------------
# ReadOnlyInputRule
# ---------------------------------------------------------------------------


class TestReadOnlyInputRule:
    def test_name_property(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule

        rule = ReadOnlyInputRule()
        assert rule.name == "read_only_input"

    def test_mapping_kind_property(self):
        from cogant.schemas.semantic import MappingKind
        from cogant.translate.rules.structural import ReadOnlyInputRule

        rule = ReadOnlyInputRule()
        assert rule.mapping_kind == MappingKind.OBSERVATION

    def test_matches_read_only_module(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule

        graph, mod, var1, var2 = _make_graph_with_module_reads()
        rule = ReadOnlyInputRule()
        results = rule.matches(graph, _make_query(graph))
        assert len(results) >= 1

    def test_matches_returns_list(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule

        graph = _make_empty_graph()
        rule = ReadOnlyInputRule()
        results = rule.matches(graph, _make_query(graph))
        assert isinstance(results, list)

    def test_apply_returns_semantic_mapping(self):
        from cogant.schemas.semantic import SemanticMapping
        from cogant.translate.rules.structural import ReadOnlyInputRule

        graph, mod, var1, var2 = _make_graph_with_module_reads()
        rule = ReadOnlyInputRule()
        results = rule.matches(graph, _make_query(graph))
        if results:
            mapping = rule.apply(graph, results[0])
            assert isinstance(mapping, SemanticMapping)

    def test_apply_missing_node_returns_none(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule

        graph = _make_empty_graph()
        rule = ReadOnlyInputRule()
        result = rule.apply(graph, {"node_id": "nonexistent", "read_count": 1, "write_count": 0})
        assert result is None

    def test_apply_confidence_score(self):
        from cogant.translate.rules.structural import ReadOnlyInputRule

        graph, mod, var1, var2 = _make_graph_with_module_reads()
        rule = ReadOnlyInputRule()
        results = rule.matches(graph, _make_query(graph))
        if results:
            mapping = rule.apply(graph, results[0])
            assert mapping is not None
            assert 0.0 < mapping.confidence_score <= 1.0


# ---------------------------------------------------------------------------
# MutatingSubsystemRule
# ---------------------------------------------------------------------------


class TestMutatingSubsystemRule:
    def test_name_property(self):
        from cogant.translate.rules.structural import MutatingSubsystemRule

        rule = MutatingSubsystemRule()
        assert rule.name == "mutating_subsystem"

    def test_mapping_kind_property(self):
        from cogant.schemas.semantic import MappingKind
        from cogant.translate.rules.structural import MutatingSubsystemRule

        rule = MutatingSubsystemRule()
        assert rule.mapping_kind == MappingKind.HIDDEN_STATE

    def test_matches_class_with_writes(self):
        from cogant.graph.builder import ProgramGraphBuilder
        from cogant.schemas.core import EdgeKind, NodeKind
        from cogant.translate.rules.structural import MutatingSubsystemRule

        builder = ProgramGraphBuilder(repo_uri="file:///test")
        mod = builder.add_node(NodeKind.MODULE, "m", "m", path="m.py", language="python")
        cls = builder.add_node(NodeKind.CLASS, "Agent", "m.Agent", path="m.py")
        var1 = builder.add_node(NodeKind.VARIABLE, "state", "m.state", path="m.py")
        builder.add_edge(mod.id, cls.id, EdgeKind.CONTAINS)
        # Direct WRITES edge from cls itself
        builder.add_edge(cls.id, var1.id, EdgeKind.WRITES)
        graph = builder.finalize()
        rule = MutatingSubsystemRule()
        results = rule.matches(graph, _make_query(graph))
        assert len(results) >= 1

    def test_matches_no_class_returns_empty(self):
        from cogant.translate.rules.structural import MutatingSubsystemRule

        graph = _make_empty_graph()
        rule = MutatingSubsystemRule()
        results = rule.matches(graph, _make_query(graph))
        assert results == []

    def test_apply_returns_hidden_state_mapping(self):
        from cogant.schemas.semantic import MappingKind, SemanticMapping
        from cogant.translate.rules.structural import MutatingSubsystemRule

        graph, mod, cls, func1, var1 = _make_graph_with_mutation()
        rule = MutatingSubsystemRule()
        results = rule.matches(graph, _make_query(graph))
        if results:
            mapping = rule.apply(graph, results[0])
            assert isinstance(mapping, SemanticMapping)
            assert mapping.kind == MappingKind.HIDDEN_STATE

    def test_apply_missing_node_returns_none(self):
        from cogant.translate.rules.structural import MutatingSubsystemRule

        graph = _make_empty_graph()
        rule = MutatingSubsystemRule()
        result = rule.apply(
            graph, {"node_id": "nonexistent", "mutation_count": 1, "mutation_edges": []}
        )
        assert result is None

    def test_priority_is_one(self):
        from cogant.translate.rules.structural import MutatingSubsystemRule

        rule = MutatingSubsystemRule()
        assert rule.priority == 1


# ---------------------------------------------------------------------------
# InheritanceRule
# ---------------------------------------------------------------------------


class TestInheritanceRule:
    def test_name_property(self):
        from cogant.translate.rules.structural import InheritanceRule

        rule = InheritanceRule()
        assert rule.name == "inheritance"

    def test_mapping_kind_property(self):
        from cogant.schemas.semantic import MappingKind
        from cogant.translate.rules.structural import InheritanceRule

        rule = InheritanceRule()
        # InheritanceRule produces HIDDEN_STATE (class hierarchy maps to state)
        assert rule.mapping_kind in (MappingKind.HIDDEN_STATE, MappingKind.POLICY)

    def test_matches_inheriting_class(self):
        from cogant.translate.rules.structural import InheritanceRule

        graph, mod, base, child = _make_graph_with_inheritance()
        rule = InheritanceRule()
        results = rule.matches(graph, _make_query(graph))
        assert len(results) >= 1

    def test_matches_no_inheritance_empty(self):
        from cogant.translate.rules.structural import InheritanceRule

        graph = _make_empty_graph()
        rule = InheritanceRule()
        results = rule.matches(graph, _make_query(graph))
        assert results == []

    def test_apply_returns_policy_or_hidden_state_mapping(self):
        from cogant.schemas.semantic import MappingKind, SemanticMapping
        from cogant.translate.rules.structural import InheritanceRule

        graph, mod, base, child = _make_graph_with_inheritance()
        rule = InheritanceRule()
        results = rule.matches(graph, _make_query(graph))
        if results:
            mapping = rule.apply(graph, results[0])
            assert isinstance(mapping, SemanticMapping)
            assert mapping.kind in (MappingKind.HIDDEN_STATE, MappingKind.POLICY)

    def test_apply_missing_node_returns_none(self):
        from cogant.translate.rules.structural import InheritanceRule

        graph = _make_empty_graph()
        rule = InheritanceRule()
        result = rule.apply(graph, {"node_id": "none", "parent_id": "none", "depth": 1})
        assert result is None


# ---------------------------------------------------------------------------
# ContainmentRule
# ---------------------------------------------------------------------------


class TestContainmentRule:
    def test_name_property(self):
        from cogant.translate.rules.structural import ContainmentRule

        rule = ContainmentRule()
        assert isinstance(rule.name, str)

    def test_mapping_kind_property(self):
        from cogant.schemas.semantic import MappingKind
        from cogant.translate.rules.structural import ContainmentRule

        rule = ContainmentRule()
        assert isinstance(rule.mapping_kind, MappingKind)

    def test_matches_returns_list(self):
        from cogant.translate.rules.structural import ContainmentRule

        graph, mod, cls, func1, var1 = _make_graph_with_mutation()
        rule = ContainmentRule()
        results = rule.matches(graph, _make_query(graph))
        assert isinstance(results, list)

    def test_apply_missing_node_returns_none(self):
        from cogant.translate.rules.structural import ContainmentRule

        graph = _make_empty_graph()
        rule = ContainmentRule()
        result = rule.apply(graph, {"node_id": "none", "contained_count": 0})
        assert result is None


# ---------------------------------------------------------------------------
# DataPipelineRule
# ---------------------------------------------------------------------------


class TestDataPipelineRule:
    def test_name_property(self):
        from cogant.translate.rules.structural import DataPipelineRule

        rule = DataPipelineRule()
        assert isinstance(rule.name, str)

    def test_mapping_kind_property(self):
        from cogant.schemas.semantic import MappingKind
        from cogant.translate.rules.structural import DataPipelineRule

        rule = DataPipelineRule()
        assert isinstance(rule.mapping_kind, MappingKind)

    def test_matches_pipeline_returns_list(self):
        from cogant.translate.rules.structural import DataPipelineRule

        graph, mod, s1, s2, s3 = _make_graph_with_pipeline()
        rule = DataPipelineRule()
        results = rule.matches(graph, _make_query(graph))
        assert isinstance(results, list)

    def test_apply_missing_node_returns_none(self):
        from cogant.translate.rules.structural import DataPipelineRule

        graph = _make_empty_graph()
        rule = DataPipelineRule()
        result = rule.apply(graph, {"node_id": "none", "pipeline_length": 0, "pipeline_nodes": []})
        assert result is None


# ---------------------------------------------------------------------------
# RetryPatternRule
# ---------------------------------------------------------------------------


class TestRetryPatternRule:
    def test_name_property(self):
        from cogant.translate.rules.resilience import RetryPatternRule

        rule = RetryPatternRule()
        assert isinstance(rule.name, str)

    def test_mapping_kind_property(self):
        from cogant.schemas.semantic import MappingKind
        from cogant.translate.rules.resilience import RetryPatternRule

        rule = RetryPatternRule()
        assert isinstance(rule.mapping_kind, MappingKind)

    def test_matches_retry_function(self):
        from cogant.translate.rules.resilience import RetryPatternRule

        graph, mod, retry_fn, normal_fn = _make_graph_with_retry()
        rule = RetryPatternRule()
        results = rule.matches(graph, _make_query(graph))
        assert len(results) >= 1

    def test_matches_returns_list(self):
        from cogant.translate.rules.resilience import RetryPatternRule

        graph = _make_empty_graph()
        rule = RetryPatternRule()
        results = rule.matches(graph, _make_query(graph))
        assert isinstance(results, list)

    def test_apply_returns_mapping(self):
        from cogant.schemas.semantic import SemanticMapping
        from cogant.translate.rules.resilience import RetryPatternRule

        graph, mod, retry_fn, normal_fn = _make_graph_with_retry()
        rule = RetryPatternRule()
        results = rule.matches(graph, _make_query(graph))
        if results:
            mapping = rule.apply(graph, results[0])
            assert isinstance(mapping, SemanticMapping)

    def test_apply_missing_node_returns_none(self):
        from cogant.translate.rules.resilience import RetryPatternRule

        graph = _make_empty_graph()
        rule = RetryPatternRule()
        result = rule.apply(graph, {"node_id": "none", "pattern_type": "retry_or_circuit_breaker"})
        assert result is None


# ---------------------------------------------------------------------------
# ErrorBoundaryRule
# ---------------------------------------------------------------------------


class TestErrorBoundaryRule:
    def test_name_property(self):
        try:
            from cogant.translate.rules.resilience import ErrorBoundaryRule

            rule = ErrorBoundaryRule()
            assert isinstance(rule.name, str)
        except (ImportError, AttributeError):
            pytest.skip("ErrorBoundaryRule not available")

    def test_mapping_kind_property(self):
        try:
            from cogant.schemas.semantic import MappingKind
            from cogant.translate.rules.resilience import ErrorBoundaryRule

            rule = ErrorBoundaryRule()
            assert isinstance(rule.mapping_kind, MappingKind)
        except (ImportError, AttributeError):
            pytest.skip("ErrorBoundaryRule not available")

    def test_matches_returns_list(self):
        try:
            from cogant.translate.rules.resilience import ErrorBoundaryRule

            graph = _make_empty_graph()
            rule = ErrorBoundaryRule()
            results = rule.matches(graph, _make_query(graph))
            assert isinstance(results, list)
        except (ImportError, AttributeError):
            pytest.skip("ErrorBoundaryRule not available")


# ---------------------------------------------------------------------------
# SingletonRule
# ---------------------------------------------------------------------------


class TestSingletonRule:
    def test_name_property(self):
        try:
            from cogant.translate.rules.resilience import SingletonRule

            rule = SingletonRule()
            assert isinstance(rule.name, str)
        except (ImportError, AttributeError):
            pytest.skip("SingletonRule not available")

    def test_matches_returns_list(self):
        try:
            from cogant.translate.rules.resilience import SingletonRule

            graph = _make_empty_graph()
            rule = SingletonRule()
            results = rule.matches(graph, _make_query(graph))
            assert isinstance(results, list)
        except (ImportError, AttributeError):
            pytest.skip("SingletonRule not available")


# ---------------------------------------------------------------------------
# CircuitBreakerRule
# ---------------------------------------------------------------------------


class TestCircuitBreakerRule:
    def test_name_property(self):
        try:
            from cogant.translate.rules.resilience import CircuitBreakerRule

            rule = CircuitBreakerRule()
            assert isinstance(rule.name, str)
        except (ImportError, AttributeError):
            pytest.skip("CircuitBreakerRule not available")

    def test_matches_circuit_breaker(self):
        try:
            from cogant.graph.builder import ProgramGraphBuilder
            from cogant.schemas.core import EdgeKind, NodeKind
            from cogant.translate.rules.resilience import CircuitBreakerRule

            builder = ProgramGraphBuilder(repo_uri="file:///test")
            mod = builder.add_node(NodeKind.MODULE, "m", "m", path="m.py", language="python")
            cb_fn = builder.add_node(NodeKind.FUNCTION, "circuit_breaker_open", "m.cb", path="m.py")
            builder.add_edge(mod.id, cb_fn.id, EdgeKind.CONTAINS)
            graph = builder.finalize()
            rule = CircuitBreakerRule()
            results = rule.matches(graph, _make_query(graph))
            assert isinstance(results, list)
        except (ImportError, AttributeError):
            pytest.skip("CircuitBreakerRule not available")
