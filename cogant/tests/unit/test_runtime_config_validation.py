from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

from cogant.runtime.config import AgentConfig

pytestmark = pytest.mark.unit


def test_default_config_is_valid() -> None:
    cfg = AgentConfig()
    assert cfg.max_steps == 100
    assert cfg.convergence_threshold == 1e-4
    assert AgentConfig(max_steps=0).max_steps == 0


@pytest.mark.parametrize("value", [-1, True, 1.5, "2"])
def test_invalid_max_steps_raises(value: object) -> None:
    with pytest.raises(ValueError, match="max_steps"):
        AgentConfig(**{"max_steps": value})


@pytest.mark.parametrize("value", [0.0, 1.0, -0.5, 2.0, float("nan"), True, "0.1"])
def test_invalid_convergence_threshold_raises(value: object) -> None:
    with pytest.raises(ValueError, match="convergence_threshold"):
        AgentConfig(**{"convergence_threshold": value})


@pytest.mark.parametrize(
    "text",
    [
        "action_selection: preference",
        "action_selection: entropy",
        "action_selection: random",
        "seed: 7",
        "unknown: true",
        "[]",
        "0",
        "false",
    ],
)
def test_from_yaml_rejects_removed_fields_and_wrong_shape(tmp_path: Path, text: str) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(text)
    with pytest.raises(ValueError):
        AgentConfig.from_yaml(str(path))


def test_from_yaml_loads_current_fields(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("max_steps: 200\nconvergence_threshold: 0.01\n")
    assert AgentConfig.from_yaml(str(path)) == AgentConfig(
        max_steps=200, convergence_threshold=0.01
    )


@pytest.mark.parametrize("text", ["", "max_steps: 100\n"])
def test_from_yaml_missing_keys_use_defaults(tmp_path: Path, text: str) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(text)
    assert AgentConfig.from_yaml(str(path)) == AgentConfig()


def test_from_yaml_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        AgentConfig.from_yaml(str(tmp_path / "missing.yaml"))


def test_from_yaml_invalid_value_propagates_validation(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("max_steps: -5\n")
    with pytest.raises(ValueError, match="max_steps"):
        AgentConfig.from_yaml(str(path))


def test_to_yaml_writes_only_supported_fields_and_roundtrips(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cfg = AgentConfig(max_steps=37, convergence_threshold=0.05)
    path = tmp_path / "config.yaml"
    with caplog.at_level(logging.INFO, logger="cogant.runtime.config"):
        cfg.to_yaml(str(path))
    assert yaml.safe_load(path.read_text()) == {"max_steps": 37, "convergence_threshold": 0.05}
    assert AgentConfig.from_yaml(str(path)) == cfg
    assert any("Saved AgentConfig" in record.message for record in caplog.records)


def test_with_defaults_returns_a_fresh_instance() -> None:
    left, right = AgentConfig.with_defaults(), AgentConfig.with_defaults()
    assert left == right == AgentConfig()
    assert left is not right
