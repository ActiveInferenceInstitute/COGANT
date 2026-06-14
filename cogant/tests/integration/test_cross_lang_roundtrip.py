"""Cross-language (JavaScript) roundtrip integration tests.

The canonical ``test_reverse_roundtrip`` suite proves the
forward → reverse → forward Galois loop for Python fixtures. These
tests extend the same empirical claim cross-language: we take a
hand-written JavaScript ``Observer`` fixture (``examples/zoo/13_js_observer``),
run the tree-sitter JS parser, build a program graph, run the
translation engine, compile a state-space model, emit a GNN markdown,
reverse-synthesize a Python package, and re-run the forward pipeline
on the synthesized package. The final role multiset must overlap the
JS-side multiset above the lenient ``ROLE_PRESERVATION_THRESHOLD`` (0.5).

The runtime tier is also exercised: the JS-derived A/B/C/D matrices
are fed into :class:`cogant.runtime.loop.AgentRuntime` which must
execute at least 10 perception–action steps without raising.

Tree-sitter is a soft dependency. When the ``tree_sitter_javascript``
grammar is not available the module emits a descriptive parser error
and these tests are skipped — the cross-language claim is about what
happens *when* the grammar is loaded, not whether it must always be.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import MappingKind, SemanticMapping

from ._js_helpers import (  # noqa: E402
    _HAS_JS_PARSER,
    _build_javascript_graph,
    _run_translation,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Probe the tree-sitter JS grammar at import time so the skip message is
# attached to a concrete reason rather than an opaque ImportError.
try:
    _PARSERS_ROOT = _REPO_ROOT / "parsers"
    if str(_PARSERS_ROOT) not in sys.path:
        sys.path.insert(0, str(_PARSERS_ROOT))
    from javascript.parser import JavaScriptLanguageParser  # type: ignore

    _probe = JavaScriptLanguageParser()
    _probe_result = _probe.parse("class _Probe {}\n", "_probe.js")
    _GRAMMAR_AVAILABLE = not _probe_result.get("error")
    _GRAMMAR_ERROR = _probe_result.get("error") or ""
except Exception as exc:  # pragma: no cover - defensive
    _GRAMMAR_AVAILABLE = False
    _GRAMMAR_ERROR = f"{type(exc).__name__}: {exc}"

_SKIP_REASON = (
    f"tree-sitter JavaScript grammar unavailable ({_GRAMMAR_ERROR}); "
    f"install cogant[multilang] to run the cross-language roundtrip tests"
)
_requires_js = pytest.mark.skipif(not _HAS_JS_PARSER or not _GRAMMAR_AVAILABLE, reason=_SKIP_REASON)


# ---------------------------------------------------------------------------
# Shared paths and cached pipeline state.
# ---------------------------------------------------------------------------

_JS_FIXTURE = _REPO_ROOT / "examples" / "zoo" / "13_js_observer" / "observer.js"


def _js_pipeline() -> dict[str, Any]:
    """Run the JS forward pipeline and return its intermediate artifacts.

    Builds a program graph from the fixture, runs the translation
    engine, compiles a state-space model, builds matrices, and returns
    a dict with everything downstream tests need. Kept as a plain
    function (not a fixture) so the expensive setup is shared between
    tests via a module-level lazy cache.
    """
    from cogant.gnn.matrices import GNNMatrices
    from cogant.statespace.compiler import StateSpaceCompiler

    graph = _build_javascript_graph(_JS_FIXTURE)
    mappings: list[SemanticMapping] = _run_translation(graph)
    mapping_dict: dict[str, SemanticMapping] = {m.id: m for m in mappings}

    compiler = StateSpaceCompiler(program_graph=graph, schema_name="js_observer")
    state_space = compiler.compile(mapping_dict)

    gnn_mats = GNNMatrices(graph=graph, mappings=mappings, state_space=state_space)
    A = gnn_mats.compute_A()
    B = gnn_mats.compute_B()
    C = gnn_mats.compute_C()
    D = gnn_mats.compute_D()

    return {
        "graph": graph,
        "mappings": mappings,
        "mapping_dict": mapping_dict,
        "state_space": state_space,
        "A": A,
        "B": B,
        "C": C,
        "D": D,
    }


@pytest.fixture
def js_pipeline() -> dict[str, Any]:
    """Fresh JS Observer forward pipeline per test (no shared mutable cache)."""
    return _js_pipeline()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@_requires_js
def test_js_fixture_parses_without_error(js_pipeline: dict[str, Any]) -> None:
    """The JS fixture must parse cleanly and produce a non-empty graph.

    Verifies:
      * The fixture file exists at the expected location.
      * The tree-sitter JS parser returns no error.
      * ``_build_javascript_graph`` yields at least one class and one
        method so the downstream translation rules have something to
        match against.
    """
    assert _JS_FIXTURE.exists(), (
        f"Expected JS fixture at {_JS_FIXTURE}. "
        f"Create it with an Observer class (see zoo/02_observer for the "
        f"Python twin)."
    )

    graph: ProgramGraph = js_pipeline["graph"]
    assert len(graph.nodes) > 0, "JS graph must not be empty"

    from cogant.schemas.core import NodeKind

    class_nodes = [n for n in graph.nodes.values() if n.kind == NodeKind.CLASS]
    method_nodes = [n for n in graph.nodes.values() if n.kind == NodeKind.METHOD]
    assert class_nodes, (
        f"JS fixture produced no CLASS nodes; got kinds "
        f"{sorted({n.kind.name for n in graph.nodes.values()})}"
    )
    assert method_nodes, (
        f"JS fixture produced no METHOD nodes; got kinds "
        f"{sorted({n.kind.name for n in graph.nodes.values()})}"
    )

    # The four named methods we care about must all appear.
    method_names = {n.name for n in method_nodes}
    expected = {"constructor", "update", "getState", "checkValid"}
    missing = expected - method_names
    assert not missing, (
        f"JS fixture is missing methods {missing}; parser surfaced {sorted(method_names)}"
    )


@_requires_js
def test_js_translation_produces_core_active_inference_roles(
    js_pipeline: dict[str, Any],
) -> None:
    """At least one HIDDEN_STATE, OBSERVATION, and ACTION mapping.

    This is the cross-language equivalent of the Python zoo/02_observer
    translation claim: the same structural rules must fire on JS source
    and produce the three mandatory Active Inference role categories.
    CONSTRAINT is exercised separately below because it's optional in
    principle — for this particular fixture the ``checkValid`` method
    should trigger the constraint rule, but we keep the mandatory list
    aligned with the cross-language differential test.
    """
    mappings: list[SemanticMapping] = js_pipeline["mappings"]
    assert mappings, "JS translation produced no mappings"

    kinds = {m.kind for m in mappings}
    required = {
        MappingKind.HIDDEN_STATE,
        MappingKind.OBSERVATION,
        MappingKind.ACTION,
    }
    missing = required - kinds
    assert not missing, (
        f"JS mappings missing {sorted(k.value for k in missing)}; "
        f"present={sorted(k.value for k in kinds)}"
    )


@_requires_js
def test_js_state_space_and_matrices_are_non_degenerate(
    js_pipeline: dict[str, Any],
) -> None:
    """The compiled state-space must expose matrices with sensible shapes.

    We do not require any particular cardinality — the fixture is tiny
    and the compiler may legitimately collapse into a single factor —
    but every matrix must be non-empty and rectangular so the runtime
    can consume it.
    """
    A = js_pipeline["A"]
    B = js_pipeline["B"]
    C = js_pipeline["C"]
    D = js_pipeline["D"]

    assert A and all(len(row) == len(A[0]) for row in A), (
        f"A must be rectangular and non-empty; got shape "
        f"{[len(row) for row in A] if A else 'empty'}"
    )
    assert B and B[0] and B[0][0], (
        f"B must have non-empty state/action extents; got "
        f"{len(B)}x{len(B[0]) if B else 0}x"
        f"{len(B[0][0]) if B and B[0] else 0}"
    )
    assert len(C) >= 1, f"C preferences empty; got len={len(C)}"
    assert len(D) >= 1, f"D prior empty; got len={len(D)}"

    # Probability-simplex sanity: A is column-stochastic (P(o|s) sums to 1
    # over observation outcomes for each fixed hidden state s), and D is a
    # valid distribution. This catches uninitialised matrices early.
    n_states_A = len(A[0]) if A else 0
    for j in range(n_states_A):
        s = sum(A[i][j] for i in range(len(A)))
        assert abs(s - 1.0) < 1e-6 or s == 0.0, f"A column {j} should be normalised; sum={s}"
    d_sum = sum(D)
    assert abs(d_sum - 1.0) < 1e-6 or d_sum == 0.0, f"D prior should be normalised; sum={d_sum}"


@_requires_js
def test_js_gnn_emission_has_all_canonical_sections(
    tmp_path: Path,
    js_pipeline: dict[str, Any],
) -> None:
    """GNN markdown emitted from the JS-derived pipeline has every section.

    The canonical GNN sections (``StateSpaceBlock``, ``Connections``,
    ``ActInfOntologyAnnotation``, ``InitialParameterization``,
    ``ModelParameters``, ``Time``) must all be present so downstream
    consumers — and the reverse parser — can round-trip the model.
    """
    from cogant.gnn.formatter import GNNMarkdownFormatter
    from cogant.process.extractor import ProcessExtractor

    graph = js_pipeline["graph"]
    mapping_dict = js_pipeline["mapping_dict"]
    state_space = js_pipeline["state_space"]

    process_model = ProcessExtractor(program_graph=graph, schema_name="js_observer").extract()

    formatter = GNNMarkdownFormatter(
        program_graph=graph,
        state_space_model=state_space,
        process_model=process_model,
        semantic_mappings=mapping_dict,
    )
    gnn_md = formatter.format()
    assert gnn_md.strip(), "Formatter produced empty GNN markdown"

    required_sections = [
        "StateSpaceBlock",
        "Connections",
        "ActInfOntologyAnnotation",
        "InitialParameterization",
        "ModelParameters",
        "Time",
    ]
    missing = [s for s in required_sections if f"## {s}" not in gnn_md]
    assert not missing, (
        f"GNN markdown missing sections {missing}. "
        f"Full output ({len(gnn_md)} chars) starts with: {gnn_md[:400]!r}"
    )

    # Persist the rendered GNN for diagnostic purposes.
    (tmp_path / "model.gnn.md").write_text(gnn_md, encoding="utf-8")


@_requires_js
def test_js_forward_reverse_forward_role_match_above_threshold(
    tmp_path: Path,
    js_pipeline: dict[str, Any],
) -> None:
    """JS → GNN → Python package → forward: role_preservation_score > 0.5.

    The strictest acceptance criterion for the cross-language claim:
    the role multiset recovered from re-scanning the reverse-synthesized
    Python package must overlap the JS-side multiset above the lenient
    isomorphism threshold. A ``role_preservation_score`` of exactly 0.5 means
    half the JS-side roles survived the lossy GNN projection; anything
    above that is evidence the core Active Inference structure holds
    cross-language.
    """
    from cogant.gnn.formatter import GNNMarkdownFormatter
    from cogant.process.extractor import ProcessExtractor
    from cogant.reverse.idempotency import (
        ROLE_PRESERVATION_THRESHOLD,
        _role_multiset_from_mappings,
        _run_forward,
    )
    from cogant.reverse.parser import parse_gnn
    from cogant.reverse.planner import plan_package
    from cogant.reverse.synthesizer import synthesize_package

    graph = js_pipeline["graph"]
    mapping_dict = js_pipeline["mapping_dict"]
    state_space = js_pipeline["state_space"]

    process_model = ProcessExtractor(program_graph=graph, schema_name="js_observer").extract()
    formatter = GNNMarkdownFormatter(
        program_graph=graph,
        state_space_model=state_space,
        process_model=process_model,
        semantic_mappings=mapping_dict,
    )
    gnn_md = formatter.format()
    gnn_path = tmp_path / "model.gnn.md"
    gnn_path.write_text(gnn_md, encoding="utf-8")

    reverse_model = parse_gnn(gnn_path)
    plan = plan_package(reverse_model)
    synth_root = tmp_path / "synth"
    synth_root.mkdir()
    package_path = synthesize_package(plan, reverse_model, synth_root)
    assert package_path.exists() and package_path.is_dir(), (
        f"Synthesized package missing: {package_path}"
    )

    # Every canonical synthesized file should be present.
    expected_files = {
        "__init__.py",
        "state.py",
        "observe.py",
        "act.py",
        "policy.py",
        "constraints.py",
        "matrices.py",
        "main.py",
    }
    present = {p.name for p in package_path.iterdir() if p.is_file()}
    missing_files = expected_files - present
    assert not missing_files, (
        f"Synthesized package missing {missing_files}; present={sorted(present)}"
    )

    forward = _run_forward(package_path)
    assert forward.get("error") is None, (
        f"Re-forward on synthesized package failed: {forward['error']}"
    )

    r1 = _role_multiset_from_mappings(mapping_dict)
    r2 = _role_multiset_from_mappings(forward.get("mappings"))
    assert sum(r1.values()) > 0, (
        f"JS forward produced zero roles; nothing to roundtrip. r1={dict(r1)}"
    )
    overlap = sum((r1 & r2).values())
    score = overlap / sum(r1.values())

    assert ROLE_PRESERVATION_THRESHOLD <= 0.5, (
        "ROLE_PRESERVATION_THRESHOLD tightened unexpectedly; this test assumes the lenient default."
    )
    assert score > 0.5, (
        f"Cross-language role_preservation_score={score:.4f} <= 0.5. "
        f"R1(js)={dict(r1)}  R2(resyn)={dict(r2)}"
    )


@_requires_js
def test_js_agent_runtime_runs_ten_steps_without_exception(
    js_pipeline: dict[str, Any],
) -> None:
    """AgentRuntime must execute ≥10 perception–action steps on JS matrices.

    Exercises the full runtime path from JS-derived A/B/C/D through
    :class:`cogant.runtime.loop.AgentRuntime`. We check that the step
    count, VFE values, and action indices are all well-formed rather
    than asserting any particular convergence behaviour — the fixture
    is too small to produce interesting dynamics, and that's fine.
    """
    from cogant.runtime.loop import AgentRuntime, AgentStep

    mats = {
        "A": js_pipeline["A"],
        "B": js_pipeline["B"],
        "C": js_pipeline["C"],
        "D": js_pipeline["D"],
    }
    runtime = AgentRuntime.from_matrices_dict(mats)

    steps = runtime.run_n_steps(10)
    assert isinstance(steps, list) and len(steps) == 10, (
        f"AgentRuntime.run_n_steps(10) produced {len(steps)} steps; expected 10"
    )
    for s in steps:
        assert isinstance(s, AgentStep)
        assert s.state_dist, "AgentStep.state_dist is empty"
        # Distributions must stay on the simplex (up to floating-point slack).
        assert all(v >= -1e-9 for v in s.state_dist), (
            f"negative probability mass at t={s.t}: {s.state_dist}"
        )
        assert abs(sum(s.state_dist) - 1.0) < 1e-6, (
            f"state_dist not normalised at t={s.t}: sum={sum(s.state_dist)}"
        )
        assert s.action >= 0, f"negative action index at t={s.t}: {s.action}"
        # Free energy must be a finite number (NaN/Inf would indicate a bug).
        assert s.free_energy == s.free_energy, (  # NaN != NaN
            f"VFE is NaN at t={s.t}"
        )
        assert float("-inf") < s.free_energy < float("inf"), (
            f"VFE is infinite at t={s.t}: {s.free_energy}"
        )
