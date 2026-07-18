"""Negative tests for the strict typed configuration boundary."""

from __future__ import annotations

import json

import pytest

from cogant.config import ProjectConfig
from cogant.config.loaders import ConfigLoader, ConfigLoadError


@pytest.mark.parametrize("payload", [[], ["pipeline"], "pipeline", 3, None])
def test_file_roots_must_be_objects(tmp_path, payload) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="mapping/object|JSON object"):
        ConfigLoader.load_json_from_file(path)


def test_yaml_file_loads_as_project_model(tmp_path) -> None:
    pytest.importorskip("yaml")
    path = tmp_path / "config.yaml"
    path.write_text("cogant:\n  log_level: debug\n", encoding="utf-8")
    config = ConfigLoader.load_from_yaml(path)
    assert isinstance(config, ProjectConfig)
    assert str(config.cogant.log_level) == "debug"


def test_missing_and_malformed_files_fail_with_config_error(tmp_path) -> None:
    with pytest.raises(ConfigLoadError):
        ConfigLoader.load_from_yaml(tmp_path / "missing.yaml")
    malformed = tmp_path / "bad.json"
    malformed.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigLoadError):
        ConfigLoader.load_json_from_file(malformed)


def test_unknown_keys_and_invalid_stages_are_rejected() -> None:
    with pytest.raises(ConfigLoadError):
        ConfigLoader.load_from_dict({"unknown": True})
    with pytest.raises(ConfigLoadError):
        ConfigLoader.load_from_dict({"pipeline": {"stages": ["not-a-stage"]}})


def test_invalid_paths_and_limits_are_rejected() -> None:
    with pytest.raises(ConfigLoadError):
        ConfigLoader.load_from_dict({"pipeline": {"output_dir": "../outside"}})
    with pytest.raises(ConfigLoadError):
        ConfigLoader.load_from_dict({"server": {"max_request_bytes": 1}})


def test_environment_keys_must_use_section_field_syntax() -> None:
    with pytest.raises(ConfigLoadError):
        ConfigLoader.load_project_config(environment={"COGANT_BAD": "1"})


def test_raw_mapping_merge_remains_a_boundary_utility() -> None:
    assert ConfigLoader.merge_configs(
        {"a": {"x": 1, "y": 2}}, {"a": {"y": 3}}
    ) == {"a": {"x": 1, "y": 3}}


def test_unknown_preset_is_typed_loader_error() -> None:
    with pytest.raises(ConfigLoadError):
        ConfigLoader.load_preset("not-a-preset")
