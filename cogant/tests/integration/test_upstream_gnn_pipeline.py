"""Integration tests for the upstream GNN 25-step pipeline pass.

Each test exercises ``run_upstream_pipeline`` against a real
``gnn_package/`` directory (no mocks). Steps actually shell out to the
upstream numbered scripts via ``src.main.execute_pipeline_step``.

The COGANT-built fixture at ``output/calculator/gnn_package/`` is used
when present; when it is not, the test builds a fresh one by running
``cogant analyze examples/control_positive/calculator``.

The full pass touches all 23 default-on steps and is correspondingly
slow; it is gated on ``COGANT_RUN_UPSTREAM_PIPELINE=1`` so the regular
test sweep stays fast. The smaller targeted tests (``only_steps``,
default-skip assertions, JSON round-trip) always run.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cogant.gnn.upstream_bridge.pipeline import (
    DEFAULT_SKIP_STEPS,
    UPSTREAM_STEP_SCRIPTS,
    UpstreamPipelineConfig,
    run_upstream_pipeline,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = REPO_ROOT / "output" / "calculator" / "gnn_package"
SAMPLE_REPO = REPO_ROOT / "examples" / "control_positive" / "calculator"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _has_required_files(pkg: Path) -> bool:
    return (pkg / "model.gnn.md").is_file() and (pkg / "manifest.json").is_file()


@pytest.fixture(scope="module")
def gnn_package_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return a real GNN package directory.

    Reuses ``output/calculator/gnn_package/`` when present (so repeated
    runs don't re-analyze the calculator example each time); otherwise
    builds a fresh one in a tmp dir.
    """
    if _has_required_files(DEFAULT_FIXTURE):
        return DEFAULT_FIXTURE

    if not SAMPLE_REPO.is_dir():  # pragma: no cover - fixture is shipped
        pytest.skip(f"sample repo missing: {SAMPLE_REPO}")

    out = tmp_path_factory.mktemp("upstream_pipeline_fixture")
    from cogant.api.pipeline import PipelineConfig, PipelineRunner

    runner = PipelineRunner()
    cfg = PipelineConfig(output_dir=str(out))
    runner.run(str(SAMPLE_REPO), cfg)
    candidate = out / "gnn_package"
    if not _has_required_files(candidate):
        pytest.skip(
            f"fresh analyze run did not produce a usable gnn_package at {candidate}"
        )
    return candidate


# ---------------------------------------------------------------------------
# Static / surface tests
# ---------------------------------------------------------------------------


def test_default_skip_excludes_render_and_execute() -> None:
    assert 11 in DEFAULT_SKIP_STEPS
    assert 12 in DEFAULT_SKIP_STEPS
    assert UPSTREAM_STEP_SCRIPTS[11] == "11_render.py"
    assert UPSTREAM_STEP_SCRIPTS[12] == "12_execute.py"


# ---------------------------------------------------------------------------
# Real-pipeline tests
# ---------------------------------------------------------------------------


def test_run_upstream_pipeline_only_steps_3_5(
    gnn_package_dir: Path, tmp_path: Path
) -> None:
    """``only=[3,5]`` runs exactly two steps and writes a summary JSON."""
    out = tmp_path / "upstream_only"
    cfg = UpstreamPipelineConfig(
        target_dir=gnn_package_dir,
        output_dir=out,
        only_steps=[3, 5],
    )
    result = run_upstream_pipeline(cfg)
    if not result.available:
        pytest.skip(f"upstream src.main not importable: {result.error}")

    assert result.executed == [3, 5]
    assert [s.step_index for s in result.steps] == [3, 5]
    assert (out / "upstream_pipeline_summary.json").is_file()

    data = json.loads(
        (out / "upstream_pipeline_summary.json").read_text(encoding="utf-8")
    )
    assert data["executed"] == [3, 5]
    assert len(data["steps"]) == 2


def test_run_upstream_pipeline_default_skips_render_and_execute(
    gnn_package_dir: Path, tmp_path: Path
) -> None:
    """The default skip list must keep 11 and 12 out of ``executed``."""
    out = tmp_path / "upstream_default_skip"
    cfg = UpstreamPipelineConfig(
        target_dir=gnn_package_dir,
        output_dir=out,
        only_steps=[10, 11, 12, 13],
    )
    result = run_upstream_pipeline(cfg)
    if not result.available:
        pytest.skip(f"upstream src.main not importable: {result.error}")

    assert 11 not in result.executed
    assert 12 not in result.executed
    assert 10 in result.executed
    assert 13 in result.executed


def test_pipeline_result_to_dict_is_json_serialisable(
    gnn_package_dir: Path, tmp_path: Path
) -> None:
    cfg = UpstreamPipelineConfig(
        target_dir=gnn_package_dir,
        output_dir=tmp_path / "upstream_round_trip",
        only_steps=[3],
    )
    result = run_upstream_pipeline(cfg)
    if not result.available:
        pytest.skip(f"upstream src.main not importable: {result.error}")

    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["available"] is True
    assert payload["executed"] == [3]
    assert "steps" in payload and isinstance(payload["steps"], list)


def test_render_execute_opt_in_runs_when_jax_available(
    gnn_package_dir: Path, tmp_path: Path
) -> None:
    """``only=[3,11,12]`` exercises render+execute when JAX is installed."""
    pytest.importorskip("jax")
    out = tmp_path / "upstream_render_execute"
    cfg = UpstreamPipelineConfig(
        target_dir=gnn_package_dir,
        output_dir=out,
        only_steps=[3, 11, 12],
        skip_steps=[],  # opt back in to render+execute
        frameworks="lite",
    )
    result = run_upstream_pipeline(cfg)
    if not result.available:
        pytest.skip(f"upstream src.main not importable: {result.error}")
    assert {s.step_index for s in result.steps} >= {11, 12}


@pytest.mark.skipif(
    os.environ.get("COGANT_RUN_UPSTREAM_PIPELINE") != "1",
    reason=(
        "Full 23-step upstream pass is slow; set "
        "COGANT_RUN_UPSTREAM_PIPELINE=1 to enable."
    ),
)
def test_run_full_upstream_pipeline_with_default_skip(
    gnn_package_dir: Path, tmp_path: Path
) -> None:
    """End-to-end: default-skip pass over the full catalogue."""
    out = tmp_path / "upstream_full_default"
    cfg = UpstreamPipelineConfig(
        target_dir=gnn_package_dir,
        output_dir=out,
    )
    result = run_upstream_pipeline(cfg)
    if not result.available:
        pytest.skip(f"upstream src.main not importable: {result.error}")
    assert len(result.executed) == 23
    assert 11 in result.skipped and 12 in result.skipped
