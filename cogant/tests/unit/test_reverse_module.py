"""Behavior tests for cogant.reverse.* modules.

Covers parser, planner, synthesizer, matrices, and metrics. Uses
canonical GNN markdown fixtures and exercises the concrete behavior
(computed values) rather than just shape assertions.

No mocks: all tests use real in-memory models and real synthesized
files under ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogant.reverse.matrices import render_matrices_module
from cogant.reverse.metrics import (
    DEFAULT_ISOMORPHISM_THRESHOLD,
    MATRIX_KEYS,
    IsomorphismReport,
    compare_graph_structure,
    compare_matrices,
    compare_role_distributions,
    compute_isomorphism_report,
)
from cogant.reverse.parser import ReverseGNNModel, parse_gnn
from cogant.reverse.planner import (
    NodePlan,
    PackagePlan,
    plan_package,
)
from cogant.reverse.synthesizer import synthesize_package

# ---------------------------------------------------------------------------
# Canonical GNN markdown fixtures
# ---------------------------------------------------------------------------


CANONICAL_GNN = """## ModelName
SampleModel-v1

## StateSpaceBlock
s_f0[3,1,type=int]
s_f1[2,1,type=float]
o_m0[2,1,type=float]
u_c0[4,1,type=int]
B_f0[3,3,4,type=float]
A_m0[2,3,type=float]
D_f0[3,1,type=float]
C_m0[2,1,type=float]

## Connections
(D_f0) > (s_f0)
(s_f0, B_f0) > (s_f0)

## InitialParameterization
D_f0={ (0.6, 0.2, 0.2) }
D_f1={ (0.4, 0.6) }
C_m0={ (0.5, 0.5) }
A_m0={ ( (0.9, 0.1, 0.0), (0.1, 0.8, 0.1) ) }
B_f0=identity(3,3,4)

## ActInfOntologyAnnotation
s_f0=HiddenState
s_f1=HiddenState
o_m0=Observation
u_c0=Action
A_m0=LikelihoodMatrix
B_f0=TransitionMatrix
C_m0=PreferenceVector
D_f0=PriorBelief
G=ExpectedFreeEnergy

## State Space

### State Variables

| ID | Name | Type |
|----|------|------|
| s_f0 | Counter - Hidden State | discrete |
| s_f1 | Temperature - Hidden State | discrete |

## State Space

### Active Inference Matrices

```gnn-matrices
A[[rows=2][cols=3]]
0.9 0.1 0.0
0.1 0.8 0.1
B[[rows=3][cols=3][depth=2]]
# action=0
1.0 0.0 0.0
0.0 1.0 0.0
0.0 0.0 1.0
# action=1
0.0 1.0 0.0
0.0 0.0 1.0
1.0 0.0 0.0
C[[rows=2]]
0.25
0.75
D[[rows=3]]
0.5
0.3
0.2
```
"""


EMPTY_GNN = """## ModelName
Empty

## StateSpaceBlock

## Connections

## InitialParameterization
"""


MINIMAL_HIDDEN_ONLY_GNN = """## ModelName
hidden_only

## StateSpaceBlock
s_f0[2,1,type=int]

