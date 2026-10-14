"""``cogant translate`` honours output settings from config file and env.

``--output`` and ``--layout-output`` belong to the highest-precedence CLI
layer only when the user actually passes them; otherwise
``pipeline.output_dir`` / ``pipeline.layout_output`` from ``--config`` or
``COGANT_PIPELINE__*`` must decide where the bundle is written.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cogant.api.bundle import Bundle, StageOutcome
from cogant.cli.main import app


@pytest.fixture()
def captured(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from cogant.cli.commands import translate_cmd

    seen: dict[str, Any] = {}

    def fake_run(runner: Any, target: str, config: Any, description_prefix: str) -> Bundle:
        seen["output_dir"] = config.output_dir
        seen["layout_output"] = config.layout_output
        bundle = Bundle(target=target)
        for stage in config.stages:
            bundle.stage_results[stage] = {}
            bundle.stage_outcomes[stage] = StageOutcome.SUCCESS
        return bundle

    monkeypatch.setattr(translate_cmd, "_run_pipeline_with_progress", fake_run)
    return seen


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    (path / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    return path


def test_config_file_output_dir_and_layout_are_used_without_cli_flags(
    tmp_path: Path, repo: Path, captured: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    from_config = tmp_path / "from_config"
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps({"pipeline": {"output_dir": str(from_config), "layout_output": True}}),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["translate", str(repo), "-c", str(cfg), "--no-dynamic"])

    assert result.exit_code == 0, result.output
    assert captured == {"output_dir": str(from_config), "layout_output": True}
    assert (from_config / "data" / "bundle.json").is_file()
    assert not (tmp_path / "output").exists()


def test_environment_output_dir_is_used_without_cli_flag(
    tmp_path: Path, repo: Path, captured: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    env_out = tmp_path / "env_out"

    result = CliRunner().invoke(
        app,
        ["translate", str(repo), "--no-dynamic"],
        env={"COGANT_PIPELINE__OUTPUT_DIR": str(env_out)},
    )

    assert result.exit_code == 0, result.output
    assert captured["output_dir"] == str(env_out)
    assert (env_out / "bundle.json").is_file()
    assert not (tmp_path / "output").exists()


def test_cli_output_flag_still_overrides_config_file(
    tmp_path: Path, repo: Path, captured: dict[str, Any]
) -> None:
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps({"pipeline": {"output_dir": str(tmp_path / "from_config")}}), encoding="utf-8"
    )
    cli_out = tmp_path / "cli_out"

    result = CliRunner().invoke(
        app, ["translate", str(repo), "-c", str(cfg), "-o", str(cli_out), "--no-dynamic"]
    )

    assert result.exit_code == 0, result.output
    assert captured == {"output_dir": str(cli_out), "layout_output": False}
    assert (cli_out / "bundle.json").is_file()
    assert not (tmp_path / "from_config").exists()


def test_default_output_dir_is_output_when_nothing_configures_it(
    tmp_path: Path, repo: Path, captured: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["translate", str(repo), "--no-dynamic"])
    assert result.exit_code == 0, result.output
    assert captured == {"output_dir": "output", "layout_output": False}
    assert (tmp_path / "output" / "bundle.json").is_file()
