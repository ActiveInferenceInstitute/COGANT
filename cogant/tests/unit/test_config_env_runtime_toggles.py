"""The environment config layer ignores COGANT runtime toggles.

COGANT reads several single-segment ``COGANT_*`` variables directly
(``COGANT_USE_RUST``, ``COGANT_DISABLE_UPSTREAM_GNN``, ...). Those are
runtime switches, not ``COGANT_SECTION__FIELD`` configuration keys, so the
loader must leave them alone instead of rejecting the whole configuration.
Keys that do use the double-underscore configuration syntax stay strict.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cogant.api.bundle import Bundle, StageOutcome
from cogant.cli.main import app
from cogant.config.loaders import ConfigLoader, ConfigLoadError

RUNTIME_TOGGLES = {
    "COGANT_USE_RUST": "0",
    "COGANT_DISABLE_UPSTREAM_GNN": "1",
    "COGANT_ENABLE_UPSTREAM_GNN": "1",
    "COGANT_USE_EXTERNAL_MMDC": "1",
    "COGANT_ALLOW_NPX_MMDC": "1",
    "COGANT_RUN_UPSTREAM_PIPELINE": "1",
    "COGANT_USE_EXTERNAL_SVG_CONVERTERS": "1",
}


@pytest.mark.parametrize(("key", "value"), sorted(RUNTIME_TOGGLES.items()))
def test_runtime_toggle_does_not_break_config_loading(key: str, value: str) -> None:
    config = ConfigLoader.load_project_config(environment={key: value})
    assert config.pipeline.output_dir == "output"


def test_runtime_toggles_coexist_with_section_field_keys() -> None:
    environment = dict(RUNTIME_TOGGLES)
    environment["COGANT_PIPELINE__OUTPUT_DIR"] = "env-output"
    config = ConfigLoader.load_project_config(environment=environment)
    assert config.pipeline.output_dir == "env-output"


@pytest.mark.parametrize(
    "key",
    [
        "COGANT_NOT_A_SECTION__FIELD",
        "COGANT_PIPELINE__",
        "COGANT___OUTPUT_DIR",
        "COGANT_PIPELINE__OUTPUT__DIR",
        "COGANT_PIPELINE__NOT_A_FIELD",
    ],
)
def test_malformed_section_field_keys_are_still_rejected(key: str) -> None:
    with pytest.raises(ConfigLoadError):
        ConfigLoader.load_project_config(environment={key: "1"})


def test_translate_runs_with_runtime_toggle_exported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``COGANT_USE_RUST=0 cogant translate`` reaches the pipeline."""
    from cogant.cli.commands import translate_cmd

    seen: dict[str, Any] = {}

    def fake_run(runner: Any, target: str, config: Any, description_prefix: str) -> Bundle:
        seen["output_dir"] = config.output_dir
        bundle = Bundle(target=target)
        for stage in config.stages:
            bundle.stage_results[stage] = {}
            bundle.stage_outcomes[stage] = StageOutcome.SUCCESS
        return bundle

    monkeypatch.setattr(translate_cmd, "_run_pipeline_with_progress", fake_run)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    out = tmp_path / "out"

    result = CliRunner().invoke(
        app,
        ["translate", str(repo), "-o", str(out), "--no-dynamic"],
        env=RUNTIME_TOGGLES,
    )

    assert result.exit_code == 0, result.stdout
    assert "Invalid configuration" not in result.stdout
    assert seen["output_dir"] == str(out)
    assert (out / "bundle.json").is_file()
