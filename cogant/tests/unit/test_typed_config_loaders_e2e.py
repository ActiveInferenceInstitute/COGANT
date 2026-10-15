"""Executable contract tests for the canonical project configuration."""

from __future__ import annotations

import pytest

from cogant.config import ProjectConfig
from cogant.config import defaults as defaults_module
from cogant.config import presets as presets_module
from cogant.config.loaders import ConfigLoader, ConfigLoadError
from cogant.config.pipeline import PipelineConfig


def test_default_pipeline_config_is_typed_and_has_all_stages() -> None:
    config = ConfigLoader.build_pipeline_config()
    assert isinstance(config, PipelineConfig)
    assert config.stages == [
        "ingest",
        "static",
        "normalize",
        "graph",
        "dynamic",
        "translate",
        "statespace",
        "process",
        "export",
        "validate",
    ]


@pytest.mark.parametrize("preset", sorted(presets_module.PRESETS))
def test_each_preset_is_a_complete_project_model(preset: str) -> None:
    config = ConfigLoader.load_preset(preset)
    assert isinstance(config, ProjectConfig)
    assert isinstance(config.pipeline, PipelineConfig)
    assert config.model_dump()["pipeline"]["stages"]


def test_defaults_and_preset_registries_are_the_same_registry() -> None:
    assert defaults_module.PRESETS is presets_module.PRESETS
    assert set(defaults_module.PRESETS) == {
        "default",
        "minimal",
        "standard",
        "comprehensive",
        "gnn-focused",
        "security",
    }


def test_file_environment_and_cli_precedence(tmp_path, monkeypatch) -> None:
    path = tmp_path / "project.yaml"
    path.write_text(
        "pipeline:\n  output_dir: file-output\n  min_confidence: 0.4\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("COGANT_PIPELINE__OUTPUT_DIR", "environment-output")
    config = ConfigLoader.load_project_config(
        path,
        preset="minimal",
        cli={"pipeline": {"output_dir": "cli-output"}},
    )
    assert config.pipeline.output_dir == "cli-output"
    assert config.pipeline.min_confidence == 0.4


def test_component_builder_accepts_canonical_nested_overlay() -> None:
    config = ConfigLoader.build_pipeline_config(
        config_dict={"pipeline": {"stages": ["ingest", "validate"]}}
    )
    assert config.stages == ["ingest", "validate"]


def test_load_project_config_returns_one_project_model() -> None:
    config = ConfigLoader.load_project_config(preset="default")
    assert isinstance(config, ProjectConfig)
    assert config.cogant is not None
    assert config.export is not None
    assert config.validation is not None
    assert config.server is not None
    assert config.batch is not None


@pytest.mark.parametrize("version", ["0.9", "1.1", "1.bad", "1.0\n", "2.0", 1, None])
def test_unsupported_schema_version_is_rejected(version) -> None:
    with pytest.raises(ConfigLoadError, match="schema_version"):
        ConfigLoader.load_project_config(overrides={"schema_version": version}, environment={})


def test_flat_fields_are_rejected() -> None:
    with pytest.raises(ConfigLoadError, match="Extra inputs"):
        ConfigLoader.load_project_config(
            overrides={"output_dir": "old", "max_workers": 2}, environment={}
        )


def test_single_segment_environment_does_not_override_config() -> None:
    config = ConfigLoader.load_project_config(
        environment={"COGANT_OUTPUT_DIR": "ignored"},
        overrides={"pipeline": {"output_dir": "canonical"}},
    )
    assert config.pipeline.output_dir == "canonical"


def test_server_resource_controls_are_in_the_canonical_model() -> None:
    config = ConfigLoader.load_from_dict(
        {
            "server": {
                "max_concurrent_requests": 2,
                "request_timeout_seconds": 12.5,
            }
        }
    )
    assert config.server.max_concurrent_requests == 2
    assert config.server.request_timeout_seconds == 12.5