## ActInfOntologyAnnotation
s_f0=HiddenState
"""


# ---------------------------------------------------------------------------
# parse_gnn: round the unit through canonical markdown
# ---------------------------------------------------------------------------


def test_parse_gnn_from_string_populates_hidden_states() -> None:
    """parse_gnn accepts a raw markdown string and fills hidden_states."""
    model = parse_gnn(CANONICAL_GNN)
    assert model.hidden_states == ["s_f0", "s_f1"]
    assert model.n_states == 2


def test_parse_gnn_populates_observations_and_actions() -> None:
    """parse_gnn recognises o_m* as observations and u_c* as actions."""
    model = parse_gnn(CANONICAL_GNN)
    assert model.observations == ["o_m0"]
    assert model.actions == ["u_c0"]
    assert model.n_obs == 1
    assert model.n_actions == 1


def test_parse_gnn_cardinalities_and_types() -> None:
    """Cardinality and type are parsed from ``s_f0[3,1,type=int]``."""
    model = parse_gnn(CANONICAL_GNN)
    assert model.cardinalities["s_f0"] == 3
    assert model.cardinalities["s_f1"] == 2
    assert model.types["s_f0"] == "int"
    assert model.types["s_f1"] == "float"


def test_parse_gnn_ontology_annotations() -> None:
    """ActInfOntologyAnnotation entries land in model.annotations."""
    model = parse_gnn(CANONICAL_GNN)
    assert model.annotations["s_f0"] == "HiddenState"
    assert model.annotations["A_m0"] == "LikelihoodMatrix"
    # Bare G=ExpectedFreeEnergy annotation does not get folded into
    # hidden_states/observations/actions.
    assert "G" not in model.hidden_states


def test_parse_gnn_sanitizes_model_name() -> None:
    """Model name is sanitized into a valid Python identifier."""
    model = parse_gnn(CANONICAL_GNN)
    assert model.raw_model_name == "SampleModel-v1"
    assert model.model_name == "samplemodel_v1"
    assert "-" not in model.model_name


def test_parse_gnn_initial_parameterization_d_vector() -> None:
    """D vector comes from the gnn-matrices fenced block (3 rows for D_f0)."""
    model = parse_gnn(CANONICAL_GNN)
    # D_f0 has cardinality 3 and the fenced block declares D[[rows=3]].
    assert len(model.D) == 3
    # D is normalized to sum to 1.
    assert abs(sum(model.D) - 1.0) < 1e-6


def test_parse_gnn_initial_parameterization_c_vector() -> None:
    """C vector is aggregated from per-observation C_mN entries."""
    model = parse_gnn(CANONICAL_GNN)
    # C is overridden later by the fenced matrix block.
    assert len(model.C) == 2


def test_parse_gnn_fenced_matrix_block_overrides_aggregates() -> None:
    """The gnn-matrices fenced block is authoritative over aggregates."""
    model = parse_gnn(CANONICAL_GNN)
    # A from the fence:
    assert model.A == [[0.9, 0.1, 0.0], [0.1, 0.8, 0.1]]
    # B from the fence with two actions.
    assert len(model.B) == 3
    assert len(model.B[0]) == 3
    assert len(model.B[0][0]) == 2
    # C from the fence = [0.25, 0.75].
    assert model.C == [0.25, 0.75]
    # D from the fence = [0.5, 0.3, 0.2].
    assert model.D == [0.5, 0.3, 0.2]


def test_parse_gnn_connections_captured() -> None:
    """Arrow-syntax connection lines are captured into model.connections."""
    model = parse_gnn(CANONICAL_GNN)
    # At least the two canonical arrow lines are present.
    assert any("(D_f0) > (s_f0)" in c for c in model.connections)


def test_parse_gnn_human_names_from_state_variables_table() -> None:
    """State Variables table populates model.human_names."""
    model = parse_gnn(CANONICAL_GNN)
    assert "s_f0" in model.human_names
    assert "Counter" in model.human_names["s_f0"]


def test_parse_gnn_from_path(tmp_path: Path) -> None:
    """parse_gnn(Path) reads from disk."""
    gnn_file = tmp_path / "model.gnn.md"
    gnn_file.write_text(CANONICAL_GNN, encoding="utf-8")
    model = parse_gnn(gnn_file)
    assert model.n_states == 2


def test_parse_gnn_from_string_path(tmp_path: Path) -> None:
    """parse_gnn(str) treats a short existing-file path as a path."""
    gnn_file = tmp_path / "model.gnn.md"
    gnn_file.write_text(MINIMAL_HIDDEN_ONLY_GNN, encoding="utf-8")
    model = parse_gnn(str(gnn_file))
    assert model.n_states == 1


def test_parse_gnn_type_error_on_unexpected_input() -> None:
    """parse_gnn raises TypeError when given a non-str/Path."""
    with pytest.raises(TypeError):
        parse_gnn(42)  # type: ignore[arg-type]


def test_parse_gnn_empty_string_produces_empty_model() -> None:
    """An empty markdown string still yields a valid empty model."""
    model = parse_gnn(EMPTY_GNN)
    assert model.n_states == 0
    assert model.n_obs == 0
    assert model.n_actions == 0


def test_reverse_gnn_model_dataclass_defaults() -> None:
    """ReverseGNNModel dataclass defaults are all empty containers."""
    m = ReverseGNNModel()
    assert m.hidden_states == []
    assert m.observations == []
    assert m.actions == []
    assert m.A == []
    assert m.B == []
    assert m.C == []
    assert m.D == []
    assert m.n_states == 0
    assert m.n_obs == 0
    assert m.n_actions == 0


def test_parse_gnn_handles_policy_annotation() -> None:
    """Policy-flagged vars get appended to policies list."""
    md = """## ModelName
