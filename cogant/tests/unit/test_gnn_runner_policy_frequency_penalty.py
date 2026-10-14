"""``GNNModelRunner`` penalises repeated actions and profiles action names.

* The frequency term in Expected Free Energy is documented as a penalty
  that encourages exploration. Since the lowest EFE wins, frequently
  chosen actions must get a *higher* EFE, so the policy rotates instead
  of locking onto the first action forever.
* ``run_with_profiling`` must record action names (not the
  ``(action, rationale)`` tuple returned by action selection) in traces
  and in the transition's state keys.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cogant.gnn.runner import GNNModelRunner

pytestmark = pytest.mark.unit


def _runner(tmp_path: Path, n_actions: int) -> GNNModelRunner:
    state_space: dict[str, Any] = {
        "variables": [{"name": "var_0"}, {"name": "var_1"}],
        "observations": [{"name": "obs_0"}, {"name": "obs_1"}],
        "actions": [{"name": f"act_{k}"} for k in range(n_actions)],
    }
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"version": "1.0"}))
    (pkg / "model.gnn.json").write_text(json.dumps({}))
    (pkg / "state_space.json").write_text(json.dumps(state_space))
    runner = GNNModelRunner()
    runner.load_package(str(pkg))
    return runner


def test_frequently_chosen_actions_score_higher_efe(tmp_path: Path) -> None:
    runner = _runner(tmp_path, n_actions=2)
    runner.action_counts["act_0"] = 3

    scores = dict(runner._evaluate_policies({"var_0": 0.5, "var_1": 0.5}))

    assert scores["act_0"] > scores["act_1"]


def test_run_rotates_through_actions(tmp_path: Path) -> None:
    result = _runner(tmp_path, n_actions=3).run(steps=6)

    assert result["action_distribution"] == {"act_0": 2, "act_1": 2, "act_2": 2}


def test_profiling_traces_record_action_names(tmp_path: Path) -> None:
    runner = _runner(tmp_path, n_actions=2)

    traces, _timing = runner.run_with_profiling(num_steps=4)

    actions = [t["action"] for t in traces]
    assert all(isinstance(a, str) for a in actions)
    assert set(actions) == {"act_0", "act_1"}
    for trace in traces:
        assert all(
            not key.startswith("step_result_") or key.removeprefix("step_result_") in actions
            for key in trace["state"]
        )
