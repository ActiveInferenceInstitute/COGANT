"""Forward → reverse → forward round-trip integration test.

Exercises the full cycle::

    repo → forward(cogant) → GNN markdown → reverse(parse/plan/synthesize)
         → synthesized package → forward(cogant) → GNN'

and verifies that the verifier returns a populated invariant ledger for
the re-emitted GNN'. The calculator fixture is the default-threshold
regression guard: generated support code must not inflate semantic role
counts, and the result must be ``ROLE_PRESERVED`` at the public ``0.5``
threshold.

This is the canonical acceptance test for the round-trip method surface:
we do not require byte-equal recovery of the source code (GNN is a lossy
projection), and we do not relabel low-score results as successful.

Notes on API choice
-------------------
The reverse module exposes two composable public helpers:

* ``verify_roundtrip(gnn_path, tmp_dir=...)`` — takes a pre-existing
  GNN markdown file, synthesizes, re-runs forward, scores.
* ``verify_repo_roundtrip(repo_path, output_dir=...)`` — runs forward
  on a source repository first, then delegates to ``verify_roundtrip``.

We use the full ``verify_repo_roundtrip`` here because it provides
true end-to-end coverage from a plain Python repository all the way
back to a comparable GNN'. For diagnostic granularity we *also* exercise
the lower-level ``parse_gnn`` / ``plan_package`` / ``synthesize_package``
chain directly in a companion test so that failures in the stitch-up
are attributable.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from cogant.reverse import (
    ROUNDTRIP_STATUS_ROLE_PRESERVED,
    ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC,
    RoundtripResult,
    parse_gnn,
    plan_package,
    synthesize_package,
    verify_repo_roundtrip,
    verify_roundtrip,
)
from cogant.reverse.parser import ReverseGNNModel
from cogant.reverse.planner import PackagePlan

logger = logging.getLogger(__name__)


# Absolute path to the cogant project root and calculator fixture.
_COGANT_ROOT = Path(__file__).resolve().parents[2]
_CALCULATOR_FIXTURE = _COGANT_ROOT / "examples" / "control_positive" / "calculator"


@pytest.fixture()
def calculator_repo(tmp_path: Path) -> Path:
    """Return a usable calculator repo; fall back to a tiny synthesized one."""
    if _CALCULATOR_FIXTURE.exists() and (_CALCULATOR_FIXTURE / "calculator.py").exists():
        return _CALCULATOR_FIXTURE

    repo = tmp_path / "mini_calculator"
    repo.mkdir(parents=True)
    (repo / "__init__.py").write_text('"""mini calculator."""\n', encoding="utf-8")
    (repo / "calculator.py").write_text(
        '"""Tiny calculator fallback."""\n'
        "\n"
        "class Calculator:\n"
        "    def __init__(self):\n"
        "        self.display = '0'\n"
        "        self.history: list[str] = []\n"
        "\n"
        "    def input_digit(self, digit: int) -> str:\n"
        "        self.display = str(digit)\n"
        "        self.history.append(f'input_digit({digit})')\n"
        "        return self.display\n"
        "\n"
        "    def clear(self) -> str:\n"
        "        self.display = '0'\n"
        "        self.history.append('clear()')\n"
        "        return self.display\n"
        "\n"
        "    def get_display(self) -> str:\n"
        "        return self.display\n"
        "\n"
        "    def assert_display(self, expected: str) -> bool:\n"
        "        return self.display == expected\n",
        encoding="utf-8",
    )
    return repo


# ---------------------------------------------------------------------------
# Low-level roundtrip: parse → plan → synthesize → re-forward.
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_reverse_pipeline_low_level(calculator_repo: Path, tmp_path: Path) -> None:
    """Drive parser → planner → synthesizer → forward manually.

    This pins the public API of each component so individual stage
    regressions surface with a clear failure point before the higher
    level ``verify_roundtrip`` test runs.
    """
    # Step 1: run forward on the calculator repo and write out the GNN markdown.
    from cogant.api.bundle import ArtifactKey
    from cogant.api.pipeline import PipelineConfig, PipelineRunner

    forward_out = tmp_path / "forward_out"
    runner = PipelineRunner()
    config = PipelineConfig(output_dir=str(forward_out), skip_dynamic=True)
    bundle = runner.run(str(calculator_repo), config)
    assert bundle.errors == [], f"Forward pipeline errors: {bundle.errors}"

    gnn_md_path = forward_out / "gnn_package" / "model.gnn.md"
    assert gnn_md_path.exists(), (
        f"Forward pipeline did not emit GNN markdown at {gnn_md_path}. "
        f"Export stage result: {bundle.stage_results.get('export')}"
    )

    # Step 2: parse the GNN markdown back into a ReverseGNNModel.
    model = parse_gnn(gnn_md_path)
    assert isinstance(model, ReverseGNNModel)

    # Step 3: build a PackagePlan from the model.
    plan = plan_package(model)
    assert isinstance(plan, PackagePlan)
    assert plan.package_name, "PackagePlan missing a package_name"

    # Step 4: synthesize the Python package to a temp directory.
    synth_root = tmp_path / "synth"
    synth_root.mkdir()
    package_path = synthesize_package(plan, model, synth_root)
    assert package_path.exists() and package_path.is_dir()

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
    missing = expected_files - present
    assert not missing, (
        f"Synthesized package missing expected files {missing}. Present: {sorted(present)}"
    )

    # Step 5: re-run forward on the synthesized package and confirm it
    # produces a graph at all (the actual role-match score is verified
    # in the verify_roundtrip test below).
    synth_forward_out = tmp_path / "synth_forward_out"
    config_synth = PipelineConfig(output_dir=str(synth_forward_out), skip_dynamic=True)
    synth_bundle = PipelineRunner().run(str(package_path), config_synth)
    pg = synth_bundle.get_artifact(ArtifactKey.PROGRAM_GRAPH)
    assert pg is not None, (
        f"Forward pipeline on synthesized package produced no program graph. "
        f"Errors: {synth_bundle.errors}"
    )
    assert len(pg.nodes) >= 1, f"Synthesized repo graph is empty; nodes={len(pg.nodes)}"


# ---------------------------------------------------------------------------
# High-level roundtrip: verifier must complete and report honest diagnostics.
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_verify_roundtrip_meets_lenient_threshold(calculator_repo: Path, tmp_path: Path) -> None:
    """``verify_repo_roundtrip`` passes the default role-preservation gate."""
    work_dir = tmp_path / "roundtrip_work"
    result: RoundtripResult = verify_repo_roundtrip(
        calculator_repo,
        output_dir=work_dir,
        role_threshold=0.5,
    )

    logger.info("Roundtrip result: %s", result.summary())

    assert result.roundtrip_status in {
        ROUNDTRIP_STATUS_ROLE_PRESERVED,
        ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC,
    }
    assert result.role_preserved is True
    assert result.role_preservation_score >= 0.5
    assert result.original_roles, "source-side role multiset must be populated"
    assert result.synthesized_roles, "synthesized-side role multiset must be populated"
    assert result.synthesized_roles == result.original_roles
    assert "CONTEXT" not in result.synthesized_roles


@pytest.mark.integration
def test_verify_roundtrip_from_gnn_markdown(calculator_repo: Path, tmp_path: Path) -> None:
    """Lower-level entry point: ``verify_roundtrip`` on a precomputed GNN file.

    Produces the GNN markdown via the forward pipeline, then drives
    ``verify_roundtrip`` directly so we also cover the
    "parse → synth → re-forward" path the CLI uses.
    """
    from cogant.api.pipeline import PipelineConfig, PipelineRunner

    forward_out = tmp_path / "forward_out"
    runner = PipelineRunner()
    config = PipelineConfig(output_dir=str(forward_out), skip_dynamic=True)
    bundle = runner.run(str(calculator_repo), config)
    assert bundle.errors == [], f"Forward pipeline errors: {bundle.errors}"

    gnn_path = forward_out / "gnn_package" / "model.gnn.md"
    assert gnn_path.exists(), "Forward pipeline did not emit GNN markdown"

    reverse_work = tmp_path / "reverse_work"
    reverse_work.mkdir()

    result = verify_roundtrip(
        gnn_path,
        tmp_dir=reverse_work,
        role_threshold=0.5,
        keep_tmp=True,
    )

    assert result.roundtrip_status in {
        ROUNDTRIP_STATUS_ROLE_PRESERVED,
        ROUNDTRIP_STATUS_STRUCTURALLY_ISOMORPHIC,
    }
    assert result.role_preserved is True
    assert result.role_preservation_score >= 0.5
    assert result.original_roles, "source-side role multiset must be populated"
    assert result.synthesized_roles, "synthesized-side role multiset must be populated"
    assert result.synthesized_roles == result.original_roles
    assert "CONTEXT" not in result.synthesized_roles
    assert result.package_path is not None
    assert Path(result.package_path).exists(), (
        "Synthesized package directory should survive with keep_tmp=True"
    )
