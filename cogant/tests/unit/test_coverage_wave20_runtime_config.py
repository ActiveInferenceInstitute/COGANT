"""Coverage wave 20: cogant.runtime.config — AgentConfig validation, YAML I/O.

Targets uncovered lines in py/cogant/runtime/config.py:
* line 43: max_steps < 0 raises ValueError
* line 46: convergence_threshold out of (0, 1) raises ValueError
* line 51: unknown action_selection emits a warning (no exception)
* lines 74-84: from_yaml roundtrip + missing-keys default
* lines 104-121: to_yaml writes a parseable file
* line 135: with_defaults returns a fresh default-valued instance

No mocks: real tmp files, real yaml roundtrip.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

from cogant.runtime.config import AgentConfig

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# __post_init__ validation
# --------------------------------------------------------------------------- #


def test_default_config_is_valid() -> None:
    cfg = AgentConfig()
    assert cfg.max_steps == 100
    assert cfg.convergence_threshold == 1e-4
    assert cfg.action_selection == "preference"
    assert cfg.seed == 42


def test_max_steps_zero_is_allowed() -> None:
    """max_steps==0 is the boundary; only negative values raise."""
    cfg = AgentConfig(max_steps=0)
    assert cfg.max_steps == 0


def test_max_steps_negative_raises() -> None:
    with pytest.raises(ValueError, match="max_steps must be non-negative"):
        AgentConfig(max_steps=-1)


def test_convergence_threshold_zero_raises() -> None:
    """The lower bound is exclusive."""
    with pytest.raises(ValueError, match="convergence_threshold"):
        AgentConfig(convergence_threshold=0.0)


def test_convergence_threshold_one_raises() -> None:
    """The upper bound is exclusive."""
    with pytest.raises(ValueError, match="convergence_threshold"):
        AgentConfig(convergence_threshold=1.0)


def test_convergence_threshold_negative_raises() -> None:
    with pytest.raises(ValueError, match="convergence_threshold"):
        AgentConfig(convergence_threshold=-0.5)


def test_convergence_threshold_above_one_raises() -> None:
    with pytest.raises(ValueError, match="convergence_threshold"):
        AgentConfig(convergence_threshold=2.0)


def test_action_selection_preference_accepted() -> None:
    cfg = AgentConfig(action_selection="preference")
    assert cfg.action_selection == "preference"


def test_action_selection_entropy_accepted() -> None:
    cfg = AgentConfig(action_selection="entropy")
    assert cfg.action_selection == "entropy"


def test_action_selection_unknown_warns_but_does_not_raise(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unknown strategy logs a warning, retains the value, does not raise."""
    with caplog.at_level(logging.WARNING, logger="cogant.runtime.config"):
        cfg = AgentConfig(action_selection="random")
    assert cfg.action_selection == "random"
    # Warning was emitted
    assert any("Unknown action_selection" in rec.message for rec in caplog.records)


# --------------------------------------------------------------------------- #
# from_yaml
# --------------------------------------------------------------------------- #


def test_from_yaml_loads_all_fields(tmp_path: Path) -> None:
    """All four fields are read from a populated YAML file."""
    p = tmp_path / "cfg.yaml"
    p.write_text(
        "max_steps: 200\n"
        "convergence_threshold: 0.01\n"
        "action_selection: entropy\n"
        "seed: 7\n",
        encoding="utf-8",
    )
    cfg = AgentConfig.from_yaml(str(p))
    assert cfg.max_steps == 200
    assert cfg.convergence_threshold == 0.01
    assert cfg.action_selection == "entropy"
    assert cfg.seed == 7


def test_from_yaml_missing_keys_use_defaults(tmp_path: Path) -> None:
    """Empty YAML (or missing keys) falls back to AgentConfig defaults."""
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")  # safe_load returns None → handled
    cfg = AgentConfig.from_yaml(str(p))
    assert cfg.max_steps == 100
    assert cfg.convergence_threshold == 1e-4
    assert cfg.action_selection == "preference"
    assert cfg.seed == 42


def test_from_yaml_partial_keys(tmp_path: Path) -> None:
    """Only some keys present — others fall back to defaults."""
    p = tmp_path / "partial.yaml"
    p.write_text("max_steps: 50\n", encoding="utf-8")
    cfg = AgentConfig.from_yaml(str(p))
    assert cfg.max_steps == 50
    # Defaults for the rest
    assert cfg.convergence_threshold == 1e-4
    assert cfg.seed == 42


def test_from_yaml_missing_file_raises(tmp_path: Path) -> None:
    p = tmp_path / "nonexistent.yaml"
    with pytest.raises(FileNotFoundError):
        AgentConfig.from_yaml(str(p))


def test_from_yaml_invalid_max_steps_propagates_validation_error(
    tmp_path: Path,
) -> None:
    """YAML loaded with an invalid value triggers __post_init__ ValueError."""
    p = tmp_path / "bad.yaml"
    p.write_text("max_steps: -5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="max_steps"):
        AgentConfig.from_yaml(str(p))


# --------------------------------------------------------------------------- #
# to_yaml
# --------------------------------------------------------------------------- #


def test_to_yaml_writes_parseable_file(tmp_path: Path) -> None:
    """to_yaml output is valid YAML with the expected keys."""
    cfg = AgentConfig(
        max_steps=37,
        convergence_threshold=0.05,
        action_selection="preference",
        seed=123,
    )
    p = tmp_path / "out.yaml"
    cfg.to_yaml(str(p))
    assert p.exists()

    raw = p.read_text(encoding="utf-8")
    # default_flow_style=False uses block style; each key on its own line
    assert "max_steps: 37" in raw
    assert "seed: 123" in raw

    # Parse round-trip
    parsed = yaml.safe_load(raw)
    assert parsed["max_steps"] == 37
    assert parsed["convergence_threshold"] == 0.05
    assert parsed["action_selection"] == "preference"
    assert parsed["seed"] == 123


def test_to_yaml_then_from_yaml_roundtrips(tmp_path: Path) -> None:
    """Saving and loading reproduces the original config."""
    original = AgentConfig(
        max_steps=88,
        convergence_threshold=0.001,
        action_selection="entropy",
        seed=2024,
    )
    p = tmp_path / "round.yaml"
    original.to_yaml(str(p))
    restored = AgentConfig.from_yaml(str(p))
    assert restored == original


def test_to_yaml_emits_info_log(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cfg = AgentConfig()
    p = tmp_path / "log.yaml"
    with caplog.at_level(logging.INFO, logger="cogant.runtime.config"):
        cfg.to_yaml(str(p))
    assert any("Saved AgentConfig" in rec.message for rec in caplog.records)


# --------------------------------------------------------------------------- #
# with_defaults
# --------------------------------------------------------------------------- #


def test_with_defaults_returns_new_instance() -> None:
    cfg1 = AgentConfig.with_defaults()
    cfg2 = AgentConfig.with_defaults()
    assert cfg1 is not cfg2
    assert cfg1 == cfg2


def test_with_defaults_matches_default_constructor() -> None:
    """with_defaults() is equivalent to AgentConfig()."""
    assert AgentConfig.with_defaults() == AgentConfig()
