"""Unit tests for :class:`cogant.gnn.matrices.GNNMatrices`.

These tests exercise the A/B/C/D matrix derivation against real COGANT
value objects (``ProgramGraph``, ``StateSpaceModel``, ``SemanticMapping``)
without numpy or mocking. The matrices are pure functions over the
inputs, so every assertion is deterministic.

The fixture builds a minimal but realistic Active Inference model with:

* 3 hidden-state factors (s_f0, s_f1, s_f2)
* 2 observation modalities (o_m0 observes s_f0, o_m1 observes s_f1)
* 2 actions (u_c0 writes s_f0, u_c1 writes s_f2)
* 1 constraint attached to o_m0 (preferring that observation)
"""

from __future__ import annotations

import pytest

from cogant.gnn.matrices import GNNMatrices
from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)
from cogant.statespace.compiler import (
    Action,
    ObservationModality,
    StateSpaceModel,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import (
    ConfidenceLevel,
    StateVariable,
    StateVariableType,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- fixtures


@pytest.fixture
def sample_graph_and_ids() -> tuple[ProgramGraph, dict[str, str]]:
    """Build a minimal program graph with hidden-state/obs/action nodes.

    Returns:
        ``(graph, ids)`` where ``ids`` maps symbolic role names to
        stable node IDs assigned by the builder.
    """
    builder = ProgramGraphBuilder(repo_uri="test://gnn-matrices")

    # Hidden state nodes
    s0 = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="state0",
        qualified_name="m.state0",
        path="m.py",
        language="python",
    )
    s1 = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="state1",
        qualified_name="m.state1",
        path="m.py",
        language="python",
    )
    s2 = builder.add_node(
        kind=NodeKind.VARIABLE,
        name="state2",
        qualified_name="m.state2",
        path="m.py",
        language="python",
    )

    # Observation nodes (functions that return something observable)
    o0 = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="sense_state0",
        qualified_name="m.sense_state0",
        path="m.py",
        language="python",
    )
    o1 = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="sense_state1",
        qualified_name="m.sense_state1",
        path="m.py",
        language="python",
    )

    # Action nodes
    a0 = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="act_write_s0",
        qualified_name="m.act_write_s0",
        path="m.py",
        language="python",
    )
    a1 = builder.add_node(
        kind=NodeKind.FUNCTION,
        name="act_write_s2",
        qualified_name="m.act_write_s2",
        path="m.py",
        language="python",
    )

    # Edges: observations read their respective states
    builder.add_edge(o0.id, s0.id, EdgeKind.READS)
    builder.add_edge(o1.id, s1.id, EdgeKind.READS)

    # Actions write their target states
    builder.add_edge(a0.id, s0.id, EdgeKind.WRITES)
    builder.add_edge(a1.id, s2.id, EdgeKind.WRITES)

    graph = builder.finalize() if hasattr(builder, "finalize") else builder.graph
    return (
        graph,
        {
            "s0": s0.id,
            "s1": s1.id,
            "s2": s2.id,
            "o0": o0.id,
            "o1": o1.id,
            "a0": a0.id,
            "a1": a1.id,
        },
    )


@pytest.fixture
def state_space(sample_graph_and_ids) -> StateSpaceModel:
    """Minimal StateSpaceModel with 3 variables, 2 obs, 2 actions."""
    _graph, ids = sample_graph_and_ids
    variables = {}
    for i, key in enumerate(("s0", "s1", "s2")):
        v = StateVariable(
            id=f"var:{key}",
            name=key,
            var_type=StateVariableType.DISCRETE,
            node_id=ids[key],
            cardinality=2,
            confidence=ConfidenceLevel.HIGH,
        )
        variables[v.id] = v

    observations = {}
    for i, key in enumerate(("o0", "o1")):
        o = ObservationModality(
            id=f"obs:{key}",
            name=key,
            source_node_id=ids[key],
            modality_type="generic",
            cardinality=2,
            confidence=ConfidenceLevel.MEDIUM,
        )
        observations[o.id] = o

    actions = {}
    for i, key in enumerate(("a0", "a1")):
        a = Action(
            id=f"act:{key}",
            name=key,
            controller_id=ids[key],
            confidence=ConfidenceLevel.MEDIUM,
        )
        actions[a.id] = a

    return StateSpaceModel(
        id="ss:matrices",
        schema_name="matrices_fixture",
        variables=variables,
        observations=observations,
        actions=actions,
        transitions={},
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
        metadata={},
    )