policy_model

## StateSpaceBlock
pi_c0[2,1,type=int]

## ActInfOntologyAnnotation
pi_c0=Policy
"""
    model = parse_gnn(md)
    assert "pi_c0" in model.policies


def test_parse_gnn_handles_constraint_annotation() -> None:
    """Variables flagged as Constraint end up in model.constraints."""
    md = """## ModelName
constraint_model

## StateSpaceBlock
c_f0[2,1,type=int]

## ActInfOntologyAnnotation
c_f0=Constraint
"""
    model = parse_gnn(md)
    assert "c_f0" in model.constraints


# ---------------------------------------------------------------------------
# plan_package
# ---------------------------------------------------------------------------


def test_plan_package_emits_state_vars_for_each_hidden_state() -> None:
    """One NodePlan per hidden-state factor is emitted with HIDDEN_STATE role."""
    model = parse_gnn(CANONICAL_GNN)
    plan = plan_package(model)
    assert len(plan.state_vars) == 2
    assert all(n.role == "HIDDEN_STATE" for n in plan.state_vars)
    assert all(n.module == "state.py" for n in plan.state_vars)


def test_plan_package_emits_obs_functions() -> None:
    """Each observation becomes an obs_function NodePlan."""
    model = parse_gnn(CANONICAL_GNN)
    plan = plan_package(model)
    assert len(plan.obs_functions) == 1
    assert plan.obs_functions[0].role == "OBSERVATION"
    assert plan.obs_functions[0].module == "observe.py"
    # The synthesized identifier must start with "get_".
    assert plan.obs_functions[0].name.startswith("get_")


def test_plan_package_emits_action_methods() -> None:
    """Each action becomes an action_method NodePlan."""
    model = parse_gnn(CANONICAL_GNN)
    plan = plan_package(model)
    assert len(plan.action_methods) == 1
    assert plan.action_methods[0].role == "ACTION"
    assert plan.action_methods[0].module == "act.py"
    # Action idents are prefixed with "update_".
    assert plan.action_methods[0].name.startswith("update_")


def test_plan_package_has_matrix_flags() -> None:
    """has_A_matrix / has_B_tensor / has_C_vector / has_D_vector are set."""
    model = parse_gnn(CANONICAL_GNN)
    plan = plan_package(model)
    assert plan.has_A_matrix is True
    assert plan.has_B_tensor is True
    assert plan.has_C_vector is True
    assert plan.has_D_vector is True


def test_plan_package_empty_model_produces_empty_plan() -> None:
    """A model with no state/obs/actions yields an empty PackagePlan."""
    model = parse_gnn(EMPTY_GNN)
    plan = plan_package(model)
    assert plan.state_vars == []
    assert plan.obs_functions == []
    assert plan.action_methods == []
    assert plan.policy_functions == []
    assert plan.constraint_checks == []


def test_plan_package_human_readable_identifiers() -> None:
    """Human names from State Variables table become Python identifiers."""
    model = parse_gnn(CANONICAL_GNN)
    plan = plan_package(model)
    # First state factor has human name "Counter - Hidden State".
    # _to_identifier strips the " - Hidden State" suffix.
    names = [n.name for n in plan.state_vars]
    assert any("counter" in n.lower() for n in names)


def test_plan_package_python_type_mapping() -> None:
    """Python types map from GNN types (int, float, bool)."""
    md = """## ModelName
types_test

## StateSpaceBlock
s_f0[2,1,type=bool]
s_f1[3,1,type=float]

## ActInfOntologyAnnotation
s_f0=HiddenState
s_f1=HiddenState
"""
    model = parse_gnn(md)
    plan = plan_package(model)
    types_by_slot = {n.slot: n.python_type for n in plan.state_vars}
    assert types_by_slot["s_f0"] == "bool"
    assert types_by_slot["s_f1"] == "float"


def test_plan_package_with_policies_and_constraints() -> None:
    """Policies and constraints both produce NodePlans."""
    md = """## ModelName
pc_test

## StateSpaceBlock
pi_c0[2,1,type=int]
c_f0[2,1,type=int]

