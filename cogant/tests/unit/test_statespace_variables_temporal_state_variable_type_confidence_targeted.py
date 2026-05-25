#!/usr/bin/env python3
"""Targeted branch tests — statespace/variables.py and statespace/temporal.py.

Covers:
- statespace/variables.py: StateVariableType enum, ConfidenceLevel enum,
  map_confidence_score, StateVariable dataclass, FactorizationInfo,
  StateVariableExtractor (init, extract with different mappings)
- statespace/temporal.py: TimeRegime enum, TemporalOrdering, EventPattern,
  TemporalMetrics, TemporalAnalyzer init and analyze
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helper: build a minimal program graph
# ---------------------------------------------------------------------------


def _make_graph(include_calls=True, include_async=False):
    from cogant.graph.builder import ProgramGraphBuilder
    from cogant.schemas.core import EdgeKind, NodeKind

    builder = ProgramGraphBuilder(repo_uri="file:///test")
    mod = builder.add_node(
        NodeKind.MODULE, "mymodule", "mymodule", path="mymodule.py", language="python"
    )
    func1 = builder.add_node(NodeKind.FUNCTION, "sender", "mymodule.sender", path="mymodule.py")
    func2 = builder.add_node(
        NodeKind.FUNCTION,
        "async_handler" if include_async else "receiver",
        "mymodule.receiver",
        path="mymodule.py",
    )
    var1 = builder.add_node(NodeKind.VARIABLE, "state", "mymodule.state", path="mymodule.py")
    builder.add_edge(mod.id, func1.id, EdgeKind.CONTAINS)
    builder.add_edge(mod.id, func2.id, EdgeKind.CONTAINS)
    builder.add_edge(mod.id, var1.id, EdgeKind.CONTAINS)
    if include_calls:
        builder.add_edge(func1.id, func2.id, EdgeKind.CALLS)
    builder.add_edge(func1.id, var1.id, EdgeKind.WRITES)
    builder.add_edge(func2.id, var1.id, EdgeKind.READS)
    return builder.finalize(), mod, func1, func2, var1


def _make_mappings(func1_id, var1_id):
    from cogant.schemas.semantic import MappingKind, SemanticMapping

    return {
        "m1": SemanticMapping(
            id="m1",
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=[var1_id],
            semantic_label="state_var",
            confidence_score=0.9,
        ),
        "m2": SemanticMapping(
            id="m2",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[func1_id],
            semantic_label="obs_var",
            confidence_score=0.7,
        ),
    }


# ---------------------------------------------------------------------------
# StateVariableType enum
# ---------------------------------------------------------------------------


class TestStateVariableType:
    def test_boolean(self):
        from cogant.statespace.variables import StateVariableType

        assert StateVariableType.BOOLEAN == "boolean"

    def test_discrete(self):
        from cogant.statespace.variables import StateVariableType

        assert StateVariableType.DISCRETE == "discrete"

    def test_continuous(self):
        from cogant.statespace.variables import StateVariableType

        assert StateVariableType.CONTINUOUS == "continuous"

    def test_categorical(self):
        from cogant.statespace.variables import StateVariableType

        assert StateVariableType.CATEGORICAL == "categorical"

    def test_vector(self):
        from cogant.statespace.variables import StateVariableType

        assert StateVariableType.VECTOR == "vector"

    def test_composite(self):
        from cogant.statespace.variables import StateVariableType

        assert StateVariableType.COMPOSITE == "composite"

    def test_all_members(self):
        from cogant.statespace.variables import StateVariableType

        assert len(StateVariableType) == 6


# ---------------------------------------------------------------------------
# ConfidenceLevel enum
# ---------------------------------------------------------------------------


class TestConfidenceLevel:
    def test_definite(self):
        from cogant.statespace.variables import ConfidenceLevel

        assert ConfidenceLevel.DEFINITE == "definite"

    def test_high(self):
        from cogant.statespace.variables import ConfidenceLevel

        assert ConfidenceLevel.HIGH == "high"

    def test_medium(self):
        from cogant.statespace.variables import ConfidenceLevel

        assert ConfidenceLevel.MEDIUM == "medium"

    def test_low(self):
        from cogant.statespace.variables import ConfidenceLevel

        assert ConfidenceLevel.LOW == "low"

    def test_uncertain(self):
        from cogant.statespace.variables import ConfidenceLevel

        assert ConfidenceLevel.UNCERTAIN == "uncertain"


# ---------------------------------------------------------------------------
# map_confidence_score
# ---------------------------------------------------------------------------


class TestMapConfidenceScore:
    def test_definite_at_0_99(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        assert map_confidence_score(0.99) == ConfidenceLevel.DEFINITE

    def test_definite_at_0_95(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        assert map_confidence_score(0.95) == ConfidenceLevel.DEFINITE

    def test_high_at_0_90(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        assert map_confidence_score(0.90) == ConfidenceLevel.HIGH

    def test_high_at_0_80(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        assert map_confidence_score(0.80) == ConfidenceLevel.HIGH

    def test_medium_at_0_70(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        assert map_confidence_score(0.70) == ConfidenceLevel.MEDIUM

    def test_medium_at_0_60(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        assert map_confidence_score(0.60) == ConfidenceLevel.MEDIUM

    def test_low_at_0_50(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        assert map_confidence_score(0.50) == ConfidenceLevel.LOW

    def test_low_at_0_40(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        assert map_confidence_score(0.40) == ConfidenceLevel.LOW

    def test_uncertain_at_0_20(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        assert map_confidence_score(0.20) == ConfidenceLevel.UNCERTAIN

    def test_uncertain_at_0_0(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        assert map_confidence_score(0.0) == ConfidenceLevel.UNCERTAIN

    def test_returns_confidence_level(self):
        from cogant.statespace.variables import ConfidenceLevel, map_confidence_score

        result = map_confidence_score(0.85)
        assert isinstance(result, ConfidenceLevel)


# ---------------------------------------------------------------------------
# StateVariable dataclass
# ---------------------------------------------------------------------------


class TestStateVariable:
    def test_basic_creation(self):
        from cogant.statespace.variables import StateVariable, StateVariableType

        sv = StateVariable(
            id="var_n1",
            name="my_state",
            var_type=StateVariableType.DISCRETE,
            node_id="n1",
            cardinality=4,
        )
        assert sv.id == "var_n1"
        assert sv.name == "my_state"
        assert sv.cardinality == 4

    def test_defaults(self):
        from cogant.statespace.variables import ConfidenceLevel, StateVariable, StateVariableType

        sv = StateVariable(id="v1", name="s", var_type=StateVariableType.BOOLEAN, node_id="n1")
        assert sv.cardinality is None
        assert sv.domain is None
        assert sv.factors is None
        assert sv.is_discrete is True
        assert sv.confidence == ConfidenceLevel.MEDIUM
        assert sv.description is None
        assert sv.mutations == []
        assert sv.reads == []
        assert sv.observable is False

    def test_continuous_type(self):
        from cogant.statespace.variables import StateVariable, StateVariableType

        sv = StateVariable(
            id="v1",
            name="pos",
            var_type=StateVariableType.CONTINUOUS,
            node_id="n1",
            is_discrete=False,
        )
        assert sv.var_type == StateVariableType.CONTINUOUS
        assert sv.is_discrete is False

    def test_observable_flag(self):
        from cogant.statespace.variables import StateVariable, StateVariableType

        sv = StateVariable(
            id="v1", name="s", var_type=StateVariableType.DISCRETE, node_id="n1", observable=True
        )
        assert sv.observable is True

    def test_mutations_and_reads_lists(self):
        from cogant.statespace.variables import StateVariable, StateVariableType

        sv = StateVariable(
            id="v1",
            name="s",
            var_type=StateVariableType.DISCRETE,
            node_id="n1",
            mutations=["e1", "e2"],
            reads=["e3"],
        )
        assert "e1" in sv.mutations
        assert "e3" in sv.reads


# ---------------------------------------------------------------------------
# FactorizationInfo dataclass
# ---------------------------------------------------------------------------


class TestFactorizationInfo:
    def test_creation(self):
        from cogant.statespace.variables import FactorizationInfo

        fi = FactorizationInfo(
            factors=["f1", "f2"],
            independence_score=0.8,
            dependencies={"f1": ["f2"]},
        )
        assert fi.independence_score == 0.8
        assert "f1" in fi.factors

    def test_no_dependencies(self):
        from cogant.statespace.variables import FactorizationInfo

        fi = FactorizationInfo(factors=["f1"], independence_score=1.0, dependencies={})
        assert fi.dependencies == {}


# ---------------------------------------------------------------------------
# StateVariableExtractor
# ---------------------------------------------------------------------------


class TestStateVariableExtractor:
    def test_init(self):
        from cogant.statespace.variables import StateVariableExtractor

        graph, *_ = _make_graph()
        extractor = StateVariableExtractor(graph)
        assert extractor.state_variables == {}
        assert extractor.factorization_map == {}

    def test_extract_returns_dict(self):
        from cogant.statespace.variables import StateVariableExtractor

        graph, mod, func1, func2, var1 = _make_graph()
        mappings = _make_mappings(func1.id, var1.id)
        extractor = StateVariableExtractor(graph)
        result = extractor.extract(mappings)
        assert isinstance(result, dict)

    def test_extract_hidden_state_mapping(self):
        from cogant.statespace.variables import StateVariable, StateVariableExtractor

        graph, mod, func1, func2, var1 = _make_graph()
        mappings = _make_mappings(func1.id, var1.id)
        extractor = StateVariableExtractor(graph)
        result = extractor.extract(mappings)
        assert len(result) >= 1
        assert all(isinstance(v, StateVariable) for v in result.values())

    def test_extract_empty_mappings(self):
        from cogant.statespace.variables import StateVariableExtractor

        graph, *_ = _make_graph()
        extractor = StateVariableExtractor(graph)
        result = extractor.extract({})
        assert result == {}

    def test_extract_populates_state_variables(self):
        from cogant.statespace.variables import StateVariableExtractor

        graph, mod, func1, func2, var1 = _make_graph()
        mappings = _make_mappings(func1.id, var1.id)
        extractor = StateVariableExtractor(graph)
        extractor.extract(mappings)
        assert len(extractor.state_variables) >= 1

    def test_extract_observable_flag_set(self):
        from cogant.schemas.semantic import MappingKind, SemanticMapping
        from cogant.statespace.variables import StateVariableExtractor

        graph, mod, func1, func2, var1 = _make_graph()
        # Create mappings where same node is both hidden state and observation
        mappings = {
            "m1": SemanticMapping(
                id="m1",
                kind=MappingKind.HIDDEN_STATE,
                graph_fragment_node_ids=[var1.id],
                semantic_label="sv",
                confidence_score=0.85,
            ),
            "m2": SemanticMapping(
                id="m2",
                kind=MappingKind.OBSERVATION,
                graph_fragment_node_ids=[var1.id],
                semantic_label="obs",
                confidence_score=0.85,
            ),
        }
        extractor = StateVariableExtractor(graph)
        result = extractor.extract(mappings)
        # At least one variable should be observable
        observable_vars = [v for v in result.values() if v.observable]
        assert len(observable_vars) >= 1


# ---------------------------------------------------------------------------
# TimeRegime enum
# ---------------------------------------------------------------------------


class TestTimeRegime:
    def test_synchronous(self):
        from cogant.statespace.temporal import TimeRegime

        assert TimeRegime.SYNCHRONOUS == "synchronous"

    def test_asynchronous(self):
        from cogant.statespace.temporal import TimeRegime

        assert TimeRegime.ASYNCHRONOUS == "asynchronous"

    def test_event_driven(self):
        from cogant.statespace.temporal import TimeRegime

        assert TimeRegime.EVENT_DRIVEN == "event_driven"

    def test_hybrid(self):
        from cogant.statespace.temporal import TimeRegime

        assert TimeRegime.HYBRID == "hybrid"

    def test_all_members(self):
        from cogant.statespace.temporal import TimeRegime

        assert len(TimeRegime) == 4


# ---------------------------------------------------------------------------
# TemporalOrdering dataclass
# ---------------------------------------------------------------------------


class TestTemporalOrdering:
    def test_creation(self):
        from cogant.statespace.temporal import TemporalOrdering

        to = TemporalOrdering(
            predecessor_id="n1",
            successor_id="n2",
            constraint_type="sequential",
            confidence=0.9,
        )
        assert to.predecessor_id == "n1"
        assert to.constraint_type == "sequential"
        assert to.confidence == 0.9


# ---------------------------------------------------------------------------
# EventPattern dataclass
# ---------------------------------------------------------------------------


class TestEventPattern:
    def test_creation(self):
        from cogant.statespace.temporal import EventPattern

        ep = EventPattern(
            event_node_id="e1",
            trigger_nodes=["t1"],
            handler_nodes=["h1"],
        )
        assert ep.event_node_id == "e1"
        assert ep.is_async is False

    def test_async_event(self):
        from cogant.statespace.temporal import EventPattern

        ep = EventPattern(
            event_node_id="e1",
            trigger_nodes=[],
            handler_nodes=[],
            is_async=True,
        )
        assert ep.is_async is True


# ---------------------------------------------------------------------------
# TemporalMetrics dataclass
# ---------------------------------------------------------------------------


class TestTemporalMetrics:
    def test_creation(self):
        from cogant.statespace.temporal import TemporalMetrics

        tm = TemporalMetrics(
            async_fraction=0.0,
            event_driven_fraction=0.0,
            parallel_edges_count=0,
            sequential_edges_count=5,
            event_patterns_count=0,
            has_async_handlers=False,
            has_event_triggers=False,
        )
        assert tm.sequential_edges_count == 5
        assert tm.has_loops is False
        assert tm.is_discrete is True

    def test_has_loops_flag(self):
        from cogant.statespace.temporal import TemporalMetrics

        tm = TemporalMetrics(
            async_fraction=0.0,
            event_driven_fraction=0.0,
            parallel_edges_count=0,
            sequential_edges_count=0,
            event_patterns_count=0,
            has_async_handlers=False,
            has_event_triggers=False,
            has_loops=True,
        )
        assert tm.has_loops is True


# ---------------------------------------------------------------------------
# TemporalAnalyzer
# ---------------------------------------------------------------------------


class TestTemporalAnalyzer:
    def test_init(self):
        from cogant.statespace.temporal import TemporalAnalyzer, TimeRegime

        graph, *_ = _make_graph()
        analyzer = TemporalAnalyzer(graph)
        assert analyzer.time_regime == TimeRegime.SYNCHRONOUS
        assert analyzer.orderings == []
        assert analyzer.event_patterns == []
        assert analyzer.metrics is None

    def test_analyze_returns_time_regime(self):
        from cogant.statespace.temporal import TemporalAnalyzer, TimeRegime

        graph, *_ = _make_graph()
        analyzer = TemporalAnalyzer(graph)
        result = analyzer.analyze()
        assert isinstance(result, TimeRegime)

    def test_analyze_sync_graph(self):
        from cogant.statespace.temporal import TemporalAnalyzer, TimeRegime

        graph, *_ = _make_graph(include_async=False)
        analyzer = TemporalAnalyzer(graph)
        result = analyzer.analyze()
        assert result == TimeRegime.SYNCHRONOUS

    def test_analyze_sets_orderings(self):
        from cogant.statespace.temporal import TemporalAnalyzer

        graph, *_ = _make_graph(include_calls=True)
        analyzer = TemporalAnalyzer(graph)
        analyzer.analyze()
        assert len(analyzer.orderings) >= 1

    def test_analyze_sets_metrics(self):
        from cogant.statespace.temporal import TemporalAnalyzer, TemporalMetrics

        graph, *_ = _make_graph()
        analyzer = TemporalAnalyzer(graph)
        analyzer.analyze()
        assert isinstance(analyzer.metrics, TemporalMetrics)

    def test_analyze_no_calls_no_orderings(self):
        from cogant.statespace.temporal import TemporalAnalyzer

        graph, *_ = _make_graph(include_calls=False)
        analyzer = TemporalAnalyzer(graph)
        analyzer.analyze()
        # With no CALLS edges, orderings should be empty
        assert len(analyzer.orderings) == 0

    def test_detect_async_nodes_empty(self):
        from cogant.statespace.temporal import TemporalAnalyzer

        graph, *_ = _make_graph(include_async=False)
        analyzer = TemporalAnalyzer(graph)
        async_nodes = analyzer._detect_async_nodes()
        assert isinstance(async_nodes, set)

    def test_detect_async_nodes_with_async_name(self):
        from cogant.statespace.temporal import TemporalAnalyzer

        graph, *_ = _make_graph(include_async=True)
        analyzer = TemporalAnalyzer(graph)
        async_nodes = analyzer._detect_async_nodes()
        # "async_handler" node should be detected
        assert len(async_nodes) >= 1

    def test_detect_event_nodes_empty(self):
        from cogant.statespace.temporal import TemporalAnalyzer

        graph, *_ = _make_graph()
        analyzer = TemporalAnalyzer(graph)
        event_nodes = analyzer._detect_event_nodes()
        assert isinstance(event_nodes, set)
