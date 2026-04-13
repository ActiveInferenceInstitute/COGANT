"""Behavioral validation tests for cogant.reverse — parser, planner,
synthesizer, callable, and metrics modules.

Tests exercise all public APIs against synthetic GNN markdown fixtures
and verify field-level correctness, compilation safety, and numeric
invariants. No mocks. No external dependencies beyond the cogant
package and numpy (which cogant already requires).
"""

from __future__ import annotations

import ast
import math
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from cogant.reverse.callable import MatrixFunctions
from cogant.reverse.metrics import (
    IsomorphismReport,
    compare_graph_structure,
    compare_role_distributions,
    compute_isomorphism_report,
)
from cogant.reverse.parser import ReverseGNNModel, parse_gnn
from cogant.reverse.planner import PackagePlan, plan_package
from cogant.reverse.synthesizer import synthesize_package


# ---------------------------------------------------------------------------
# Shared GNN markdown fixtures
# ---------------------------------------------------------------------------

MINIMAL_GNN = dedent("""\
## ModelName
MinimalModel

## StateSpaceBlock
s_f0[3,1,type=int]

## ActInfOntologyAnnotation
s_f0=HiddenState

## InitialParameterization
D_f0={ (0.5, 0.3, 0.2) }

## Connections
(s_f0) > (s_f0)
""")

MULTI_FACTOR_GNN = dedent("""\
## ModelName
MultiFactor

## StateSpaceBlock
s_f0[4,1,type=int]
s_f1[3,1,type=float]
o_m0[2,1,type=int]
u_c0[2,1,type=int]

## ActInfOntologyAnnotation
s_f0=HiddenState
s_f1=HiddenState
o_m0=Observation
u_c0=Action

## InitialParameterization
D_f0={ (0.4, 0.3, 0.2, 0.1) }
D_f1={ (0.6, 0.3, 0.1) }
A_m0={ ((0.7, 0.3), (0.2, 0.8)) }
B_f0=identity(4,4,2)
C_m0={ (1.0, -1.0) }

## Connections
(s_f0) > (o_m0)
(u_c0) > (s_f0)
""")

ALL_ROLES_GNN = dedent("""\
## ModelName
AllRoles

## StateSpaceBlock
s_f0[5,1,type=int]
o_m0[3,1,type=int]
o_m1[2,1,type=float]
u_c0[2,1,type=int]
u_c1[3,1,type=int]
pi_c0[1,1,type=int]
c_f0[1,1,type=bool]

## ActInfOntologyAnnotation
s_f0=HiddenState
o_m0=Observation
o_m1=Observation
u_c0=Action
u_c1=Action
pi_c0=Policy
c_f0=Constraint

## InitialParameterization
D_f0={ (0.2, 0.2, 0.2, 0.2, 0.2) }

## Connections
(s_f0) > (o_m0)
(s_f0) > (o_m1)
(u_c0) > (s_f0)
(u_c1) > (s_f0)
""")

MATRICES_FENCED_GNN = dedent("""\
## ModelName
FencedMatrices

## StateSpaceBlock
s_f0[2,1,type=int]
s_f1[2,1,type=int]
o_m0[2,1,type=int]
u_c0[2,1,type=int]

## ActInfOntologyAnnotation
s_f0=HiddenState
s_f1=HiddenState
o_m0=Observation
u_c0=Action

## InitialParameterization
D_f0={ (0.6, 0.4) }
D_f1={ (0.5, 0.5) }

```gnn-matrices
A[[rows=1][cols=2]]
0.8 0.2
D[[rows=2]]
0.7
0.3
```

## Connections
(s_f0) > (o_m0)
""")

HUMAN_NAMES_GNN = dedent("""\
## ModelName
HumanNamed

## StateSpaceBlock
s_f0[3,1,type=int]
s_f1[4,1,type=float]

## ActInfOntologyAnnotation
s_f0=HiddenState
s_f1=HiddenState

## InitialParameterization
D_f0={ (0.5, 0.3, 0.2) }
D_f1={ (0.4, 0.3, 0.2, 0.1) }

## State Space
### State Variables
| ID | Name | Type |
|----|------|------|
| s_f0 | Calculator | int |
| s_f1 | Temperature | float |
""")


