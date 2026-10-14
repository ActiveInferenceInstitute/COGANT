"""Pure-function tests for ``cogant.gnn.upstream_bridge.pipeline``.

These are intentionally side-effect free — no upstream subprocess is
launched, no GNN package is built. Anything that requires real upstream
execution lives in ``tests/integration/test_upstream_gnn_pipeline.py``.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

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


def test_default_skip_steps_excludes_setup_tests_render_and_execute() -> None:
    """Setup/tests mutate or require an upstream checkout; render/execute are heavy."""
    assert DEFAULT_SKIP_STEPS == frozenset({1, 2, 11, 12})
    assert UPSTREAM_STEP_SCRIPTS[1] == "1_setup.py"
    assert UPSTREAM_STEP_SCRIPTS[2] == "2_tests.py"
    assert UPSTREAM_STEP_SCRIPTS[11] == "11_render.py"
    assert UPSTREAM_STEP_SCRIPTS[12] == "12_execute.py"


def test_config_default_skip_matches_catalogue_default(tmp_path: Path) -> None:
    cfg = UpstreamPipelineConfig(target_dir=tmp_path, output_dir=tmp_path / "out")
    assert cfg.skip_steps == sorted(DEFAULT_SKIP_STEPS)


# ---------------------------------------------------------------------------
# resolve_steps
# ---------------------------------------------------------------------------


def test_resolve_steps_default_returns_full_range() -> None:
    assert resolve_steps(None, None) == list(range(25))


def test_resolve_steps_default_skip_drops_setup_tests_render_and_execute() -> None:
    chosen = resolve_steps(None, sorted(DEFAULT_SKIP_STEPS))
    for step in (1, 2, 11, 12):
        assert step not in chosen
    assert len(chosen) == 21


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
    assert cfg.skip_steps == [1, 2, 11, 12]
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


def test_run_upstream_pipeline_returns_unavailable_when_gnn_main_missing(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bridge stays graceful when ``gnn.main`` cannot be imported."""
    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "_import_gnn_main", lambda: None)
    cfg = UpstreamPipelineConfig(
        target_dir=tmp_path / "pkg",
        output_dir=tmp_path / "out",
    )
    (tmp_path / "pkg").mkdir()
    result = pipeline_mod.run_upstream_pipeline(cfg)
    assert result.available is False
    assert result.error is not None
    assert "gnn.main" in result.error
    assert result.steps == []


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "gnn_package"
    package.mkdir()
    (package / "model.gnn.md").write_text("## GNNSection\nDemo\n", encoding="utf-8")
    (package / "connections.json").write_text("{}", encoding="utf-8")
    return package


