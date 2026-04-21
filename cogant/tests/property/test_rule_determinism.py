"""Property tests for rule determinism and stability.

Using Hypothesis, verify that translation rules are deterministic:
- Same graph input produces same mappings across multiple runs
- Rule evidence is stable and reproducible
- No floating-point nondeterminism in scoring
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# Ensure cogant imports work
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PY_ROOT = _REPO_ROOT / "py"
if str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))

from cogant.graph.builder import ProgramGraphBuilder
from cogant.graph.queries import GraphQuery
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.translate.engine import TranslationEngine
from cogant.translate.rules import (
    ActionRule,
    ContainmentRule,
    InheritanceRule,
    MutatingSubsystemRule,
    ObservationRule,
    OrchestratorRule,
    ReadOnlyInputRule,
)

pytestmark = pytest.mark.property


# ============================================================================
# STRATEGIES: Hypothesis generators for graphs
# ============================================================================


_NODE_KINDS = [
    NodeKind.MODULE,
    NodeKind.CLASS,
    NodeKind.FUNCTION,
    NodeKind.METHOD,
    NodeKind.VARIABLE,
]

_EDGE_KINDS = [
    EdgeKind.CONTAINS,
    EdgeKind.READS,
    EdgeKind.WRITES,
    EdgeKind.CALLS,
    EdgeKind.INHERITS,
]


@st.composite
def small_graph(draw, min_nodes: int = 2, max_nodes: int = 15) -> ProgramGraph:
    """Generate small, well-formed program graphs."""
    n = draw(st.integers(min_value=min_nodes, max_value=max_nodes))
    builder = ProgramGraphBuilder(repo_uri="hypothesis://prop_rule_det")

    # Create nodes
    nodes = []
    for i in range(n):
        kind = draw(st.sampled_from(_NODE_KINDS))
        node = builder.add_node(
            kind=kind,
            name=f"node_{i}",
            qualified_name=f"node_{i}",
            path=f"file_{i % 3}.py",
            language="python",
        )
        nodes.append(node)

    # Add edges
    n_edges = draw(st.integers(min_value=0, max_value=n + 3))
    for _ in range(n_edges):
        src = draw(st.sampled_from(nodes))
        tgt = draw(st.sampled_from(nodes))
        if src.id != tgt.id:  # No self-loops
            kind = draw(st.sampled_from(_EDGE_KINDS))
            builder.add_edge(src.id, tgt.id, kind)

    return builder.finalize()


# ============================================================================
# TESTS: Rule determinism
# ============================================================================


class TestRuleDeterminism:
    """Property tests for rule determinism."""

    @given(small_graph())
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.filter_too_much],
    )
    def test_rule_matching_is_deterministic(self, graph: ProgramGraph):
        """Running rule.matches() twice on same graph yields same results."""
        rule = ReadOnlyInputRule()
        query1 = GraphQuery(graph)
        query2 = GraphQuery(graph)

        matches1 = rule.matches(graph, query1)
        matches2 = rule.matches(graph, query2)

        # Convert to comparable form (dicts may have same content but different ids)
        sig1 = frozenset((m.get("node_id"), m.get("edge_id")) for m in matches1)
        sig2 = frozenset((m.get("node_id"), m.get("edge_id")) for m in matches2)

        assert sig1 == sig2

    @given(small_graph())
    @settings(max_examples=20, deadline=None)
    def test_mapping_signatures_are_stable(self, graph: ProgramGraph):
        """Same engine, same graph -> same mapping signatures across runs."""
        engine = TranslationEngine()
        engine.register_rule(ReadOnlyInputRule())
        engine.register_rule(MutatingSubsystemRule())

        # First run
        mappings1 = engine.translate(graph)

        # Reset engine and run again
        engine2 = TranslationEngine()
        engine2.register_rule(ReadOnlyInputRule())
        engine2.register_rule(MutatingSubsystemRule())
        mappings2 = engine2.translate(graph)

        # Extract stable signatures (ignore ids and timestamps)
        def sig(mappings):
            return frozenset(
                (m.kind.value, tuple(sorted(m.graph_fragment_node_ids))) for m in mappings
            )

        assert sig(mappings1) == sig(mappings2)

    @given(small_graph())
    @settings(max_examples=20, deadline=None)
    def test_mapping_confidence_scores_are_deterministic(self, graph: ProgramGraph):
        """Confidence scores for same graph are consistent."""
        engine = TranslationEngine()
        engine.register_rule(ReadOnlyInputRule())
        engine.register_rule(ActionRule())
        engine.register_rule(ObservationRule())

        mappings1 = engine.translate(graph)

        engine2 = TranslationEngine()
        engine2.register_rule(ReadOnlyInputRule())
        engine2.register_rule(ActionRule())
        engine2.register_rule(ObservationRule())
        mappings2 = engine2.translate(graph)

        # Group mappings by kind and fragment, then compare confidence
        def score_map(mappings):
            result = {}
            for m in mappings:
                key = (m.kind.value, tuple(sorted(m.graph_fragment_node_ids)))
                result[key] = m.confidence_score
            return result

        scores1 = score_map(mappings1)
        scores2 = score_map(mappings2)

        # Same keys
        assert set(scores1.keys()) == set(scores2.keys())

        # Same confidence scores (within floating-point tolerance)
        for key in scores1:
            assert abs(scores1[key] - scores2[key]) < 1e-9

    @given(small_graph())
    @settings(max_examples=15, deadline=None)
    def test_rule_evidence_is_stable(self, graph: ProgramGraph):
        """Evidence strings for a rule firing are consistent."""
        rule = ContainmentRule()
        query1 = GraphQuery(graph)
        query2 = GraphQuery(graph)

        matches1 = rule.matches(graph, query1)
        matches2 = rule.matches(graph, query2)

        # Signatures should match
        sig1 = frozenset((m.get("source_id"), m.get("target_id")) for m in matches1)
        sig2 = frozenset((m.get("source_id"), m.get("target_id")) for m in matches2)

        assert sig1 == sig2


# ============================================================================
# TESTS: All rules preserve determinism on fixed fixtures
# ============================================================================


class TestAllRulesDeterminism:
    """Verify each of the 7 core rules is deterministic."""

    @pytest.mark.parametrize(
        "rule_class",
        [
            ReadOnlyInputRule,
            MutatingSubsystemRule,
            InheritanceRule,
            ContainmentRule,
            ObservationRule,
            ActionRule,
            OrchestratorRule,
        ],
        ids=lambda c: c.__name__,
    )
    @given(graph=small_graph())
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_rule_is_deterministic(self, rule_class, graph: ProgramGraph):
        """Each rule produces the same matches on repeated runs.

        Hypothesis is composed with ``pytest.mark.parametrize`` here: the
        rule class varies across pytest collection, while the graph varies
        across Hypothesis examples.
        """
        rule1 = rule_class()
        rule2 = rule_class()

        query1 = GraphQuery(graph)
        query2 = GraphQuery(graph)

        matches1 = rule1.matches(graph, query1)
        matches2 = rule2.matches(graph, query2)

        def _freeze(value):
            if isinstance(value, dict):
                return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
            if isinstance(value, list | tuple):
                return tuple(_freeze(v) for v in value)
            return value

        def canonical(matches):
            return frozenset(_freeze(m) for m in matches)

        assert canonical(matches1) == canonical(matches2)


# ============================================================================
# TESTS: Engine determinism over full pipelines
# ============================================================================


class TestEngineDeterminism:
    """Property tests for full translation engine determinism."""

    @given(small_graph())
    @settings(max_examples=15, deadline=None)
    def test_engine_translation_deterministic(self, graph: ProgramGraph):
        """TranslationEngine.translate() produces same mappings each call."""
        engine = TranslationEngine(max_iterations=5)
        engine.register_rule(ReadOnlyInputRule())
        engine.register_rule(MutatingSubsystemRule())
        engine.register_rule(ContainmentRule())

        # Run 1
        mappings1 = engine.translate(graph)

        # Run 2 (fresh engine)
        engine2 = TranslationEngine(max_iterations=5)
        engine2.register_rule(ReadOnlyInputRule())
        engine2.register_rule(MutatingSubsystemRule())
        engine2.register_rule(ContainmentRule())
        mappings2 = engine2.translate(graph)

        # Signatures match
        def sig(mappings):
            return frozenset(
                (m.kind.value, tuple(sorted(m.graph_fragment_node_ids))) for m in mappings
            )

        assert sig(mappings1) == sig(mappings2)

    @given(small_graph())
    @settings(max_examples=15, deadline=None)
    def test_fixpoint_iterations_consistent(self, graph: ProgramGraph):
        """Fixpoint convergence path is stable across runs."""
        engine = TranslationEngine(max_iterations=10)
        engine.register_rule(ReadOnlyInputRule())
        engine.register_rule(MutatingSubsystemRule())

        engine.translate(graph)
        iter_count1 = len(engine.iterations)

        engine2 = TranslationEngine(max_iterations=10)
        engine2.register_rule(ReadOnlyInputRule())
        engine2.register_rule(MutatingSubsystemRule())
        engine2.translate(graph)
        iter_count2 = len(engine2.iterations)

        # Same number of iterations
        assert iter_count1 == iter_count2


# ============================================================================
# TESTS: Confidence and evidence stability
# ============================================================================


class TestConfidenceStability:
    """Property tests for confidence score stability."""

    @given(small_graph())
    @settings(max_examples=15, deadline=None)
    def test_confidence_scores_no_nondeterminism(self, graph: ProgramGraph):
        """Confidence scores have no random variation."""
        engine = TranslationEngine()
        engine.register_rule(ObservationRule())
        engine.register_rule(ActionRule())

        run1 = engine.translate(graph)
        run2 = engine.translate(graph)

        # Group by mapping signature
        def by_sig(mappings):
            result = {}
            for m in mappings:
                sig = (m.kind.value, tuple(sorted(m.graph_fragment_node_ids)))
                result[sig] = m.confidence_score
            return result

        sig1 = by_sig(run1)
        sig2 = by_sig(run2)

        for key in sig1:
            if key in sig2:
                assert abs(sig1[key] - sig2[key]) < 1e-9

    @given(small_graph())
    @settings(max_examples=10, deadline=None)
    def test_evidence_count_consistent(self, graph: ProgramGraph):
        """Evidence counts are stable across runs."""
        engine = TranslationEngine()
        engine.register_rule(ContainmentRule())
        engine.register_rule(InheritanceRule())

        mappings1 = engine.translate(graph)

        engine2 = TranslationEngine()
        engine2.register_rule(ContainmentRule())
        engine2.register_rule(InheritanceRule())
        mappings2 = engine2.translate(graph)

        def by_sig(mappings):
            result = {}
            for m in mappings:
                sig = (m.kind.value, tuple(sorted(m.graph_fragment_node_ids)))
                result[sig] = m.evidence_count
            return result

        sig1 = by_sig(mappings1)
        sig2 = by_sig(mappings2)

        for key in sig1:
            if key in sig2:
                assert sig1[key] == sig2[key]