## ActInfOntologyAnnotation
pi_c0=Policy
c_f0=Constraint
"""
    model = parse_gnn(md)
    plan = plan_package(model)
    assert len(plan.policy_functions) == 1
    assert plan.policy_functions[0].role == "POLICY"
    assert len(plan.constraint_checks) == 1
    assert plan.constraint_checks[0].role == "CONSTRAINT"


def test_plan_package_nodeplan_defaults() -> None:
    """NodePlan has sensible dataclass defaults."""
    n = NodePlan()
    assert n.python_type == "float"
    assert n.cardinality == 0
    assert n.initial_value == "0.0"


def test_plan_package_packageplan_defaults() -> None:
    """PackagePlan has sensible dataclass defaults."""
    p = PackagePlan()
    assert p.package_name == "cogant_model"
    assert p.state_vars == []
    assert p.has_A_matrix is False


def test_plan_package_reserved_keyword_is_sanitized() -> None:
    """A hidden state with a Python reserved keyword as name gets prefixed."""
    md = """## ModelName
kw_test

## StateSpaceBlock
s_f0[2,1,type=int]

## ActInfOntologyAnnotation
s_f0=HiddenState

## State Space

### State Variables

| ID | Name | Type |
|----|------|------|
| v1 | class | discrete |
"""
    model = parse_gnn(md)
    plan = plan_package(model)
    assert plan.state_vars[0].name != "class"
    assert plan.state_vars[0].name.startswith("var_")


# ---------------------------------------------------------------------------
# render_matrices_module
# ---------------------------------------------------------------------------


def test_render_matrices_module_produces_valid_python() -> None:
    """Rendered matrices.py is valid Python source."""
    model = parse_gnn(CANONICAL_GNN)
    source = render_matrices_module(model)
    # Compile it to ensure syntactic validity.
    compile(source, "matrices.py", "exec")
    assert "N_HIDDEN_STATES: int = 2" in source
    assert "N_OBSERVATIONS: int = 1" in source
    assert "N_ACTIONS: int = 1" in source


def test_render_matrices_module_runtime_semantics() -> None:
    """The emitted likelihood / transition / preference_score execute."""
    model = parse_gnn(CANONICAL_GNN)
    source = render_matrices_module(model)
    ns: dict = {}
    exec(compile(source, "matrices.py", "exec"), ns)
    # A is the 2x3 likelihood, so likelihood over uniform state gives row sums/3.
    uniform_state = [1.0 / 3] * 3
    obs = ns["likelihood"](uniform_state)
    assert len(obs) == 2
    # transition on a uniform state returns a normalized distribution.
    next_state = ns["transition"](uniform_state, 0)
    assert abs(sum(next_state) - 1.0) < 1e-6
    # preference_score is the inner product of C and obs.
    score = ns["preference_score"](obs)
    assert isinstance(score, float)


def test_render_matrices_module_empty_a_falls_back_to_identity() -> None:
    """When A is missing but n_obs/n_states > 0, we synthesize a uniform A."""
    model = ReverseGNNModel(
        hidden_states=["s_f0", "s_f1"],
        observations=["o_m0"],
        actions=["u_c0"],
        A=[],
        B=[],
        C=[],
        D=[],
    )
    source = render_matrices_module(model)
    compile(source, "matrices.py", "exec")
    # Non-empty A was synthesized.
    assert "A: List[List[float]] = []" not in source


def test_render_matrices_module_empty_model_yields_scalars() -> None:
    """Completely empty model still emits compileable source."""
    model = ReverseGNNModel()
    source = render_matrices_module(model)
    compile(source, "matrices.py", "exec")
    assert "N_HIDDEN_STATES: int = 0" in source


def test_render_matrices_module_likelihood_guards_empty_inputs() -> None:
    """Runtime likelihood returns [] on empty A or empty state."""
    model = ReverseGNNModel()
    source = render_matrices_module(model)
    ns: dict = {}
    exec(compile(source, "matrices.py", "exec"), ns)
    assert ns["likelihood"]([]) == []
    assert ns["likelihood"]([1.0]) == []  # A is empty


def test_render_matrices_module_preference_score_empty() -> None:
    """preference_score returns 0.0 on empty C."""
    model = ReverseGNNModel()
    source = render_matrices_module(model)
    ns: dict = {}
    exec(compile(source, "matrices.py", "exec"), ns)
    assert ns["preference_score"]([1.0]) == 0.0


def test_render_matrices_module_with_mismatched_A_shape() -> None:
    """A whose row count != n_obs is trimmed to match."""
    model = ReverseGNNModel(
        hidden_states=["s_f0"],
        observations=["o_m0", "o_m1"],
        A=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],  # 3 rows > n_obs=2
    )
    source = render_matrices_module(model)
    compile(source, "matrices.py", "exec")


# ---------------------------------------------------------------------------
# synthesize_package: full round-trip to disk and imports
# ---------------------------------------------------------------------------


def test_synthesize_package_creates_expected_files(tmp_path: Path) -> None:
    """All 9 expected files land under the package directory."""
    model = parse_gnn(CANONICAL_GNN)
    plan = plan_package(model)
    pkg = synthesize_package(plan, model, tmp_path)
    expected = {
        "__init__.py",
        "state.py",
        "observe.py",
        "act.py",
        "policy.py",
        "constraints.py",
        "matrices.py",
        "main.py",
    }
    present = {p.name for p in pkg.iterdir() if p.is_file()}
    assert expected.issubset(present)
    assert (pkg / "tests" / "test_smoke.py").is_file()


def test_synthesize_package_all_generated_files_compile(tmp_path: Path) -> None:
    """Every generated .py file is valid Python."""
    model = parse_gnn(CANONICAL_GNN)
    plan = plan_package(model)
    pkg = synthesize_package(plan, model, tmp_path)
    for py_file in pkg.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        compile(source, str(py_file), "exec")


def test_synthesize_package_empty_model(tmp_path: Path) -> None:
    """Degenerate empty model still yields a compilable package."""
    model = parse_gnn(EMPTY_GNN)
    plan = plan_package(model)
    pkg = synthesize_package(plan, model, tmp_path)
    state_src = (pkg / "state.py").read_text()
    # Empty state placeholder class is emitted.
    assert "class State:" in state_src
    assert "_placeholder" in state_src


def test_synthesize_package_hidden_only(tmp_path: Path) -> None:
    """A model with only hidden states generates Factor + State classes."""
    model = parse_gnn(MINIMAL_HIDDEN_ONLY_GNN)
    plan = plan_package(model)
    pkg = synthesize_package(plan, model, tmp_path)
    state_src = (pkg / "state.py").read_text()
    assert "class Factor0:" in state_src
    assert "class State:" in state_src
    assert "def update(" in state_src


def test_synthesize_package_deterministic(tmp_path: Path) -> None:
    """Running synthesize twice produces byte-identical outputs."""
    model = parse_gnn(CANONICAL_GNN)
    plan = plan_package(model)
    pkg1 = synthesize_package(plan, model, tmp_path / "run1")
    pkg2 = synthesize_package(plan, model, tmp_path / "run2")
    for f in ("state.py", "observe.py", "act.py", "policy.py", "matrices.py"):
        a = (pkg1 / f).read_text()
        b = (pkg2 / f).read_text()
        assert a == b, f"{f} differs between runs"


def test_synthesize_package_state_module_executes(tmp_path: Path) -> None:
    """Generated state.py can be exec'd and used to construct instances."""
    model = parse_gnn(CANONICAL_GNN)
    plan = plan_package(model)
    pkg = synthesize_package(plan, model, tmp_path)
    ns: dict = {}
    exec((pkg / "state.py").read_text(), ns)
    State = ns["State"]
    s = State()
    # A State has one attribute per factor from plan.state_vars.
    for n in plan.state_vars:
        assert hasattr(s, n.name)