def _flag_values(cmd: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for i, token in enumerate(cmd):
        if token.startswith("--") and i + 1 < len(cmd) and not cmd[i + 1].startswith("--"):
            values[token] = cmd[i + 1]
    return values


def test_build_main_command_is_one_invocation_with_active_python(tmp_path: Path) -> None:
    """GNN 4.x binds a run to one ``python -m gnn.main`` invocation."""
    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    cfg = UpstreamPipelineConfig(
        target_dir=_package(tmp_path),
        output_dir=tmp_path / "out",
        frameworks="pymdp,jax",
        timesteps=7,
        verbose=True,
        skip_llm=True,
    )
    cmd = pipeline_mod._build_main_command(cfg, tmp_path / "staged", [3, 5, 7])
    assert cmd[:3] == [sys.executable, "-m", "gnn.main"]
    flags = _flag_values(cmd)
    assert flags["--target-dir"] == str(tmp_path / "staged")
    assert flags["--output-dir"] == str(cfg.output_dir)
    assert flags["--only-steps"] == "3,5,7"
    assert flags["--frameworks"] == "pymdp,jax"
    assert flags["--timesteps"] == "7"
    # Default skips plus 13 (skip_llm) are passed explicitly.
    assert flags["--skip-steps"] == "1,2,11,12,13"
    assert "--verbose" in cmd and "--skip-llm" in cmd
    quiet = UpstreamPipelineConfig(
        target_dir=cfg.target_dir, output_dir=cfg.output_dir, skip_steps=[]
    )
    quiet_cmd = pipeline_mod._build_main_command(quiet, cfg.target_dir, [3])
    assert "--no-verbose" in quiet_cmd and "--skip-llm" not in quiet_cmd
    assert "--skip-steps" not in quiet_cmd


def test_skip_llm_removes_step_13_from_the_selection(tmp_path: Path) -> None:
    """Upstream never plans 13 under --skip-llm; the bridge must not request it."""
    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    cfg = UpstreamPipelineConfig(
        target_dir=tmp_path, output_dir=tmp_path / "out", only_steps=[3, 13], skip_llm=True
    )
    assert pipeline_mod._effective_skip(cfg) == [1, 2, 11, 12, 13]
    assert resolve_steps(cfg.only_steps, pipeline_mod._effective_skip(cfg)) == [3]


def test_auto_included_prerequisites_are_reported_not_hidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Steps upstream adds as prerequisites appear in steps/executed/auto_included."""
    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "_import_gnn_main", lambda: object())
    fake_run, _ = _fake_run_writing(
        _summary(
            {"script_name": "3_gnn.py", "status": "SUCCESS"},
            {"script_name": "7_export.py", "status": "SUCCESS"},
            {"script_name": "16_analysis.py", "status": "SUCCESS_WITH_WARNINGS"},
        )
    )
    monkeypatch.setattr(pipeline_mod.subprocess, "run", fake_run)
    cfg = UpstreamPipelineConfig(
        target_dir=_package(tmp_path), output_dir=tmp_path / "out", only_steps=[3, 16]
    )

    result = pipeline_mod.run_upstream_pipeline(cfg)

    assert [s.step_index for s in result.steps] == [3, 7, 16]
    assert result.auto_included == [7]
    assert result.executed == [3, 7, 16]
    assert 7 not in result.skipped and 12 in result.skipped
    assert result.to_dict()["auto_included"] == [7]


def test_child_env_scopes_llm_model_and_drops_inherited_run_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``llm_model`` reaches only the child; the caller's environment is untouched."""
    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    monkeypatch.setenv("GNN_RUN_ID", "stale-run")
    monkeypatch.setenv("GNN_RUN_CONTEXT_FILE", "/tmp/stale.json")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    cfg = UpstreamPipelineConfig(
        target_dir=tmp_path, output_dir=tmp_path / "out", llm_model="llama3:8b"
    )
    env = pipeline_mod._child_env(cfg)
    assert env["OLLAMA_MODEL"] == "llama3:8b"
    assert env["PYTHONUNBUFFERED"] == "1"
    assert "GNN_RUN_ID" not in env and "GNN_RUN_CONTEXT_FILE" not in env
    assert "OLLAMA_MODEL" not in os.environ
    assert os.environ["GNN_RUN_ID"] == "stale-run"


def test_stage_target_dir_stages_only_gnn_markdown(tmp_path: Path) -> None:
    """Upstream discovery must not receive JSON sidecars as model sources."""
    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    package = _package(tmp_path)
    (package / "notes.md").write_text("# not a gnn model\n", encoding="utf-8")
    out = tmp_path / "out"
    cfg = UpstreamPipelineConfig(target_dir=package, output_dir=out)

    staged = pipeline_mod._stage_target_dir(cfg)

    assert staged == (out / "_cogant_input").resolve()
    assert sorted(path.name for path in staged.iterdir()) == ["model.gnn.md"]
    assert (staged / "model.gnn.md").read_text(encoding="utf-8") == "## GNNSection\nDemo\n"


def test_stage_target_dir_without_markdown_returns_package(tmp_path: Path) -> None:
    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    package = tmp_path / "empty_pkg"
    package.mkdir()
    cfg = UpstreamPipelineConfig(target_dir=package, output_dir=tmp_path / "out")
    assert pipeline_mod._stage_target_dir(cfg) == package.resolve()


def _summary(*steps: dict[str, object], status: str = "SUCCESS_WITH_WARNINGS") -> dict[str, object]:
    return {"overall_status": status, "run_id": "abc123", "steps": list(steps)}


def test_steps_from_summary_maps_every_requested_step(tmp_path: Path) -> None:
    """Records map by script; requested steps missing from the summary are NOT_RUN."""
    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    cfg = UpstreamPipelineConfig(target_dir=tmp_path, output_dir=tmp_path / "out")
    summary = _summary(
        {
            "script_name": "3_gnn.py",
            "status": "SUCCESS_WITH_WARNINGS",
            "exit_code": 0,
            "duration_seconds": 0.5,
            "memory_delta_mb": 1.25,
        },
        {
            "script_name": "6_validation.py",
            "status": "FAILED",
            "exit_code": 1,
            "duration_seconds": "1.5",
            "stderr": "",
            "stdout": "x - INFO - ok\ny 6_validation.py - ERROR - Undefined variable\n",
        },
    )
    steps = pipeline_mod._steps_from_summary(summary, cfg, [3, 5, 6])
    assert [s.step_index for s in steps] == [3, 5, 6]
    gnn_step, missing, failed = steps
    assert gnn_step.success and gnn_step.status == "SUCCESS_WITH_WARNINGS"
    assert gnn_step.memory_delta_mb == 1.25 and gnn_step.error is None
    assert gnn_step.output_dir == str(cfg.output_dir / "3_gnn_output")
    assert missing.status == "NOT_RUN" and not missing.success
    assert failed.status == "FAILED" and failed.exit_code == 1 and failed.duration_s == 1.5
    assert failed.error is not None and "Undefined variable" in failed.error


def _fake_run_writing(summary: dict[str, object] | None, returncode: int = 0):
    import json as _json
    import subprocess as _subprocess

    captured: dict[str, object] = {}

    def _run(cmd, cwd, env, stdout, stderr, timeout, check):
        captured.update(cmd=cmd, cwd=cwd, env=env, timeout=timeout)
        stdout.write("upstream console line\nlast line of output\n")
        if summary is not None:
            out = Path(cmd[cmd.index("--output-dir") + 1])
            target = out / "00_pipeline_summary" / "pipeline_execution_summary.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(_json.dumps(summary), encoding="utf-8")
        return _subprocess.CompletedProcess(cmd, returncode)

    return _run, captured


def test_run_upstream_pipeline_reads_current_invocation_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "_import_gnn_main", lambda: object())
    fake_run, captured = _fake_run_writing(
        _summary({"script_name": "3_gnn.py", "status": "SUCCESS", "exit_code": 0})
    )
    monkeypatch.setattr(pipeline_mod.subprocess, "run", fake_run)
    cfg = UpstreamPipelineConfig(
        target_dir=_package(tmp_path), output_dir=tmp_path / "out", only_steps=[3], timeout_s=42
    )

    result = pipeline_mod.run_upstream_pipeline(cfg)

    assert result.available and result.error is None
    assert result.executed == [3]
    assert result.upstream_status == "SUCCESS_WITH_WARNINGS" and result.run_id == "abc123"
    assert [s.status for s in result.steps] == ["SUCCESS"]
    assert captured["cwd"] == cfg.output_dir and captured["timeout"] == 42
    cmd = captured["cmd"]
    assert cmd[cmd.index("--target-dir") + 1] == str(cfg.output_dir / "_cogant_input")
    log = (cfg.output_dir / "upstream_pipeline.log").read_text(encoding="utf-8")
    assert "upstream console line" in log
    bridge_summary = json.loads(
        (cfg.output_dir / "upstream_pipeline_summary.json").read_text(encoding="utf-8")
    )
    assert bridge_summary["executed"] == [3]
    assert bridge_summary["steps"][0]["status"] == "SUCCESS"