@pytest.fixture
def semantic_mappings(sample_graph_and_ids) -> dict[str, SemanticMapping]:
    """Build semantic mappings: HIDDEN_STATE, OBSERVATION, ACTION, CONSTRAINT."""
    _graph, ids = sample_graph_and_ids
    mappings: dict[str, SemanticMapping] = {}

    # Hidden states
    for i, key in enumerate(("s0", "s1", "s2")):
        m = SemanticMapping(
            id=f"m:{key}",
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=[ids[key]],
            semantic_label=key,
            confidence_score=0.9 - i * 0.1,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
        )
        mappings[m.id] = m

    # Observations
    for i, key in enumerate(("o0", "o1")):
        m = SemanticMapping(
            id=f"m:{key}",
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[ids[key]],
            semantic_label=key,
            confidence_score=0.85,
        )
        mappings[m.id] = m

    # Actions
    for i, key in enumerate(("a0", "a1")):
        m = SemanticMapping(
            id=f"m:{key}",
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=[ids[key]],
            semantic_label=key,
            confidence_score=0.8,
        )
        mappings[m.id] = m

    # Constraint: positive preference on observation o0.
    c = SemanticMapping(
        id="m:c_prefer_o0",
        kind=MappingKind.CONSTRAINT,
        graph_fragment_node_ids=[ids["o0"]],
        semantic_label="prefer_o0",
        confidence_score=0.75,
    )
    mappings[c.id] = c

    return mappings


@pytest.fixture
def matrices(
    sample_graph_and_ids,
    semantic_mappings,
    state_space,
) -> GNNMatrices:
    graph, _ = sample_graph_and_ids
    return GNNMatrices(
        graph=graph, mappings=semantic_mappings, state_space=state_space
    )


# ------------------------------------------------------------------- dimensions


class TestGNNMatricesDimensions:
    """Tests for dimension accessors."""

    def test_n_states_reflects_hidden_state_mappings(
        self, matrices: GNNMatrices
    ) -> None:
        assert matrices.n_states == 3

    def test_n_obs_reflects_observation_mappings(
        self, matrices: GNNMatrices
    ) -> None:
        assert matrices.n_obs == 2

    def test_n_actions_reflects_action_mappings(
        self, matrices: GNNMatrices
    ) -> None:
        assert matrices.n_actions == 2


# ------------------------------------------------------------------- A matrix


class TestAMatrix:
    """Tests for the likelihood matrix A."""

    def test_A_matrix_shape(self, matrices: GNNMatrices) -> None:
        A = matrices.compute_A()
        assert len(A) == matrices.n_obs  # 2 observations
        for row in A:
            assert len(row) == matrices.n_states  # 3 hidden states

    def test_A_rows_sum_to_one(self, matrices: GNNMatrices) -> None:
        """Each row of A must be a valid probability distribution."""
        A = matrices.compute_A()
        for i, row in enumerate(A):
            assert abs(sum(row) - 1.0) < 1e-6, (
                f"A row {i} sums to {sum(row)}"
            )

    def test_A_concentrates_mass_on_direct_reads(
        self, matrices: GNNMatrices
    ) -> None:
        """Observation 0 reads state 0, so A[0][0] should be the largest."""
        A = matrices.compute_A()
        # A[0] is the likelihood of obs 0 over hidden states.
        # State 0 is the direct read → it should dominate.
        assert A[0][0] > A[0][1]
        assert A[0][0] > A[0][2]
        # Observation 1 reads state 1.
        assert A[1][1] > A[1][0]
        assert A[1][1] > A[1][2]


# ------------------------------------------------------------------- B tensor


class TestBMatrix:
    """Tests for the transition tensor B."""

    def test_B_matrix_shape(self, matrices: GNNMatrices) -> None:
        B = matrices.compute_B()
        n_s = matrices.n_states
        n_a = matrices.n_actions
        assert len(B) == n_s
        for row in B:
            assert len(row) == n_s
            for cell in row:
                assert len(cell) == n_a

    def test_B_columns_sum_to_one_per_action(
        self, matrices: GNNMatrices
    ) -> None:
        """For each (current state, action) column, sum over next states == 1."""
        B = matrices.compute_B()
        n_s = matrices.n_states
        n_a = matrices.n_actions
        for cur in range(n_s):
            for k in range(n_a):
                col_sum = sum(B[nxt][cur][k] for nxt in range(n_s))
                assert abs(col_sum - 1.0) < 1e-6, (
                    f"B column (cur={cur}, k={k}) sums to {col_sum}"
                )

    def test_B_action_writes_concentrate_mass(
        self, matrices: GNNMatrices
    ) -> None:
        """Action 0 writes state 0 → B[0][cur][0] should dominate."""
        B = matrices.compute_B()
        # From state 1, action 0 should push mass toward state 0.
        assert B[0][1][0] > B[1][1][0], (
            "Action 0 should transition away from current state toward state 0"
        )