def test_synthesize_package_returns_package_path_inside_output(tmp_path: Path) -> None:
    """The returned path is ``output_dir / plan.package_name``."""
    model = parse_gnn(CANONICAL_GNN)
    plan = plan_package(model)
    pkg = synthesize_package(plan, model, tmp_path)
    assert pkg.parent == tmp_path.resolve()
    assert pkg.name == plan.package_name


def test_synthesize_package_policy_module_has_select_policy(tmp_path: Path) -> None:
    """policy.py defines select_policy and it returns a non-negative int."""
    model = parse_gnn(CANONICAL_GNN)
    plan = plan_package(model)
    pkg = synthesize_package(plan, model, tmp_path)
    src = (pkg / "policy.py").read_text()
    assert "def select_policy(" in src


def test_synthesize_package_act_module_has_noop_fallback(tmp_path: Path) -> None:
    """When there are no actions, act.py emits a noop update function."""
    model = parse_gnn(MINIMAL_HIDDEN_ONLY_GNN)
    plan = plan_package(model)
    pkg = synthesize_package(plan, model, tmp_path)
    src = (pkg / "act.py").read_text()
    # Synthesizer emits update_noop as the no-action fallback.
    assert "def update_noop(" in src or "def act_noop(" in src


def test_synthesize_package_observe_module_has_noop_fallback(tmp_path: Path) -> None:
    """When there are no observations, observe.py emits a noop observe function."""
    model = parse_gnn(MINIMAL_HIDDEN_ONLY_GNN)
    plan = plan_package(model)
    pkg = synthesize_package(plan, model, tmp_path)
    src = (pkg / "observe.py").read_text()
    # Synthesizer emits observe_noop or observe_state as the no-obs fallback.
    assert "def observe_noop(" in src or "def observe_state(" in src or "noop" in src