# ===================================================================
# Parser validation (8 tests)
# ===================================================================


class TestParser:
    """Parser behavioral validation."""

    def test_parse_minimal_gnn(self) -> None:
        """Parse minimal GNN (hidden state only) -> correct model fields."""
        model = parse_gnn(MINIMAL_GNN)
        assert model.model_name == "minimalmodel"
        assert model.hidden_states == ["s_f0"]
        assert model.n_states == 1
        assert model.observations == []
        assert model.actions == []

    def test_parse_multi_factor_gnn(self) -> None:
        """Parse multi-factor GNN -> correct hidden_states list."""
        model = parse_gnn(MULTI_FACTOR_GNN)
        assert model.hidden_states == ["s_f0", "s_f1"]
        assert model.n_states == 2
        assert model.observations == ["o_m0"]
        assert model.actions == ["u_c0"]

    def test_parse_all_annotations(self) -> None:
        """Parse with all annotations -> all 7 roles present."""
        model = parse_gnn(ALL_ROLES_GNN)
        assert len(model.hidden_states) == 1
        assert len(model.observations) == 2
        assert len(model.actions) == 2
        assert len(model.policies) == 1
        assert len(model.constraints) == 1
        # Annotations dict should have all 7 entries
        assert len(model.annotations) == 7

    def test_parse_gnn_matrices_fenced_block(self) -> None:
        """Parse with gnn-matrices fenced block -> A/D populated from block."""
        model = parse_gnn(MATRICES_FENCED_GNN)
        # The fenced block overrides InitialParameterization
        assert model.A == [[0.8, 0.2]]
        assert model.D == [0.7, 0.3]

    def test_parse_human_names_table(self) -> None:
        """Parse with human names table -> human_names populated."""
        model = parse_gnn(HUMAN_NAMES_GNN)
        assert model.human_names.get("s_f0") == "Calculator"
        assert model.human_names.get("s_f1") == "Temperature"

    def test_parse_invalid_empty(self) -> None:
        """Parse invalid/empty -> no crash, default model."""
        model = parse_gnn("")
        assert model.model_name == "cogant_model"
        assert model.hidden_states == []
        assert model.n_states == 0

    def test_parse_from_path_object(self, tmp_path: Path) -> None:
        """Parse from Path object -> same as string."""
        gnn_file = tmp_path / "test.gnn.md"
        gnn_file.write_text(MINIMAL_GNN, encoding="utf-8")
        model = parse_gnn(gnn_file)
        assert model.model_name == "minimalmodel"
        assert model.hidden_states == ["s_f0"]

    def test_parse_roundtrip_field_comparison(self) -> None:
        """Parse round-trip: parse -> fields stable on re-parse of same input."""
        model1 = parse_gnn(MULTI_FACTOR_GNN)
        model2 = parse_gnn(MULTI_FACTOR_GNN)
        assert model1.model_name == model2.model_name
        assert model1.hidden_states == model2.hidden_states
        assert model1.observations == model2.observations
        assert model1.actions == model2.actions
        assert model1.D == model2.D
        assert model1.A == model2.A
        assert model1.cardinalities == model2.cardinalities


# ===================================================================
# Planner validation (5 tests)
# ===================================================================