def test_run_upstream_pipeline_ignores_stale_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A summary left by an earlier run is never reported as this run's evidence."""
    import json

    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    out = tmp_path / "out"
    stale = out / "00_pipeline_summary" / "pipeline_execution_summary.json"
    stale.parent.mkdir(parents=True)
    stale.write_text(
        json.dumps(_summary({"script_name": "3_gnn.py", "status": "SUCCESS"})), encoding="utf-8"
    )
    os.utime(stale, (1_000_000, 1_000_000))
    monkeypatch.setattr(pipeline_mod, "_import_gnn_main", lambda: object())
    fake_run, _ = _fake_run_writing(None, returncode=1)
    monkeypatch.setattr(pipeline_mod.subprocess, "run", fake_run)
    cfg = UpstreamPipelineConfig(target_dir=_package(tmp_path), output_dir=out, only_steps=[3, 5])

    result = pipeline_mod.run_upstream_pipeline(cfg)

    assert [s.status for s in result.steps] == ["BRIDGE_ERROR", "BRIDGE_ERROR"]
    assert result.failure_count == 2
    assert result.error is not None
    assert "exited 1 without a pipeline summary" in result.error
    assert "last line of output" in result.error


def test_run_upstream_pipeline_reports_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    def _timeout(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(pipeline_mod, "_import_gnn_main", lambda: object())
    monkeypatch.setattr(pipeline_mod.subprocess, "run", _timeout)
    cfg = UpstreamPipelineConfig(
        target_dir=_package(tmp_path), output_dir=tmp_path / "out", only_steps=[3], timeout_s=5
    )

    result = pipeline_mod.run_upstream_pipeline(cfg)

    assert [s.status for s in result.steps] == ["TIMEOUT"]
    assert result.error == "upstream gnn.main exceeded the 5s bridge timeout"


def test_run_upstream_pipeline_empty_selection_is_a_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cogant.gnn.upstream_bridge import pipeline as pipeline_mod

    def _never(*args, **kwargs):
        raise AssertionError("upstream must not be launched for an empty selection")

    monkeypatch.setattr(pipeline_mod, "_import_gnn_main", lambda: object())
    monkeypatch.setattr(pipeline_mod.subprocess, "run", _never)
    cfg = UpstreamPipelineConfig(
        target_dir=_package(tmp_path), output_dir=tmp_path / "out", only_steps=[3], skip_steps=[3]
    )
    result = pipeline_mod.run_upstream_pipeline(cfg)
    assert result.available and result.steps == [] and result.executed == []
    assert len(result.skipped) == 25


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


def test_pipeline_config_default_skip_matches_bridge_default() -> None:
    """``PipelineConfig`` keeps a literal copy of the bridge default; pin it."""
    from cogant.config.pipeline import PipelineConfig

    assert PipelineConfig().upstream_gnn_skip_steps == sorted(DEFAULT_SKIP_STEPS)