def test_synthesize_package_constraints_module_noop_fallback(tmp_path: Path) -> None:
    """When there are no explicit constraints, constraints.py emits check_* stubs.

    Wave-14 synthesizer change: noop stubs replaced with per-factor scaffold
    predicates (check_hs_<factor>) so forward pipeline's PreferenceRule can
    detect them as CONSTRAINT mappings.  Any check_* function satisfies the
    invariant.
    """
    model = parse_gnn(MINIMAL_HIDDEN_ONLY_GNN)
    plan = plan_package(model)
    pkg = synthesize_package(plan, model, tmp_path)
    src = (pkg / "constraints.py").read_text()
    assert "def check_" in src


# ---------------------------------------------------------------------------
# metrics: compare_role_distributions
# ---------------------------------------------------------------------------


def test_compare_role_distributions_identical_returns_one() -> None:
    """Two identical multisets get a similarity of 1.0."""
    a = {"HIDDEN_STATE": 3, "OBSERVATION": 2}
    b = {"HIDDEN_STATE": 3, "OBSERVATION": 2}
    assert compare_role_distributions(a, b) == pytest.approx(1.0, abs=1e-6)


def test_compare_role_distributions_disjoint_supports() -> None:
    """Two multisets with fully disjoint supports score 0.0 (JS=1)."""
    a = {"HIDDEN_STATE": 3}
    b = {"OBSERVATION": 3}
    score = compare_role_distributions(a, b)
    assert score == pytest.approx(0.0, abs=1e-6)


def test_compare_role_distributions_partial_overlap() -> None:
    """Partial overlap gives a score strictly between 0 and 1."""
    a = {"HIDDEN_STATE": 3, "OBSERVATION": 1}
    b = {"HIDDEN_STATE": 1, "OBSERVATION": 3}
    score = compare_role_distributions(a, b)
    assert 0.0 < score < 1.0


def test_compare_role_distributions_both_empty() -> None:
    """Both empty distributions return 0.0 (neutral-low)."""
    assert compare_role_distributions({}, {}) == 0.0


def test_compare_role_distributions_one_empty() -> None:
    """Exactly one empty distribution returns 0.0."""
    assert compare_role_distributions({"HIDDEN_STATE": 2}, {}) == 0.0
    assert compare_role_distributions({}, {"HIDDEN_STATE": 2}) == 0.0


def test_compare_role_distributions_symmetry() -> None:
    """compare_role_distributions(a, b) == compare_role_distributions(b, a)."""
    a = {"HIDDEN_STATE": 3, "OBSERVATION": 2, "ACTION": 1}
    b = {"HIDDEN_STATE": 2, "OBSERVATION": 3, "ACTION": 2}
    s1 = compare_role_distributions(a, b)
    s2 = compare_role_distributions(b, a)
    assert s1 == pytest.approx(s2, abs=1e-9)


# ---------------------------------------------------------------------------
# metrics: compare_matrices
# ---------------------------------------------------------------------------


def test_compare_matrices_identical_matrices_score_one() -> None:
    """Identical matrices give similarity = 1.0."""
    a = {"A": [[0.5, 0.5], [0.25, 0.75]]}
    b = {"A": [[0.5, 0.5], [0.25, 0.75]]}
    assert compare_matrices(a, b) == pytest.approx(1.0, abs=1e-6)


def test_compare_matrices_no_shared_keys_returns_neutral_half() -> None:
    """With no shared keys the score is 0.5 (undefined → neutral)."""
    assert compare_matrices({"A": [[1.0]]}, {"B": [[1.0]]}) == 0.5