class TestPlanner:
    """Planner behavioral validation."""

    def test_plan_minimal_model(self) -> None:
        """Plan minimal model -> plan has state_vars with correct slot/type."""
        model = parse_gnn(MINIMAL_GNN)
        plan = plan_package(model)
        assert len(plan.state_vars) == 1
        assert plan.state_vars[0].slot == "s_f0"
        assert plan.state_vars[0].python_type == "int"
        assert plan.state_vars[0].role == "HIDDEN_STATE"

    def test_plan_multi_factor(self) -> None:
        """Plan multi-factor -> plan has >= 2 state_vars."""
        model = parse_gnn(MULTI_FACTOR_GNN)
        plan = plan_package(model)
        assert len(plan.state_vars) >= 2

    def test_plan_with_observations(self) -> None:
        """Plan with observations -> plan has obs_functions with correct sigs."""
        model = parse_gnn(MULTI_FACTOR_GNN)
        plan = plan_package(model)
        assert len(plan.obs_functions) == 1
        obs = plan.obs_functions[0]
        assert obs.role == "OBSERVATION"
        assert obs.module == "observe.py"

    def test_plan_with_actions(self) -> None:
        """Plan with actions -> plan has action_functions."""
        model = parse_gnn(ALL_ROLES_GNN)
        plan = plan_package(model)
        assert len(plan.action_methods) == 2
        for act in plan.action_methods:
            assert act.role == "ACTION"
            assert act.module == "act.py"

    def test_plan_with_policies(self) -> None:
        """Plan with policies -> plan has policy_functions."""
        model = parse_gnn(ALL_ROLES_GNN)
        plan = plan_package(model)
        assert len(plan.policy_functions) == 1
        assert plan.policy_functions[0].role == "POLICY"
        assert plan.policy_functions[0].module == "policy.py"


# ===================================================================
# Synthesizer validation (6 tests)
# ===================================================================


class TestSynthesizer:
    """Synthesizer behavioral validation."""

    @pytest.fixture()
    def synth_dir(self, tmp_path: Path) -> Path:
        """Synthesize the multi-factor model and return package path."""
        model = parse_gnn(MULTI_FACTOR_GNN)
        plan = plan_package(model)
        return synthesize_package(plan, model, tmp_path)

    def test_synthesize_creates_all_files(self, synth_dir: Path) -> None:
        """Synthesize minimal -> all expected files created."""
        expected = [
            "state.py",
            "matrices.py",
            "observe.py",
            "act.py",
            "policy.py",
            "constraints.py",
        ]
        for fname in expected:
            assert (synth_dir / fname).exists(), f"Missing {fname}"

    def test_synthesize_state_has_dataclass(self, synth_dir: Path) -> None:
        """Synthesize -> state.py contains State class with fields."""
        content = (synth_dir / "state.py").read_text()
        assert "class State:" in content
        # Multi-factor model should have field references for both factors
        assert "Factor0" in content
        assert "Factor1" in content

    def test_synthesize_matrices_constants(self, synth_dir: Path) -> None:
        """Synthesize -> matrices.py contains N_HIDDEN_STATES, A, B, C, D."""
        content = (synth_dir / "matrices.py").read_text()
        assert "N_HIDDEN_STATES" in content
        # matrices.py uses type-annotated assignment: "A: List[..."
        assert "A:" in content or "A =" in content
        assert "B:" in content or "B =" in content
        assert "C:" in content or "C =" in content
        assert "D:" in content or "D =" in content
        assert "likelihood" in content
        assert "transition" in content

    def test_synthesize_matrices_compiles(self, synth_dir: Path) -> None:
        """Synthesize -> matrices.py compiles (ast.parse passes)."""
        content = (synth_dir / "matrices.py").read_text()
        tree = ast.parse(content)
        assert tree is not None

    def test_synthesize_all_files_valid_python(self, synth_dir: Path) -> None:
        """Synthesize -> all .py files are valid Python (compile each)."""
        for py_file in synth_dir.rglob("*.py"):
            content = py_file.read_text()
            try:
                ast.parse(content)
            except SyntaxError as exc:
                pytest.fail(f"{py_file.name} has syntax error: {exc}")

    def test_synthesize_multi_factor_state_fields(self, tmp_path: Path) -> None:
        """Synthesize multi-factor -> >= 2 state fields in State."""
        model = parse_gnn(MULTI_FACTOR_GNN)
        plan = plan_package(model)
        pkg = synthesize_package(plan, model, tmp_path / "multi")
        content = (pkg / "state.py").read_text()
        # Both factors should have their own class
        assert "Factor0" in content
        assert "Factor1" in content
        # State __init__ should reference both factor names
        assert "def __init__" in content


# ===================================================================
# MatrixFunctions (callable) validation (6 tests)
# ===================================================================


