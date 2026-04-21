"""Pure-function tests for ``cogant.gnn.upstream_bridge.pipeline``.

These are intentionally side-effect free — no upstream subprocess is
launched, no GNN package is built. Anything that requires real upstream
execution lives in ``tests/integration/test_upstream_gnn_pipeline.py``.
"""

from __future__ import annotations

import re

import pytest

from cogant.gnn.upstream_bridge.pipeline import (
    DEFAULT_SKIP_STEPS,
    UPSTREAM_STEP_SCRIPTS,
    UpstreamPipelineConfig,
    UpstreamPipelineResult,
    UpstreamStepResult,
    resolve_steps,
)

# ---------------------------------------------------------------------------
# Catalogue invariants
# ---------------------------------------------------------------------------


def test_upstream_step_scripts_has_25_entries() -> None:
    assert len(UPSTREAM_STEP_SCRIPTS) == 25


def test_upstream_step_scripts_indices_match_filename_prefix() -> None:
    """``UPSTREAM_STEP_SCRIPTS[i]`` must start with ``{i}_``."""
    pattern = re.compile(r"^(\d+)_[a-z0-9_]+\.py$")
    for index, script in enumerate(UPSTREAM_STEP_SCRIPTS):
        match = pattern.match(script)
        assert match is not None, f"unexpected script name: {script!r}"
        assert int(match.group(1)) == index, (
            f"script {script!r} at index {index} reports prefix {match.group(1)}; ordering broken"
        )


def test_upstream_step_scripts_are_unique() -> None:
    assert len(set(UPSTREAM_STEP_SCRIPTS)) == len(UPSTREAM_STEP_SCRIPTS)


def test_default_skip_steps_excludes_render_and_execute() -> None:
    assert DEFAULT_SKIP_STEPS == frozenset({11, 12})
    assert UPSTREAM_STEP_SCRIPTS[11] == "11_render.py"
    assert UPSTREAM_STEP_SCRIPTS[12] == "12_execute.py"


# ---------------------------------------------------------------------------
# resolve_steps
# ---------------------------------------------------------------------------


def test_resolve_steps_default_returns_full_range() -> None:
    assert resolve_steps(None, None) == list(range(25))


def test_resolve_steps_default_skip_drops_render_and_execute() -> None:
    chosen = resolve_steps(None, sorted(DEFAULT_SKIP_STEPS))
    assert 11 not in chosen
    assert 12 not in chosen
    assert len(chosen) == 23


def test_resolve_steps_only_steps_preserves_order() -> None:
    assert resolve_steps([5, 3, 7, 3], None) == [3, 5, 7]


def test_resolve_steps_only_intersected_with_skip() -> None:
    assert resolve_steps([3, 5, 7], [5]) == [3, 7]


def test_resolve_steps_drops_out_of_range_only() -> None:
    """Step indices outside ``range(25)`` are silently dropped."""
    assert resolve_steps([3, 99, -1, 24], None) == [3, 24]


def test_resolve_steps_returns_empty_when_only_and_skip_overlap() -> None:
    assert resolve_steps([3, 5], [3, 5]) == []


# ---------------------------------------------------------------------------
# Dataclass defaults / round-trips
# ---------------------------------------------------------------------------


def test_upstream_pipeline_config_resolves_paths(tmp_path) -> None:
    target = tmp_path / "pkg"
    target.mkdir()
    out = tmp_path / "out"
    cfg = UpstreamPipelineConfig(target_dir=target, output_dir=out)
    assert cfg.target_dir == target.resolve()
    assert cfg.output_dir == out.resolve()
    assert cfg.skip_steps == [11, 12]
    assert cfg.only_steps is None
    assert cfg.frameworks == "lite"


def test_upstream_step_result_to_dict_round_trips_via_json() -> None:
    import json

    result = UpstreamStepResult(
        step_index=3,
        script="3_gnn.py",
        status="SUCCESS",
        success=True,
        duration_s=1.25,
        exit_code=0,
        memory_delta_mb=12.5,
        output_dir="/tmp/out/3_gnn_output",
    )
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["step_index"] == 3
    assert payload["status"] == "SUCCESS"
    assert payload["success"] is True


def test_upstream_pipeline_result_counts_successes_and_failures() -> None:
    steps = [
        UpstreamStepResult(0, "0_template.py", "SUCCESS", True, 0.1),
        UpstreamStepResult(1, "1_setup.py", "SUCCESS_WITH_WARNINGS", True, 0.2),
        UpstreamStepResult(2, "2_tests.py", "FAILED", False, 0.3, error="boom"),
    ]
    result = UpstreamPipelineResult(
        available=True,
        steps=steps,
        executed=[0, 1, 2],
        skipped=list(range(3, 25)),
        total_duration_s=0.6,
    )
    assert result.success_count == 2
    assert result.failure_count == 1
    assert result.success_rate == pytest.approx(2 / 3)
    payload = result.to_dict()
    assert payload["success_count"] == 2
    assert payload["failure_count"] == 1
    assert payload["success_rate"] == pytest.approx(2 / 3)
    assert len(payload["steps"]) == 3


def test_upstream_pipeline_result_success_rate_is_zero_for_empty_run() -> None:
    """``success_rate`` defines a safe value for empty / unavailable runs."""
    empty = UpstreamPipelineResult(available=False)
    assert empty.success_rate == 0.0
    assert empty.to_dict()["success_rate"] == 0.0


def test_run_upstream_pipeline_returns_unavailable_when_src_main_missing(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bridge stays graceful when ``src.main`` cannot be imported."""
    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "_import_src_main", lambda: None)
    cfg = UpstreamPipelineConfig(
        target_dir=tmp_path / "pkg",
        output_dir=tmp_path / "out",
    )
    (tmp_path / "pkg").mkdir()
    result = pipeline_mod.run_upstream_pipeline(cfg)
    assert result.available is False
    assert result.error is not None
    assert "src.main" in result.error
    assert result.steps == []


# ---------------------------------------------------------------------------
# CLI helper: --upstream-gnn-skip-steps semantics
# ---------------------------------------------------------------------------


def test_parse_step_csv_empty_means_distinguishes_skip_from_only() -> None:
    """``--skip-steps ""`` clears the default; ``--only-steps ""`` stays None."""
    from cogant.cli.main import _parse_step_csv

    assert _parse_step_csv(None, label="x") is None
    assert _parse_step_csv("", label="x") is None
    assert _parse_step_csv("", label="x", empty_means=[]) == []
    assert _parse_step_csv("3,5,7", label="x") == [3, 5, 7]


def test_parse_step_csv_rejects_out_of_range() -> None:
    import typer

    from cogant.cli.main import _parse_step_csv

    with pytest.raises(typer.BadParameter):
        _parse_step_csv("3,99", label="--upstream-gnn-only-steps")
    with pytest.raises(typer.BadParameter):
        _parse_step_csv("not,an,int", label="--upstream-gnn-only-steps")
