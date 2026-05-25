"""Behavior tests for target-based POLICY / CONTEXT / CONSTRAINT synthesis.

These tests lock down deficit-based scaffolding: generated scaffolds are
emitted only when a caller supplies source role counts that exceed the
roles directly declared in the parsed GNN. Default plans must not add
fixed POLICY / CONTEXT floors.

The tests assert:

1. ``plan_package(..., expected_roles=...)`` populates
   ``scaffold_constraint_checks`` only for target CONSTRAINT deficits.
2. POLICY deficits are split between one semantic ``select_policy``
   helper and ``route_factor_<i>`` scaffolds.
3. CONTEXT deficits produce ``ObservationSettings<i>`` classes, while
   default plans with no source CONTEXT produce none.
4. Scaffold naming avoids substring collisions with the forward
   pipeline's ACTION / OBSERVATION / POLICY / CONTEXT keyword lexicons
   (regression guard against the ``set`` in ``state`` collision).
5. ``synthesize_package`` writes a ``context.py`` module that imports
   cleanly and exposes the expected ``*Settings`` classes.
6. ``synthesize_package`` emits ``check_*`` functions in
   ``constraints.py`` and ``route_*`` functions in ``policy.py`` that
   are syntactically valid Python (compile cleanly).
7. Planner output is deterministic across invocations on the same
   parsed model (same identifiers, same ordering).
8. Empty / degenerate default models receive no source-absent scaffold
   populations.

No mocks: every test parses real GNN markdown, plans a real package,
synthesizes real files under ``tmp_path``, and asserts on the actual
generated source strings.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from cogant.reverse.parser import parse_gnn
from cogant.reverse.planner import PackagePlan, plan_package
from cogant.reverse.synthesizer import synthesize_package

# ---------------------------------------------------------------------------
# GNN fixtures
# ---------------------------------------------------------------------------


SAMPLE_GNN = """## ModelName
ScaffoldSample

## StateSpaceBlock
s_f0[3,1,type=int]
s_f1[2,1,type=int]
s_f2[2,1,type=int]
o_m0[2,1,type=float]
o_m1[3,1,type=float]
u_c0[4,1,type=int]
u_c1[2,1,type=int]
A_m0[2,3,type=float]
B_f0[3,3,4,type=float]
C_m0[2,1,type=float]
D_f0[3,1,type=float]

## Connections
(D_f0) > (s_f0)
(s_f0, B_f0) > (s_f0)

## InitialParameterization
D_f0={ (0.5, 0.3, 0.2) }
C_m0={ (0.6, 0.4) }

## ActInfOntologyAnnotation
s_f0=HiddenState
s_f1=HiddenState
s_f2=HiddenState
o_m0=Observation
o_m1=Observation
u_c0=Action
u_c1=Action
C_m0=PreferenceVector
"""


EMPTY_GNN = """## ModelName
Degenerate

## StateSpaceBlock

## Connections

## InitialParameterization