class TestMatrixFunctions:
    """MatrixFunctions callable validation."""

    @pytest.fixture()
    def mf(self) -> MatrixFunctions:
        """MatrixFunctions built from multi-factor GNN."""
        model = parse_gnn(MULTI_FACTOR_GNN)
        return MatrixFunctions(model)

    def test_likelihood_length(self, mf: MatrixFunctions) -> None:
        """likelihood([1/n]*n) has len == n_obs."""
        n = mf._n_states
        state_dist = [1.0 / n] * n
        obs = mf.likelihood(state_dist)
        assert len(obs) == mf._n_obs

    def test_transition_sums_to_one(self, mf: MatrixFunctions) -> None:
        """transition(uniform, 0) -> sums to ~1.0."""
        n = mf._n_states
        state_dist = [1.0 / n] * n
        result = mf.transition(state_dist, 0)
        assert abs(sum(result) - 1.0) < 1e-6

    def test_prior_sums_to_one(self, mf: MatrixFunctions) -> None:
        """prior() -> sums to ~1.0."""
        prior = mf.prior()
        assert len(prior) > 0
        assert abs(sum(prior) - 1.0) < 1e-6

    def test_preference_score_returns_float(self, mf: MatrixFunctions) -> None:
        """preference_score returns float."""
        n = mf._n_obs
        obs_dist = [1.0 / n] * n if n > 0 else [1.0]
        score = mf.preference_score(obs_dist)
        assert isinstance(score, float)

    def test_best_action_in_range(self, mf: MatrixFunctions) -> None:
        """best_action returns int in [0, n_actions)."""
        n = mf._n_states
        state_dist = [1.0 / n] * n
        action = mf.best_action(state_dist)
        assert isinstance(action, int)
        assert 0 <= action < mf._n_actions

    def test_efe_is_finite(self, mf: MatrixFunctions) -> None:
        """EFE is finite float."""
        n = mf._n_states
        state_dist = [1.0 / n] * n
        efe = mf.expected_free_energy(state_dist, 0)
        assert isinstance(efe, float)
        assert math.isfinite(efe)


# ===================================================================
# Metrics validation (5 tests)
# ===================================================================


class TestMetrics:
    """Metrics module validation."""

    def test_compare_role_distributions_identical(self) -> None:
        """compare_role_distributions({A:3},{A:3}) -> 1.0."""
        score = compare_role_distributions({"A": 3}, {"A": 3})
        assert score == 1.0

    def test_compare_role_distributions_disjoint(self) -> None:
        """compare_role_distributions({A:3},{B:3}) -> 0.0."""
        score = compare_role_distributions({"A": 3}, {"B": 3})
        assert score == 0.0

    def test_compare_graph_structure_same(self) -> None:
        """compare_graph_structure: same graph -> 1.0."""
        nodes = [{"role": "HIDDEN_STATE"}, {"role": "OBSERVATION"}]
        score = compare_graph_structure(nodes, [], nodes, [])
        assert score == 1.0

    def test_isomorphism_report_fields(self) -> None:
        """IsomorphismReport has expected fields."""
        report = IsomorphismReport()
        assert hasattr(report, "structural_score")
        assert hasattr(report, "role_score")
        assert hasattr(report, "matrix_score")
        assert hasattr(report, "total_score")
        assert hasattr(report, "is_isomorphic")
        assert hasattr(report, "breakdown")

    def test_compute_isomorphism_report_score_in_range(self) -> None:
        """compute_isomorphism_report: returns report with role_match_score in [0,1]."""
        gnn_a = {
            "roles": {"HIDDEN_STATE": 2, "OBSERVATION": 1},
            "matrices": {},
            "nodes": [{"role": "HIDDEN_STATE"}],
            "edges": [],
        }
        gnn_b = {
            "roles": {"HIDDEN_STATE": 2, "OBSERVATION": 1},
            "matrices": {},
            "nodes": [{"role": "HIDDEN_STATE"}],
            "edges": [],
        }
        report = compute_isomorphism_report(gnn_a, gnn_b)
        assert 0.0 <= report.role_score <= 1.0
        assert 0.0 <= report.total_score <= 1.0
        assert report.is_isomorphic is True  # identical inputs
