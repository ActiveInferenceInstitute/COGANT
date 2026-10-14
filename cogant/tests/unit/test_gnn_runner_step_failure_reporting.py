"""``GNNModelRunner.run`` reports step failures instead of claiming success.

* A run whose steps raise must report ``success=False`` with the error and
  the failing step, and the execution report must not claim the run
  completed successfully.
* A package with actions but no hidden-state variables (e.g. the shipped
  ``plugin_architecture`` fixture: 0 variables, 3 actions) must still run:
  action selection may not crash on an empty belief distribution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cogant.gnn.runner import GNNModelRunner

pytestmark = pytest.mark.unit


def _package(tmp_path: Path, state_space: dict[str, Any]) -> GNNModelRunner:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"version": "1.0"}))
    (pkg / "model.gnn.json").write_text(json.dumps({}))
    (pkg / "state_space.json").write_text(json.dumps(state_space))
    runner = GNNModelRunner()
    runner.load_package(str(pkg))
    return runner


def _state_space(n_vars: int = 2, n_actions: int = 3) -> dict[str, Any]:
    return {
        "variables": [{"name": f"var_{i}"} for i in range(n_vars)],
        "observations": [{"name": "obs_0"}, {"name": "obs_1"}],
        "actions": [{"name": f"act_{k}"} for k in range(n_actions)],
    }


def test_run_reports_failure_when_a_step_raises(tmp_path: Path) -> None:
    state_space = _state_space()
    state_space["actions"] = ["not-an-action-object"]
    runner = _package(tmp_path, state_space)

    result = runner.run(steps=4)

    assert result["success"] is False
    assert result["steps_completed"] == 0
    assert "AttributeError" in result["error"]
    assert result["failed_step"] == 0
    report = runner.generate_execution_report(result)
    assert "completed successfully" not in report
    assert "stopped at step 0" in report


def test_report_of_last_run_reflects_mid_run_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _package(tmp_path, _state_space())
    original = runner._compute_transition
    calls = {"n": 0}

    def transition_failing_on_third_step(state: dict[str, Any], action: str) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("transition model unavailable")
        return original(state, action)

    monkeypatch.setattr(runner, "_compute_transition", transition_failing_on_third_step)
    result = runner.run(steps=5)

    assert result["success"] is False
    assert result["steps_completed"] == 2
    assert result["failed_step"] == 2
    report = runner.generate_execution_report()
    assert "completed successfully" not in report
    assert "stopped at step 2" in report
    assert "transition model unavailable" in report


def test_successful_run_reports_no_error(tmp_path: Path) -> None:
    result = _package(tmp_path, _state_space()).run(steps=3)

    assert result["success"] is True
    assert result["error"] is None
    assert result["failed_step"] is None
    assert result["steps_completed"] == 3


def test_run_without_hidden_states_selects_actions(tmp_path: Path) -> None:
    runner = _package(tmp_path, _state_space(n_vars=0))

    result = runner.run(steps=5)

    assert result["success"] is True
    assert result["steps_completed"] == 5
    assert sum(result["action_distribution"].values()) == 5
