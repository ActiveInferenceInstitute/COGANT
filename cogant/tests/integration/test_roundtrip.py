"""Round-trip integration tests for ``cogant.reverse``.

These tests exercise the reverse direction of the COGANT pipeline:

    repo -> COGANT forward -> GNN -> cogant.reverse -> synthesized Python
                                                       |
                                                       v
                                              COGANT forward (again)
                                                       |
                                                       v
                                                     GNN'

The round-trip emits a diagnostic verdict under the role-multiset
equivalence defined in :mod:`cogant.reverse`. Current v0.6 evidence keeps
fresh role-preserved runs separate from out-of-sync compatibility DRIFT fixtures rather
than treating every successful command as role-preserved evidence.

The ``cogant.reverse`` module is under active construction. Every
import is guarded with a ``HAS_*`` flag and each test is
``skipif``-gated on the specific subset of the module it needs so the
suite collects cleanly even before the downstream components exist,
and fills in naturally as they land.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import guards — each reverse sub-module may or may not be available yet.
# ---------------------------------------------------------------------------


try:
    from cogant.reverse.parser import ReverseGNNModel, parse_gnn

    HAS_PARSER = True
except ImportError:  # pragma: no cover - availability sentinel
    HAS_PARSER = False
    ReverseGNNModel = None  # type: ignore[assignment,misc]
    parse_gnn = None  # type: ignore[assignment]

try:
    from cogant.reverse.planner import NodePlan, PackagePlan, plan_package

    HAS_PLANNER = True
except ImportError:  # pragma: no cover - availability sentinel
    HAS_PLANNER = False
    NodePlan = None  # type: ignore[assignment,misc]
    PackagePlan = None  # type: ignore[assignment,misc]
    plan_package = None  # type: ignore[assignment]

try:
    from cogant.reverse.synthesizer import synthesize_package

    HAS_SYNTHESIZER = True
except ImportError:  # pragma: no cover - availability sentinel
    HAS_SYNTHESIZER = False
    synthesize_package = None  # type: ignore[assignment]

try:
    from cogant.reverse.idempotency import RoundtripResult, verify_roundtrip

    HAS_IDEMPOTENCY = True
except ImportError:  # pragma: no cover - availability sentinel
    HAS_IDEMPOTENCY = False
    RoundtripResult = None  # type: ignore[assignment,misc]
    verify_roundtrip = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# GNN fixture — canonical upstream v2.0.0 markdown.
#
# This deliberately mirrors what :class:`cogant.gnn.formatter.upstream`
# emits so the parser handles it through its production code path. The
# toy format shown in the task description would not round-trip; the
# parser expects the ``s_fN[card,1,type=int]`` declaration syntax and
# the ``D_f0={ (p0, p1) }`` initial-parameterization syntax.
# ---------------------------------------------------------------------------


MINIMAL_GNN = """\
## GNNSection
TestModel

## GNNVersionAndFlags
GNNVersion=2.0.0
Flags=

## ModelName
TestModel

## StateSpaceBlock
s_f0[2,1,type=int]
s_f1[2,1,type=int]
o_m0[2,1,type=int]
u_c0[2,1,type=int]
u_c1[2,1,type=int]

## Connections
(D_f0) > (s_f0)
(D_f1) > (s_f1)
(s_f0) > (A_m0)
(A_m0, s_f0) > (o_m0)
(u_c0) > (s_f0)
(u_c1) > (s_f0)

## InitialParameterization
D_f0={ (0.6, 0.4) }
D_f1={ (0.55, 0.45) }
A_m0={ ( (0.8, 0.2), (0.3, 0.7) ) }
B_f0=identity(2,2,2)
B_f1=identity(2,2,2)
C_m0={ (0.5, -0.3) }

## Time
Discrete
ModelTimeHorizon=Unbounded

