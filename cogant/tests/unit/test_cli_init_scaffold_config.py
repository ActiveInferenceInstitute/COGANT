"""``cogant init`` scaffolds a loadable config and writes the bundle it reports.

The scaffolded ``.cogant/config.json`` must validate as a canonical
``ProjectConfig`` (so ``cogant translate -c .cogant/config.json`` works), and
``init --run`` must actually write the ``bundle.json`` path it prints.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cogant.api.bundle import Bundle, StageOutcome
from cogant.cli.main import app
from cogant.config.loaders import ConfigLoader


def _fake_bundle(target: str, config: Any) -> Bundle:
    bundle = Bundle(target=target)
    for stage in config.stages:
        bundle.stage_results[stage] = {}
        bundle.stage_outcomes[stage] = StageOutcome.SUCCESS
    return bundle


def test_init_config_loads_as_canonical_project_config(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    result = CliRunner().invoke(app, ["init", str(proj)])
    assert result.exit_code == 0, result.output

    config_path = proj / ".cogant" / "config.json"
    config = ConfigLoader.load_project_config(config_path)

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    assert config.pipeline.stages == raw["pipeline"]["stages"]
    assert "translate" in config.pipeline.stages
    assert config.pipeline.output_dir == "output"


def test_translate_accepts_init_config_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cogant.cli.commands import translate_cmd

    seen: dict[str, Any] = {}

    def fake_run(runner: Any, target: str, config: Any, description_prefix: str) -> Bundle:
        seen["stages"] = list(config.stages)
        return _fake_bundle(target, config)

    monkeypatch.setattr(translate_cmd, "_run_pipeline_with_progress", fake_run)
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    runner = CliRunner()
    assert runner.invoke(app, ["init", str(proj)]).exit_code == 0

    result = runner.invoke(
        app,
        [
            "translate",
            str(proj),
            "-c",
            str(proj / ".cogant" / "config.json"),
            "-o",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Invalid configuration" not in result.output
    raw = json.loads((proj / ".cogant" / "config.json").read_text(encoding="utf-8"))
    assert seen["stages"] == raw["pipeline"]["stages"]


def test_init_run_writes_the_bundle_it_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cogant.cli.commands import setup

    def fake_run(runner: Any, target: str, config: Any, description_prefix: str) -> Bundle:
        return _fake_bundle(target, config)

    monkeypatch.setattr(setup, "_run_pipeline_with_progress", fake_run)
    proj = tmp_path / "run_proj"
    proj.mkdir()
    (proj / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["init", str(proj), "--run", "--yes"])

    assert result.exit_code == 0, result.output
    bundle_path = proj / "output" / "bundle.json"
    # Rich wraps long paths; compare against the unwrapped text.
    assert f"Bundle: {bundle_path}" in result.output.replace("\n", "")
    saved = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert saved["target"] == str(proj)
