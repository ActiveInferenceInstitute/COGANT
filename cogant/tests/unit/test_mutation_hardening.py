"""Targeted tests that kill specific surviving mutants.

These tests exist because mutation testing (see
``_rnd/MUTATION_REPORT.md``) found that the baseline suite silently
ignored a handful of semantically meaningful code changes. Each test in
this file pins one of those behaviours so a mutation that previously
"survived" is now caught.

Every test is deliberately narrow: one behaviour, one assertion, no
fixture reuse. The goal is not coverage, it is *defensive coverage* of
the exact contract the original code intended.

Cross-reference: ``_rnd/MUTATION_REPORT.md`` → "Surviving mutants"
section.
"""

from __future__ import annotations

import pytest

from cogant.gnn.matrices import GNNMatrices
from cogant.graph.builder import ProgramGraphBuilder
from cogant.markov import BlanketRole, partition_by_seeds
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.semantic import MappingKind, SemanticMapping
from cogant.statespace.compiler import (
    ObservationModality,
    StateSpaceCompiler,
    StateSpaceModel,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import (
    ConfidenceLevel,
    StateVariable,
    StateVariableType,
)

pytestmark = pytest.mark.unit


# ==========================================================================
# Kills M4 — compute_C aversive-preference path
# ==========================================================================


class TestCVectorAversivePreference:
    """Preference mappings with 'avoid'/'reject'/'!' labels must
    contribute NEGATIVE log-preference to C. Surviving mutation: flipping
    ``label.startswith(("avoid", "reject", "!"))`` to never match was
    not caught by any baseline test.
    """

    def _build(self, label: str, confidence: float = 0.7) -> GNNMatrices:
        builder = ProgramGraphBuilder(repo_uri="test://c_aversive")
        state = builder.add_node(
            kind=NodeKind.VARIABLE,
            name="s",
            qualified_name="m.s",
            path="m.py",
            language="python",
        )
        obs = builder.add_node(
            kind=NodeKind.FUNCTION,
            name="sense",
            qualified_name="m.sense",
            path="m.py",
            language="python",
        )
        builder.add_edge(obs.id, state.id, EdgeKind.READS)
        graph = builder.finalize()

        mappings = {
            "m:s": SemanticMapping(
                id="m:s",
                kind=MappingKind.HIDDEN_STATE,
                graph_fragment_node_ids=[state.id],
                semantic_label="s",
                confidence_score=0.9,
            ),
            "m:obs": SemanticMapping(
                id="m:obs",
                kind=MappingKind.OBSERVATION,
                graph_fragment_node_ids=[obs.id],
                semantic_label="sense",
                confidence_score=0.9,
            ),
            "m:pref": SemanticMapping(
                id="m:pref",
                kind=MappingKind.PREFERENCE,
                graph_fragment_node_ids=[obs.id],
                semantic_label=label,
                confidence_score=confidence,
            ),
        }

        state_space = StateSpaceModel(
            id="ss:c_aversive",
            schema_name="c_aversive",
            variables={
                "var:s": StateVariable(
                    id="var:s",
                    name="s",
                    var_type=StateVariableType.DISCRETE,
                    node_id=state.id,
                    cardinality=2,
                    confidence=ConfidenceLevel.HIGH,
                ),
            },
            observations={
                "obs:sense": ObservationModality(
                    id="obs:sense",
                    name="sense",
                    source_node_id=obs.id,
                    modality_type="generic",
                    cardinality=2,
                    confidence=ConfidenceLevel.MEDIUM,
                ),
            },
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
            metadata={},
        )
        return GNNMatrices(graph=graph, mappings=mappings, state_space=state_space)

    def test_avoid_prefix_produces_negative_log_preference(self) -> None:
        matrices = self._build(label="avoid_crash", confidence=0.7)
        C = matrices.compute_C()
        assert len(C) == 1
        assert C[0] < 0.0, (
            f"'avoid_' PREFERENCE should yield negative log-pref, got C[0]={C[0]}"
        )
        assert C[0] == pytest.approx(-0.7, abs=1e-9)

    def test_reject_prefix_produces_negative_log_preference(self) -> None:
        matrices = self._build(label="reject_nan", confidence=0.5)
        C = matrices.compute_C()
        assert C[0] < 0.0
        assert C[0] == pytest.approx(-0.5, abs=1e-9)

    def test_bang_prefix_produces_negative_log_preference(self) -> None:
        matrices = self._build(label="!forbidden", confidence=0.3)
        C = matrices.compute_C()
        assert C[0] < 0.0
        assert C[0] == pytest.approx(-0.3, abs=1e-9)

    def test_non_aversive_preference_is_non_negative(self) -> None:
        """Sanity guard: a plain PREFERENCE with no aversive prefix must
        not acquire a negative sign. This kills the *opposite* mutation
        (make every PREFERENCE aversive)."""
        matrices = self._build(label="prefer_smooth", confidence=0.4)
        C = matrices.compute_C()
        assert C[0] >= 0.0


# ==========================================================================
# Kills M8 — markov sensory↔active swap
# ==========================================================================


class TestMarkovBoundaryDirection:
    """Boundary nodes must be classified by edge direction:
    out-only → ACTIVE, in-only → SENSORY. Surviving mutation: swapping
    the two role assignments left every existing markov test green.
    """

    def _two_node_graph(self, direction: str):
        """Build a 2-node graph with one directed edge between them."""
        b = ProgramGraphBuilder(repo_uri=f"test://markov_dir_{direction}")
        inner = b.add_node(
            kind=NodeKind.FUNCTION,
            name="inner",
            qualified_name="m.inner",
            path="m.py",
            language="python",
        )
        outer = b.add_node(
            kind=NodeKind.FUNCTION,
            name="outer",
            qualified_name="m.outer",
            path="m.py",
            language="python",
        )
        if direction == "out":
            # inner --CALLS--> outer : inner has outgoing edge to external
            b.add_edge(inner.id, outer.id, EdgeKind.CALLS)
        elif direction == "in":
            # outer --CALLS--> inner : inner has incoming edge from external
            b.add_edge(outer.id, inner.id, EdgeKind.CALLS)
        else:
            raise ValueError(f"bad direction: {direction}")
        return b.finalize(), inner.id, outer.id

    def test_boundary_with_only_outgoing_edge_is_active(self) -> None:
        graph, inner_id, outer_id = self._two_node_graph("out")
        blanket = partition_by_seeds(graph, seeds={inner_id})
        assert inner_id in blanket.active_ids, (
            "node with outgoing-to-external edge should be ACTIVE"
        )
        assert inner_id not in blanket.sensory_ids, (
            "ACTIVE node must not also be SENSORY"
        )
        assert blanket.role_of(inner_id) is BlanketRole.ACTIVE
        assert outer_id in blanket.external_ids

    def test_boundary_with_only_incoming_edge_is_sensory(self) -> None:
        graph, inner_id, outer_id = self._two_node_graph("in")
        blanket = partition_by_seeds(graph, seeds={inner_id})
        assert inner_id in blanket.sensory_ids, (
            "node with incoming-from-external edge should be SENSORY"
        )
        assert inner_id not in blanket.active_ids, (
            "SENSORY node must not also be ACTIVE"
        )
        assert blanket.role_of(inner_id) is BlanketRole.SENSORY
        assert outer_id in blanket.external_ids

    def test_bidirectional_boundary_is_active_and_tagged(self) -> None:
        """A boundary node with edges flowing in AND out is ACTIVE
        (because it has causal influence outward) and reported in
        metadata.bidirectional_ids."""
        b = ProgramGraphBuilder(repo_uri="test://markov_bidi")
        inner = b.add_node(
            kind=NodeKind.FUNCTION,
            name="inner",
            qualified_name="m.inner",
            path="m.py",
            language="python",
        )
        outer = b.add_node(
            kind=NodeKind.FUNCTION,
            name="outer",
            qualified_name="m.outer",
            path="m.py",
            language="python",
        )
        b.add_edge(inner.id, outer.id, EdgeKind.CALLS)
        b.add_edge(outer.id, inner.id, EdgeKind.READS)
        graph = b.finalize()
        blanket = partition_by_seeds(graph, seeds={inner.id})
        assert inner.id in blanket.active_ids
        assert inner.id not in blanket.sensory_ids
        assert inner.id in blanket.metadata["bidirectional_ids"]


# ==========================================================================
# Kills M9 — _map_confidence boundary values
# ==========================================================================


class TestMapConfidenceExactBoundaries:
    """``_map_confidence`` uses ``>=`` to segment confidence into tiers,
    so the exact cutoff values (0.95, 0.80, 0.60, 0.40) must land in
    the HIGHER tier. Surviving mutation: flipping every ``>=`` to ``>``
    was not caught because the baseline test only exercised mid-tier
    values.
    """

    @pytest.fixture
    def compiler(self) -> StateSpaceCompiler:
        b = ProgramGraphBuilder(repo_uri="test://compiler_boundary")
        graph = b.finalize()
        return StateSpaceCompiler(graph, schema_name="boundary")

    def test_exact_definite_boundary(self, compiler: StateSpaceCompiler) -> None:
        assert compiler._map_confidence(0.95) is ConfidenceLevel.DEFINITE

    def test_exact_high_boundary(self, compiler: StateSpaceCompiler) -> None:
        assert compiler._map_confidence(0.80) is ConfidenceLevel.HIGH

    def test_exact_medium_boundary(self, compiler: StateSpaceCompiler) -> None:
        assert compiler._map_confidence(0.60) is ConfidenceLevel.MEDIUM

    def test_exact_low_boundary(self, compiler: StateSpaceCompiler) -> None:
        assert compiler._map_confidence(0.40) is ConfidenceLevel.LOW

    def test_just_below_definite_is_high(
        self, compiler: StateSpaceCompiler
    ) -> None:
        """Complementary assertion: 0.949999... must be HIGH, not
        DEFINITE. This kills a mutation that widens the DEFINITE tier."""
        assert compiler._map_confidence(0.9499) is ConfidenceLevel.HIGH

    def test_just_below_high_is_medium(
        self, compiler: StateSpaceCompiler
    ) -> None:
        assert compiler._map_confidence(0.7999) is ConfidenceLevel.MEDIUM
