"""CLI path options accept ``..`` and invalid values fail with a clean message.

``PipelineConfig`` rejects ``..`` components so config files, the
environment and server payloads cannot traverse. A path typed on the command
line (``-o ../out``, ``--cache-dir ../cache``) is the user's own choice and
is resolved to an absolute path instead. Values the model still rejects must
produce a one-line error and exit 1, never a raw pydantic traceback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from cogant.api.bundle import Bundle, StageOutcome
from cogant.cli.main import app


@pytest.fixture()
def layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """``tmp/repo`` with sources; the CLI runs from ``tmp/work``."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "counter.py").write_text(
        "class Counter:\n"
        "    def __init__(self):\n"
        "        self.n = 0\n"
        "    def inc(self):\n"
        "        self.n += 1\n",
        encoding="utf-8",
    )
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return tmp_path


@pytest.fixture()
def translate_seen(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from cogant.cli.commands import translate_cmd

    seen: dict[str, Any] = {}

    def fake_run(runner: Any, target: str, config: Any, description_prefix: str) -> Bundle:
        seen["config"] = config
        bundle = Bundle(target=target)
        for stage in config.stages:
            bundle.stage_results[stage] = {}
            bundle.stage_outcomes[stage] = StageOutcome.SUCCESS
        return bundle

    monkeypatch.setattr(translate_cmd, "_run_pipeline_with_progress", fake_run)
    return seen


def test_analyze_accepts_parent_relative_target_and_output(layout: Path) -> None:
    result = CliRunner().invoke(
        app, ["analyze", "../repo", "-o", "../out_dotdot", "--no-dynamic", "--format", "json"]
    )

    assert not isinstance(result.exception, ValidationError), result.exception
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output[result.output.index("{") :])
    assert Path(payload["bundle_path"]) == layout / "out_dotdot" / "bundle.json"
    assert (layout / "out_dotdot" / "bundle.json").is_file()


def test_translate_resolves_parent_relative_path_options(
    layout: Path, translate_seen: dict[str, Any]
) -> None:
    (layout / "cov.xml").write_text("<coverage/>", encoding="utf-8")
    (layout / "trace.json").write_text("[]", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "translate",
            "../repo",
            "-o",
            "../out",
            "--coverage",
            "../cov.xml",
            "--trace",
            "../trace.json",
            "--cache-dir",
            "../cache",
        ],
    )

    assert not isinstance(result.exception, ValidationError), result.exception
    assert result.exit_code == 0, result.output
    config = translate_seen["config"]
    assert config.output_dir == str(layout / "out")
    assert config.coverage_path == str(layout / "cov.xml")
    assert config.trace_path == str(layout / "trace.json")
    assert config.cache_dir == str(layout / "cache")
    assert (layout / "out" / "bundle.json").is_file()


def test_init_run_accepts_parent_relative_project(
    layout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cogant.cli.commands import setup

    seen: dict[str, Any] = {}

    def fake_run(runner: Any, target: str, config: Any, description_prefix: str) -> Bundle:
        seen["output_dir"] = config.output_dir
        return Bundle(target=target)

    monkeypatch.setattr(setup, "_run_pipeline_with_progress", fake_run)

    result = CliRunner().invoke(app, ["init", "../repo", "--run", "--yes"])

    assert result.exit_code == 0, result.output
    assert "Unexpected error" not in result.output
    assert seen["output_dir"] == str(layout / "repo" / "output")
    assert (layout / "repo" / "output" / "bundle.json").is_file()


@pytest.mark.parametrize("command", ["translate", "analyze"])
@pytest.mark.parametrize(
    ("option", "value", "field"),
    [
        ("--upstream-gnn-frameworks", "   ", "upstream_gnn_frameworks"),
        ("--skip", "not-a-stage", "skip_stages"),
    ],
)
def test_invalid_option_value_is_reported_without_traceback(
    command: str, option: str, value: str, field: str, layout: Path
) -> None:
    result = CliRunner().invoke(app, [command, "../repo", "-o", "../o", option, value])

    assert not isinstance(result.exception, ValidationError), result.exception
    assert result.exit_code == 1, result.output
    assert f"Invalid option value for {field}" in result.output
    assert "Traceback" not in result.output
    assert not (layout / "o").exists()


def test_config_file_parent_traversal_is_still_rejected(layout: Path) -> None:
    cfg = layout / "cfg.json"
    cfg.write_text(json.dumps({"pipeline": {"output_dir": "../outside"}}), encoding="utf-8")

    result = CliRunner().invoke(app, ["translate", "../repo", "-c", str(cfg)])

    assert result.exit_code == 1
    assert "Invalid configuration" in result.output
    assert not (layout / "outside").exists()
