"""Executable contract tests for the canonical project configuration."""

from __future__ import annotations

import pytest

from cogant.config import ProjectConfig
from cogant.config import defaults as defaults_module
from cogant.config import presets as presets_module
from cogant.config.loaders import ConfigLoader, ConfigLoadError, ConfigMigrationWarning
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


def test_load_all_configs_returns_one_project_model() -> None:
    config = ConfigLoader.load_all_configs(preset="default")
    assert isinstance(config, ProjectConfig)
    assert config.cogant is not None
    assert config.export is not None
    assert config.validation is not None
    assert config.server is not None
    assert config.batch is not None


def test_legacy_flat_config_is_migrated_with_warning(tmp_path) -> None:
    path = tmp_path / "legacy.json"
    path.write_text(
        '{"output_dir": "legacy-output", "max_workers": 2, "schema_version": "0.9"}',
        encoding="utf-8",
    )
    with pytest.warns(ConfigMigrationWarning):
        config = ConfigLoader.load_project_config(path)
    assert config.schema_version == "1.0"
    assert config.pipeline.output_dir == "legacy-output"
    assert config.cogant.max_workers == 2


def test_legacy_environment_field_participates_in_precedence() -> None:
    with pytest.warns(ConfigMigrationWarning):
        config = ConfigLoader.load_project_config(
            environment={"COGANT_OUTPUT_DIR": "legacy-env"},
            cli={"pipeline": {"output_dir": "cli"}},
        )
    assert config.pipeline.output_dir == "cli"


def test_future_config_schema_is_rejected(tmp_path) -> None:
    path = tmp_path / "future.json"
    path.write_text('{"schema_version": "2.0"}\n', encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="Unsupported configuration schema_version"):
        ConfigLoader.load_project_config(path)


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