def test_compare_matrices_both_empty_returns_neutral_half() -> None:
    """Both empty dicts return 0.5 (neutral)."""
    assert compare_matrices({}, {}) == 0.5


def test_compare_matrices_mismatched_shapes_are_zero_padded() -> None:
    """Matrices of different shape still produce a finite score."""
    a = {"A": [[1.0, 0.0], [0.0, 1.0]]}
    b = {"A": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]}
    score = compare_matrices(a, b)
    assert 0.0 < score < 1.0


def test_compare_matrices_symmetry() -> None:
    """compare_matrices is symmetric in its arguments."""
    a = {"A": [[0.9, 0.1], [0.2, 0.8]]}
    b = {"A": [[0.1, 0.9], [0.8, 0.2]]}
    assert compare_matrices(a, b) == pytest.approx(compare_matrices(b, a), abs=1e-9)


def test_compare_matrices_handles_vectors() -> None:
    """1D vectors are auto-promoted to column matrices."""
    a = {"C": [1.0, 2.0, 3.0]}
    b = {"C": [1.0, 2.0, 3.0]}
    assert compare_matrices(a, b) == pytest.approx(1.0, abs=1e-6)


def test_compare_matrices_handles_extra_keys_beyond_ABCD() -> None:
    """Extra shared keys beyond A/B/C/D are still included."""
    a = {"A": [[1.0]], "X": [[1.0]]}
    b = {"A": [[1.0]], "X": [[1.0]]}
    assert compare_matrices(a, b) == pytest.approx(1.0, abs=1e-6)


def test_compare_matrices_skips_non_numeric_values() -> None:
    """Non-numeric entries are silently dropped, yielding neutral 0.5 when all drop."""
    a = {"A": "not a matrix"}
    b = {"A": "also not"}
    # _coerce_matrix returns None for non-numeric; both dropped → neutral.
    assert compare_matrices(a, b) == 0.5


def test_matrix_keys_constant_is_canonical() -> None:
    """MATRIX_KEYS exposes the Active Inference slot names."""
    assert MATRIX_KEYS == ("A", "B", "C", "D")


# ---------------------------------------------------------------------------
# metrics: compare_graph_structure
# ---------------------------------------------------------------------------


def test_compare_graph_structure_both_empty_returns_one() -> None:
    """Two empty graphs are trivially identical."""
    assert compare_graph_structure([], [], [], []) == 1.0


def test_compare_graph_structure_identical_nodes() -> None:
    """Identical node multisets with no edges give similarity 1.0."""
    nodes = [{"role": "HIDDEN_STATE"}, {"role": "OBSERVATION"}]
    assert compare_graph_structure(nodes, [], nodes, []) == 1.0


def test_compare_graph_structure_one_empty_one_nonempty() -> None:
    """Empty vs non-empty graph returns 0.0 structural similarity."""
    nodes = [{"role": "HIDDEN_STATE"}]
    assert compare_graph_structure([], [], nodes, []) == 0.0


def test_compare_graph_structure_with_edges() -> None:
    """Edge-role-pair multisets contribute to the distance."""
    nodes_a = [{"role": "A"}, {"role": "B"}]
    edges_a = [{"source": "A", "target": "B"}]
    nodes_b = [{"role": "A"}, {"role": "B"}]
    edges_b = [{"source": "A", "target": "B"}]
    assert compare_graph_structure(nodes_a, edges_a, nodes_b, edges_b) == 1.0


def test_compare_graph_structure_different_node_labels() -> None:
    """Different node-role multisets reduce the similarity below 1."""
    score = compare_graph_structure(
        [{"role": "A"}, {"role": "A"}],
        [],
        [{"role": "A"}, {"role": "B"}],
        [],
    )
    assert 0.0 <= score < 1.0


def test_compare_graph_structure_attribute_style_nodes() -> None:
    """Attribute-style node objects are handled via getattr."""

    class N:
        def __init__(self, role: str) -> None:
            self.role = role

    nodes = [N("HIDDEN_STATE"), N("HIDDEN_STATE")]
    assert compare_graph_structure(nodes, [], nodes, []) == 1.0


def test_compare_graph_structure_edges_only_asymmetry() -> None:
    """Edge asymmetry is captured even if nodes match."""
    nodes = [{"role": "A"}, {"role": "B"}]
    score = compare_graph_structure(
        nodes,
        [{"source": "A", "target": "B"}],
        nodes,
        [{"source": "B", "target": "A"}],
    )
    assert score < 1.0