# ------------------------------------------------------------------- C vector


class TestCVector:
    """Tests for the log-preference vector C."""

    def test_C_vector_length(self, matrices: GNNMatrices) -> None:
        C = matrices.compute_C()
        assert len(C) == matrices.n_obs

    def test_C_reflects_constraint_on_o0(self, matrices: GNNMatrices) -> None:
        """The constraint attached to obs 0 should make C[0] > C[1]."""
        C = matrices.compute_C()
        assert C[0] > 0.0
        assert C[1] == 0.0  # no constraint on obs 1
        assert C[0] > C[1]


# ------------------------------------------------------------------- D vector


class TestDVector:
    """Tests for the initial prior vector D."""

    def test_D_vector_length(self, matrices: GNNMatrices) -> None:
        D = matrices.compute_D()
        assert len(D) == matrices.n_states

    def test_D_sums_to_one(self, matrices: GNNMatrices) -> None:
        D = matrices.compute_D()
        assert abs(sum(D) - 1.0) < 1e-6, f"D sums to {sum(D)}"

    def test_D_all_nonnegative(self, matrices: GNNMatrices) -> None:
        D = matrices.compute_D()
        for v in D:
            assert v >= 0.0


# --------------------------------------------------------- markdown / dict


class TestMatrixOutputs:
    """Tests for the markdown and dict output formatters."""

    def test_markdown_block_contains_all_sections(
        self, matrices: GNNMatrices
    ) -> None:
        block = matrices.to_gnn_markdown_block()
        assert "A[[rows=" in block
        assert "B[[rows=" in block
        assert "C[[rows=" in block
        assert "D[[rows=" in block

    def test_markdown_block_has_depth_for_B(
        self, matrices: GNNMatrices
    ) -> None:
        block = matrices.to_gnn_markdown_block()
        assert "depth=" in block

    def test_to_dict_has_all_keys(self, matrices: GNNMatrices) -> None:
        d = matrices.to_dict()
        assert set(d.keys()) >= {"A", "B", "C", "D", "shapes", "dimensions"}
        assert d["dimensions"]["n_states"] == 3
        assert d["dimensions"]["n_obs"] == 2
        assert d["dimensions"]["n_actions"] == 2

    def test_shapes_reported_correctly(self, matrices: GNNMatrices) -> None:
        d = matrices.to_dict()
        assert d["shapes"]["A"] == [2, 3]
        assert d["shapes"]["B"] == [3, 3, 2]
        assert d["shapes"]["C"] == [2]
        assert d["shapes"]["D"] == [3]


# --------------------------------------------------------- validate_shapes


class TestValidateShapes:
    """Tests for the built-in shape validator."""

    def test_validate_shapes_ok_for_fixture(
        self, matrices: GNNMatrices
    ) -> None:
        ok, errors = matrices.validate_shapes()
        assert ok, f"Expected valid shapes, got errors: {errors}"


# ---------------------------------------------- empty / degenerate inputs


class TestEmptyModel:
    """Tests for empty or degenerate COGANT models."""

    def test_empty_state_space_returns_empty_matrices(self) -> None:
        builder = ProgramGraphBuilder(repo_uri="test://empty")
        graph = builder.graph
        empty_ss = StateSpaceModel(
            id="empty",
            schema_name="empty",
            variables={},
            observations={},
            actions={},
            transitions={},
            likelihoods={},
            preferences={},
            time_regime=TimeRegime.SYNCHRONOUS,
            metadata={},
        )
        m = GNNMatrices(graph=graph, mappings={}, state_space=empty_ss)
        assert m.compute_A() == []
        assert m.compute_B() == []
        assert m.compute_C() == []
        assert m.compute_D() == []

    def test_mappings_as_list_are_accepted(
        self,
        sample_graph_and_ids,
        state_space,
        semantic_mappings,
    ) -> None:
        graph, _ = sample_graph_and_ids
        m = GNNMatrices(
            graph=graph,
            mappings=list(semantic_mappings.values()),
            state_space=state_space,
        )
        assert m.n_states == 3
        assert len(m.compute_A()) == 2