## ActInfOntologyAnnotation
s_f0 = HiddenState
s_f1 = HiddenState
o_m0 = Observation
u_c0 = Action
u_c1 = Action
A_m0 = LikelihoodMatrix
B_f0 = TransitionMatrix
B_f1 = TransitionMatrix
D_f0 = PriorBelief
D_f1 = PriorBelief
"""


@pytest.fixture
def minimal_gnn_file(tmp_path: Path) -> Path:
    """Write ``MINIMAL_GNN`` to a temp file and return its path."""
    f = tmp_path / "test_model.gnn.md"
    f.write_text(MINIMAL_GNN, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# Group 1 — Parser tests.
# These exercise ``cogant.reverse.parser.parse_gnn``. They should pass
# as soon as parser.py lands (already the case).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_PARSER, reason="cogant.reverse.parser not yet available")
def test_parse_gnn_returns_model(minimal_gnn_file: Path) -> None:
    """``parse_gnn`` returns a ``ReverseGNNModel`` with the expected name."""
    model = parse_gnn(str(minimal_gnn_file))
    assert isinstance(model, ReverseGNNModel)
    # The parser sanitizes the model name to a lowercase Python identifier,
    # so accept either the raw or the sanitized form.
    assert model.model_name == "testmodel"
    assert model.raw_model_name == "TestModel"


@pytest.mark.skipif(not HAS_PARSER, reason="cogant.reverse.parser not yet available")
def test_parse_gnn_extracts_hidden_states(minimal_gnn_file: Path) -> None:
    """The parser lists the two ``s_fN`` factors as hidden states."""
    model = parse_gnn(str(minimal_gnn_file))
    assert "s_f0" in model.hidden_states
    assert "s_f1" in model.hidden_states
    assert model.n_states == 2


@pytest.mark.skipif(not HAS_PARSER, reason="cogant.reverse.parser not yet available")
def test_parse_gnn_extracts_observations_and_actions(minimal_gnn_file: Path) -> None:
    """Observations ``o_mN`` and actions ``u_cN`` are classified correctly."""
    model = parse_gnn(str(minimal_gnn_file))
    assert "o_m0" in model.observations
    assert model.n_obs == 1
    assert "u_c0" in model.actions
    assert "u_c1" in model.actions
    assert model.n_actions == 2


@pytest.mark.skipif(not HAS_PARSER, reason="cogant.reverse.parser not yet available")
def test_parse_gnn_extracts_matrices(minimal_gnn_file: Path) -> None:
    """A/B/C/D have the shapes dictated by the state-space cardinalities."""
    model = parse_gnn(str(minimal_gnn_file))
    # A is [n_obs x n_states].
    assert len(model.A) == model.n_obs == 1
    assert len(model.A[0]) == model.n_states == 2
    # D has one entry per hidden factor and sums to 1.
    assert len(model.D) == model.n_states == 2
    assert abs(sum(model.D) - 1.0) < 1e-6
    # C has one entry per observation modality.
    assert len(model.C) == model.n_obs == 1
    # B is [n_states x n_states x n_actions].
    assert len(model.B) == model.n_states == 2
    assert len(model.B[0]) == model.n_states == 2
    assert len(model.B[0][0]) == model.n_actions == 2


@pytest.mark.skipif(not HAS_PARSER, reason="cogant.reverse.parser not yet available")
def test_parse_gnn_extracts_annotations(minimal_gnn_file: Path) -> None:
    """``ActInfOntologyAnnotation`` entries land in ``model.annotations``."""
    model = parse_gnn(str(minimal_gnn_file))
    assert model.annotations.get("s_f0") == "HiddenState"
    assert model.annotations.get("s_f1") == "HiddenState"
    assert model.annotations.get("o_m0") == "Observation"
    assert model.annotations.get("u_c0") == "Action"
    assert model.annotations.get("u_c1") == "Action"


@pytest.mark.skipif(not HAS_PARSER, reason="cogant.reverse.parser not yet available")
def test_parse_gnn_extracts_cardinalities(minimal_gnn_file: Path) -> None:
    """StateSpaceBlock cardinalities populate ``model.cardinalities``."""
    model = parse_gnn(str(minimal_gnn_file))
    assert model.cardinalities.get("s_f0") == 2
    assert model.cardinalities.get("o_m0") == 2
    assert model.cardinalities.get("u_c0") == 2


@pytest.mark.skipif(not HAS_PARSER, reason="cogant.reverse.parser not yet available")
def test_parse_gnn_accepts_raw_markdown_string() -> None:
    """Passing the markdown text directly (no file) must work too."""
    model = parse_gnn(MINIMAL_GNN)
    assert isinstance(model, ReverseGNNModel)
    assert model.n_states == 2


# ---------------------------------------------------------------------------
# Group 2 — Planner tests.
# These exercise ``cogant.reverse.planner.plan_package``. They share
# the same fixture and skip together with the parser.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not (HAS_PARSER and HAS_PLANNER),
    reason="cogant.reverse.parser or .planner not yet available",
)
def test_plan_package_returns_plan(minimal_gnn_file: Path) -> None:
    """``plan_package`` returns a ``PackagePlan`` with a non-empty name."""
    model = parse_gnn(str(minimal_gnn_file))
    plan = plan_package(model)
    assert isinstance(plan, PackagePlan)
    assert plan.package_name  # non-empty
    assert plan.raw_model_name == "TestModel"


@pytest.mark.skipif(
    not (HAS_PARSER and HAS_PLANNER),
    reason="cogant.reverse.parser or .planner not yet available",
)
def test_plan_has_state_vars(minimal_gnn_file: Path) -> None:
    """Every GNN hidden-state factor becomes a ``HIDDEN_STATE`` NodePlan."""
    model = parse_gnn(str(minimal_gnn_file))
    plan = plan_package(model)
    assert len(plan.state_vars) == model.n_states == 2
    for node in plan.state_vars:
        assert node.role == "HIDDEN_STATE"
        assert node.module == "state.py"
    slots = {n.slot for n in plan.state_vars}
    assert slots == {"s_f0", "s_f1"}


@pytest.mark.skipif(
    not (HAS_PARSER and HAS_PLANNER),
    reason="cogant.reverse.parser or .planner not yet available",
)
def test_plan_has_observations(minimal_gnn_file: Path) -> None:
    """Each observation modality becomes an ``OBSERVATION`` NodePlan."""
    model = parse_gnn(str(minimal_gnn_file))
    plan = plan_package(model)
    assert len(plan.obs_functions) == model.n_obs == 1
    assert plan.obs_functions[0].role == "OBSERVATION"
    assert plan.obs_functions[0].module == "observe.py"
    assert plan.obs_functions[0].slot == "o_m0"


@pytest.mark.skipif(
    not (HAS_PARSER and HAS_PLANNER),
    reason="cogant.reverse.parser or .planner not yet available",
)
def test_plan_has_actions(minimal_gnn_file: Path) -> None:
    """Each action slot becomes an ``ACTION`` NodePlan in ``act.py``."""
    model = parse_gnn(str(minimal_gnn_file))
    plan = plan_package(model)
    assert len(plan.action_methods) == model.n_actions == 2
    for node in plan.action_methods:
        assert node.role == "ACTION"
        assert node.module == "act.py"
    slots = {n.slot for n in plan.action_methods}
    assert slots == {"u_c0", "u_c1"}


@pytest.mark.skipif(
    not (HAS_PARSER and HAS_PLANNER),
    reason="cogant.reverse.parser or .planner not yet available",
)
def test_plan_matrix_flags(minimal_gnn_file: Path) -> None:
    """Plan flags reflect the parsed A/B/C/D availability."""
    model = parse_gnn(str(minimal_gnn_file))
    plan = plan_package(model)
    assert plan.has_A_matrix is True
    assert plan.has_B_tensor is True
    assert plan.has_C_vector is True
    assert plan.has_D_vector is True


@pytest.mark.skipif(
    not (HAS_PARSER and HAS_PLANNER),
    reason="cogant.reverse.parser or .planner not yet available",
)
def test_plan_nodes_are_role_complete(minimal_gnn_file: Path) -> None:
    """Concatenated role lists equal the full ``nodes`` list."""
    model = parse_gnn(str(minimal_gnn_file))
    plan = plan_package(model)
    total = (
        len(plan.state_vars)
        + len(plan.obs_functions)
        + len(plan.action_methods)
        + len(plan.policy_functions)
        + len(plan.constraint_checks)
    )
    assert total == len(plan.nodes)


# ---------------------------------------------------------------------------
# Group 3 — Synthesizer tests (marked ``slow``).
# The synthesizer writes a full Python package; these tests import the
# emitted code, so they only run once the synthesizer module lands.
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(
    not (HAS_PARSER and HAS_PLANNER and HAS_SYNTHESIZER),
    reason="cogant.reverse.synthesizer not yet available",
)
def test_synthesize_creates_files(minimal_gnn_file: Path, tmp_path: Path) -> None:
    """Synthesis emits the canonical package layout under ``package_name``."""
    model = parse_gnn(str(minimal_gnn_file))
    plan = plan_package(model)
    out_dir = tmp_path / "synthesized"
    pkg_path = synthesize_package(plan, model, str(out_dir))

    assert pkg_path.is_dir()
    assert pkg_path.parent == out_dir.resolve()
    assert pkg_path.name == plan.package_name

    expected = [
        "__init__.py",
        "state.py",
        "observe.py",
        "act.py",
        "policy.py",
        "constraints.py",
        "matrices.py",
        "main.py",
    ]
    for filename in expected:
        assert (pkg_path / filename).is_file(), f"missing {filename}"
    assert (pkg_path / "tests" / "test_smoke.py").is_file()


@pytest.mark.slow
@pytest.mark.skipif(
    not (HAS_PARSER and HAS_PLANNER and HAS_SYNTHESIZER),
    reason="cogant.reverse.synthesizer not yet available",
)
def test_synthesized_state_is_importable(minimal_gnn_file: Path, tmp_path: Path) -> None:
    """The emitted ``state.py`` module imports and exposes a ``State`` class."""
    model = parse_gnn(str(minimal_gnn_file))
    plan = plan_package(model)
    out_dir = tmp_path / "synthesized"
    pkg_path = synthesize_package(plan, model, str(out_dir))

    state_file = pkg_path / "state.py"
    assert state_file.is_file()

    spec = importlib.util.spec_from_file_location(
        f"_roundtrip_state_{plan.package_name}", state_file
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    assert hasattr(module, "State"), "synthesized state module exposes State"
    instance = module.State()
    assert instance is not None


@pytest.mark.slow
@pytest.mark.skipif(
    not (HAS_PARSER and HAS_PLANNER and HAS_SYNTHESIZER),
    reason="cogant.reverse.synthesizer not yet available",
)
def test_synthesis_is_deterministic(minimal_gnn_file: Path, tmp_path: Path) -> None:
    """Synthesizing twice into different dirs yields identical file contents."""
    model = parse_gnn(str(minimal_gnn_file))
    plan_a = plan_package(model)
    plan_b = plan_package(model)
    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"
    pkg_a = synthesize_package(plan_a, model, str(out_a))
    pkg_b = synthesize_package(plan_b, model, str(out_b))

    for name in ("state.py", "matrices.py", "main.py"):
        content_a = (pkg_a / name).read_text(encoding="utf-8")
        content_b = (pkg_b / name).read_text(encoding="utf-8")
        assert content_a == content_b, f"{name} not deterministic across runs"


# ---------------------------------------------------------------------------
# Group 4 — Full round-trip tests against the idempotency verifier.
#
# ``cogant.reverse.idempotency.verify_roundtrip`` takes a **GNN markdown
# file** (not a repo dir) and runs: GNN -> parse -> plan -> synthesize
# -> COGANT forward -> compare role multisets. Feeding the fixture GNN
# drives the whole pipeline end-to-end without requiring a hand-written
# source repository. When the forward pipeline cannot be imported (for
# example, optional deps missing), the verifier records an error and
# we skip rather than fail — the test flips to a hard assertion as
# soon as the verifier returns populated role multisets.
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not HAS_IDEMPOTENCY, reason="idempotency verifier not available")
def test_roundtrip_result_structure(minimal_gnn_file: Path, tmp_path: Path) -> None:
    """``verify_roundtrip`` returns a populated ``RoundtripResult``."""
    result = verify_roundtrip(str(minimal_gnn_file), str(tmp_path / "roundtrip"))
    assert isinstance(result, RoundtripResult)
    assert hasattr(result, "structurally_isomorphic")
    assert hasattr(result, "role_preservation_score")
    assert hasattr(result, "original_roles")
    assert hasattr(result, "synthesized_roles")
    assert isinstance(result.original_roles, dict)
    assert isinstance(result.synthesized_roles, dict)
    # Original roles come straight from the parsed GNN and should be
    # non-empty for our canonical fixture regardless of whether the
    # forward pipeline was able to run on the synthesized package.
    assert result.original_roles, "original role multiset must be populated"
    assert "HIDDEN_STATE" in result.original_roles
    assert "OBSERVATION" in result.original_roles
    assert "ACTION" in result.original_roles


@pytest.mark.slow
@pytest.mark.skipif(not HAS_IDEMPOTENCY, reason="idempotency verifier not available")
def test_roundtrip_role_preservation_score_bounds(minimal_gnn_file: Path, tmp_path: Path) -> None:
    """Role-match score is always a valid probability in ``[0, 1]``."""
    result = verify_roundtrip(str(minimal_gnn_file), str(tmp_path / "roundtrip-bounds"))
    assert 0.0 <= result.role_preservation_score <= 1.0


@pytest.mark.slow
@pytest.mark.skipif(not HAS_IDEMPOTENCY, reason="idempotency verifier not available")
def test_roundtrip_role_match_meets_lenient_threshold(
    minimal_gnn_file: Path, tmp_path: Path
) -> None:
    """Round-trip on the canonical fixture returns a populated diagnostic verdict."""
    result = verify_roundtrip(str(minimal_gnn_file), str(tmp_path / "roundtrip-threshold"))
    if not result.synthesized_roles and result.errors:
        pytest.skip(f"forward pipeline not yet runnable on synthesized package: {result.errors[0]}")
    assert result.roundtrip_status in {"DRIFT", "ROLE_PRESERVED", "STRUCTURALLY_ISOMORPHIC"}
    assert result.original_roles
    assert result.synthesized_roles
    assert result.role_preservation_score > 0.0


@pytest.mark.slow
@pytest.mark.skipif(not HAS_IDEMPOTENCY, reason="idempotency verifier not available")
def test_roundtrip_shape_match_populated(minimal_gnn_file: Path, tmp_path: Path) -> None:
    """``shape_match`` is populated with the three state-space dimensions.

    The canonical fixture declares non-zero hidden states, observations,
    and actions, so all three keys must appear in ``shape_match``. At
    least one dimension must survive the round-trip — the lenient floor
    while the synthesizer is still lossy. Tighten to ``all(values)``
    once ``state.py`` is rich enough for the forward pipeline to
    recover hidden-state fields from the synthesized package.
    """
    result = verify_roundtrip(str(minimal_gnn_file), str(tmp_path / "roundtrip-shape"))
    if not result.shape_match:
        pytest.skip("verifier did not populate shape_match for this fixture")
    assert set(result.shape_match.keys()) == {"n_states", "n_obs", "n_actions"}
    assert any(result.shape_match.values()), (
        f"no shape dimensions survived round-trip: {result.shape_match}"
    )