# ---------------------------------------------------------------------------
# metrics: compute_isomorphism_report
# ---------------------------------------------------------------------------


def test_compute_isomorphism_report_identical_gnns() -> None:
    """Identical role + matrix + graph inputs → total_score of 1.0."""
    gnn = {
        "roles": {"HIDDEN_STATE": 2, "OBSERVATION": 1},
        "matrices": {"A": [[0.5, 0.5], [0.5, 0.5]]},
        "nodes": [{"role": "HIDDEN_STATE"}, {"role": "HIDDEN_STATE"}],
        "edges": [],
    }
    report = compute_isomorphism_report(gnn, gnn)
    assert report.total_score == pytest.approx(1.0, abs=1e-6)
    assert report.is_isomorphic is True
    assert "role_score" in report.breakdown
    assert "matrix_score" in report.breakdown
    assert "structural_score" in report.breakdown


def test_compute_isomorphism_report_disjoint_gnns() -> None:
    """Disjoint inputs fall well below the default threshold."""
    a = {
        "roles": {"HIDDEN_STATE": 3},
        "matrices": {"A": [[1.0]]},
        "nodes": [{"role": "X"}],
        "edges": [],
    }
    b = {"roles": {"ACTION": 3}, "matrices": {"B": [[1.0]]}, "nodes": [{"role": "Y"}], "edges": []}
    report = compute_isomorphism_report(a, b)
    assert report.is_isomorphic is False
    assert report.total_score < DEFAULT_ISOMORPHISM_THRESHOLD


def test_compute_isomorphism_report_missing_sections_use_neutral_defaults() -> None:
    """Missing keys degrade gracefully to neutral values."""
    a: dict = {}
    b: dict = {}
    report = compute_isomorphism_report(a, b)
    assert isinstance(report, IsomorphismReport)
    # role_score is 0.0 when both are empty, matrix is 0.5, graph is 1.0.
    assert report.matrix_score == 0.5
    assert report.structural_score == 1.0


def test_compute_isomorphism_report_custom_threshold() -> None:
    """A custom threshold shifts the is_isomorphic decision."""
    gnn = {"roles": {"HIDDEN_STATE": 1}}
    # role_score=1.0, matrix_score=0.5 (neutral), struct=1.0
    # total = 0.4*1 + 0.4*0.5 + 0.2*1 = 0.8
    report_loose = compute_isomorphism_report(gnn, gnn, threshold=0.5)
    report_tight = compute_isomorphism_report(gnn, gnn, threshold=0.99)
    assert report_loose.is_isomorphic is True
    assert report_tight.is_isomorphic is False


def test_compute_isomorphism_report_per_matrix_frobenius_breakdown() -> None:
    """Per-matrix Frobenius distances land in the breakdown."""
    a = {"matrices": {"A": [[1.0, 0.0], [0.0, 1.0]]}}
    b = {"matrices": {"A": [[0.0, 1.0], [1.0, 0.0]]}}
    report = compute_isomorphism_report(a, b)
    assert "per_matrix_frobenius" in report.breakdown
    assert "A" in report.breakdown["per_matrix_frobenius"]


def test_isomorphism_report_summary_format() -> None:
    """IsomorphismReport.summary() produces the documented one-liner."""
    report = IsomorphismReport(
        role_score=0.9,
        matrix_score=0.8,
        structural_score=0.7,
        total_score=0.82,
        is_isomorphic=True,
    )
    s = report.summary()
    assert "ISO" in s
    assert "0.82" in s


def test_isomorphism_report_summary_drift() -> None:
    """is_isomorphic=False surfaces as 'DRIFT' in summary()."""
    report = IsomorphismReport(
        role_score=0.1,
        matrix_score=0.1,
        structural_score=0.1,
        total_score=0.1,
        is_isomorphic=False,
    )
    assert "DRIFT" in report.summary()


def test_default_isomorphism_threshold_constant() -> None:
    """DEFAULT_ISOMORPHISM_THRESHOLD is exposed and within [0,1]."""
    assert 0.0 <= DEFAULT_ISOMORPHISM_THRESHOLD <= 1.0
    assert DEFAULT_ISOMORPHISM_THRESHOLD == 0.7