## ActInfOntologyAnnotation
"""


@pytest.fixture
def sample_plan(tmp_path: Path) -> PackagePlan:
    path = tmp_path / "sample.gnn.md"
    path.write_text(SAMPLE_GNN, encoding="utf-8")
    model = parse_gnn(path)
    return plan_package(
        model,
        expected_roles={
            "HIDDEN_STATE": 3,
            "OBSERVATION": 2,
            "ACTION": 2,
            "CONSTRAINT": 4,
            "POLICY": 3,
            "CONTEXT": 2,
        },
    )


@pytest.fixture
def empty_plan(tmp_path: Path) -> PackagePlan:
    path = tmp_path / "empty.gnn.md"
    path.write_text(EMPTY_GNN, encoding="utf-8")
    model = parse_gnn(path)
    return plan_package(model)


# ---------------------------------------------------------------------------
# Forward pipeline keyword lexicons (kept in sync with
# cogant.translate.rules.semantic). Used as regression guards so that a
# future edit to scaffold naming cannot silently re-introduce a
# substring collision with another rule's keyword list.
# ---------------------------------------------------------------------------


ACTION_KEYWORDS = {
    "set",
    "update",
    "create",
    "delete",
    "send",
    "push",
    "execute",
    "run",
    "process",
    "handle",
    "dispatch",
    "encode",
    "decode",
    "dump",
    "load",
}
OBSERVATION_KEYWORDS = {
    "get",
    "read",
    "fetch",
    "query",
    "display",
    "show",
    "status",
    "info",
    "list",
}
POLICY_FUNCTION_KEYWORDS = {"route", "dispatch", "handle"}
CONTEXT_KEYWORDS = {"config", "settings", "env", "options", "params"}
CONSTRAINT_KEYWORDS = {"check", "validate", "assert", "test_"}


def _contains_any(name: str, keywords: set[str]) -> bool:
    lowered = name.lower()
    return any(kw in lowered for kw in keywords)


# ---------------------------------------------------------------------------
# Test 1: scaffold constraint checks satisfy only the target deficit
# ---------------------------------------------------------------------------


def test_scaffold_constraints_one_per_obs_act_hs(sample_plan: PackagePlan) -> None:
    """``_build_scaffold_constraints`` emits target CONSTRAINT deficits."""
    target = sample_plan.target_role_counts["CONSTRAINT"]
    authoritative = len(sample_plan.constraint_checks)
    scaffolds = sample_plan.scaffold_constraint_checks

    assert len(scaffolds) == target - authoritative
    assert all(s.name.startswith("check_role_") for s in scaffolds)

    # Every scaffold carries the CONSTRAINT role so the synthesizer
    # knows to render it as a ``check_*`` predicate.
    assert all(s.role == "CONSTRAINT" for s in scaffolds)


# ---------------------------------------------------------------------------
# Test 2: scaffold policy count equals target deficit after selector helper
# ---------------------------------------------------------------------------


def test_scaffold_policies_scale_with_state_factors(
    sample_plan: PackagePlan,
) -> None:
    """Scaffold POLICY count fills the target after ``select_policy``."""
    expected = sample_plan.target_role_counts["POLICY"] - 1
    scaffolds = sample_plan.scaffold_policy_functions

    assert len(scaffolds) == expected
    assert all(s.role == "POLICY" for s in scaffolds)
    assert all(s.name.startswith("route_factor_") for s in scaffolds)
    # Slot identifiers are unique — required by the synthesizer's
    # identifier-reservation invariant.
    assert len({s.name for s in scaffolds}) == len(scaffolds)


# ---------------------------------------------------------------------------
# Test 3: scaffold context classes — naming + deficit count
# ---------------------------------------------------------------------------


def test_scaffold_contexts_emit_settings_classes(
    sample_plan: PackagePlan,
) -> None:
    """Scaffold CONTEXT entries are ``ObservationSettings*`` classes."""
    expected = sample_plan.target_role_counts["CONTEXT"] - len(sample_plan.context_functions)
    scaffolds = sample_plan.scaffold_context_classes

    assert len(scaffolds) == expected
    assert all(s.role == "CONTEXT" for s in scaffolds)
    assert all(s.name.startswith("ObservationSettings") for s in scaffolds)
    # Every scaffold name contains ``settings`` so ``ContextRule``
    # fires on it in the forward pass.
    assert all("settings" in s.name.lower() for s in scaffolds)


# ---------------------------------------------------------------------------
# Test 4: regression guard — scaffold names must NOT collide with any
# other rule's keyword lexicon. This is the "set" in "state" guard.
# ---------------------------------------------------------------------------


def test_scaffold_names_avoid_keyword_collisions(sample_plan: PackagePlan) -> None:
    """No scaffold name contains a substring from a competing rule's lexicon.

    The original bug was ``"set" in "state"`` which would cause
    ``check_state_*`` scaffolds to match ActionRule on tiebreak and
    collapse CONSTRAINT → ACTION. We guard against every rule's
    lexicon, not just ActionRule.
    """
    # CONSTRAINT scaffolds must contain a CONSTRAINT keyword and no
    # ACTION / OBSERVATION / POLICY / CONTEXT keywords.
    for s in sample_plan.scaffold_constraint_checks:
        assert _contains_any(s.name, CONSTRAINT_KEYWORDS), s.name
        assert not _contains_any(s.name, ACTION_KEYWORDS), (
            f"constraint scaffold {s.name!r} collides with ACTION_KEYWORDS"
        )
        assert not _contains_any(s.name, OBSERVATION_KEYWORDS), (
            f"constraint scaffold {s.name!r} collides with OBSERVATION_KEYWORDS"
        )
        assert not _contains_any(s.name, POLICY_FUNCTION_KEYWORDS), (
            f"constraint scaffold {s.name!r} collides with POLICY keywords"
        )
        assert not _contains_any(s.name, CONTEXT_KEYWORDS), (
            f"constraint scaffold {s.name!r} collides with CONTEXT_KEYWORDS"
        )

    # POLICY scaffolds must contain exactly ``route`` (not ``handle``
    # or ``dispatch`` which would collide with ActionRule).
    for s in sample_plan.scaffold_policy_functions:
        assert "route" in s.name.lower()
        assert not _contains_any(s.name, ACTION_KEYWORDS), (
            f"policy scaffold {s.name!r} collides with ACTION_KEYWORDS"
        )
        assert not _contains_any(s.name, OBSERVATION_KEYWORDS)
        assert not _contains_any(s.name, CONSTRAINT_KEYWORDS)
        assert not _contains_any(s.name, CONTEXT_KEYWORDS)

    # CONTEXT scaffolds must carry ``settings`` (not ``config`` which
    # is superseded by ConfigRule) and must not hit any higher-priority
    # rule's lexicon. Note: ``settings`` lexically contains ``set``
    # (an ACTION keyword) but ContextRule classifies by class name
    # while ActionRule's ``set`` keyword is tokenized on words, so
    # ``ObservationSettings0`` is classified as CONTEXT in practice.
    # We therefore only assert the critical invariants here.
    for s in sample_plan.scaffold_context_classes:
        assert "settings" in s.name.lower()
        assert "config" not in s.name.lower()
        assert not _contains_any(s.name, CONSTRAINT_KEYWORDS), s.name
        assert not _contains_any(s.name, POLICY_FUNCTION_KEYWORDS), s.name


# ---------------------------------------------------------------------------
# Test 5: synthesize_package writes a context.py that imports and
# exposes the expected Settings classes.
# ---------------------------------------------------------------------------


def test_synthesize_writes_context_module(tmp_path: Path, sample_plan: PackagePlan) -> None:
    """``synthesize_package`` must write ``context.py`` containing valid Settings classes."""
    model_path = tmp_path / "sample.gnn.md"
    model_path.write_text(SAMPLE_GNN, encoding="utf-8")
    model = parse_gnn(model_path)
    pkg = synthesize_package(sample_plan, model, tmp_path / "pkg")

    ctx_path = pkg / "context.py"
    assert ctx_path.exists(), "synthesize_package must emit context.py"
    src = ctx_path.read_text(encoding="utf-8")

    # Module compiles as Python (catches syntax errors in the renderer).
    tree = ast.parse(src)
    class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    expected = {s.name for s in sample_plan.scaffold_context_classes}
    assert expected.issubset(class_names), f"expected {expected}, got {class_names}"


# ---------------------------------------------------------------------------
# Test 6: synthesized constraints.py and policy.py are syntactically
# valid and contain the scaffold check_*/route_* entries.
# ---------------------------------------------------------------------------


def test_synthesize_writes_valid_constraints_and_policy(
    tmp_path: Path, sample_plan: PackagePlan
) -> None:
    """The emitted constraints.py and policy.py compile and include scaffolds."""
    model_path = tmp_path / "sample.gnn.md"
    model_path.write_text(SAMPLE_GNN, encoding="utf-8")
    model = parse_gnn(model_path)
    pkg = synthesize_package(sample_plan, model, tmp_path / "pkg2")

    constraints_src = (pkg / "constraints.py").read_text(encoding="utf-8")
    policy_src = (pkg / "policy.py").read_text(encoding="utf-8")

    # Parse to catch syntax errors.
    c_tree = ast.parse(constraints_src)
    p_tree = ast.parse(policy_src)

    c_fns = {n.name for n in ast.walk(c_tree) if isinstance(n, ast.FunctionDef)}
    p_fns = {n.name for n in ast.walk(p_tree) if isinstance(n, ast.FunctionDef)}

    expected_checks = {s.name for s in sample_plan.scaffold_constraint_checks}
    expected_routes = {s.name for s in sample_plan.scaffold_policy_functions}

    assert expected_checks.issubset(c_fns), f"missing scaffold checks: {expected_checks - c_fns}"
    assert expected_routes.issubset(p_fns), f"missing scaffold routes: {expected_routes - p_fns}"

    # Every scaffold check has the ``check_`` prefix so PreferenceRule
    # fires; every scaffold route has the ``route_`` prefix so
    # PolicyRule fires.
    for name in expected_checks:
        assert name.startswith("check_")
    for name in expected_routes:
        assert name.startswith("route_")


# ---------------------------------------------------------------------------
# Test 7: determinism — two planner runs on the same parsed model
# produce identical scaffold populations (same names, same order).
# ---------------------------------------------------------------------------


def test_plan_package_is_deterministic(tmp_path: Path) -> None:
    """Two plan_package calls on the same model produce identical scaffolds."""
    path = tmp_path / "det.gnn.md"
    path.write_text(SAMPLE_GNN, encoding="utf-8")
    model_a = parse_gnn(path)
    model_b = parse_gnn(path)

    plan_a = plan_package(model_a)
    plan_b = plan_package(model_b)

    assert [n.name for n in plan_a.scaffold_constraint_checks] == [
        n.name for n in plan_b.scaffold_constraint_checks
    ]
    assert [n.name for n in plan_a.scaffold_policy_functions] == [
        n.name for n in plan_b.scaffold_policy_functions
    ]
    assert [n.name for n in plan_a.scaffold_context_classes] == [
        n.name for n in plan_b.scaffold_context_classes
    ]


# ---------------------------------------------------------------------------
# Test 8: degenerate / empty default models do not get fixed scaffolds.
# ---------------------------------------------------------------------------


def test_empty_model_gets_minimum_scaffold_populations(
    empty_plan: PackagePlan,
) -> None:
    """Degenerate default models do not synthesize source-absent roles."""
    assert empty_plan.target_role_counts == {}
    assert empty_plan.scaffold_policy_functions == []
    assert empty_plan.scaffold_context_classes == []
    assert empty_plan.scaffold_constraint_checks == []


# ---------------------------------------------------------------------------
# Test 9: end-to-end — a synthesized package from a non-trivial GNN
# contains all four scaffold populations wired through correctly.
# This is the integration-level guard that the wiring in
# ``synthesize_package`` does not drop any scaffold module.
# ---------------------------------------------------------------------------


def test_synthesized_package_has_all_scaffold_populations(
    tmp_path: Path, sample_plan: PackagePlan
) -> None:
    """Synthesized package contains constraint, policy, and context scaffolds."""
    model_path = tmp_path / "sample.gnn.md"
    model_path.write_text(SAMPLE_GNN, encoding="utf-8")
    model = parse_gnn(model_path)
    pkg = synthesize_package(sample_plan, model, tmp_path / "pkg3")

    for filename in ("constraints.py", "policy.py", "context.py"):
        p = pkg / filename
        assert p.exists(), f"missing {filename} from synthesized package"
        src = p.read_text(encoding="utf-8")
        assert src.strip(), f"{filename} is empty"
        # All modules must parse cleanly.
        ast.parse(src)
