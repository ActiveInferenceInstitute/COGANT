from pathlib import Path

import pytest

from tests.gnn_execution_fixture import MODEL, runner

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("preference,expected", [("0.0\n4.0", 1), ("4.0\n0.0", 0)])
def test_policy_choice_follows_exported_preferences(
    tmp_path: Path, preference: str, expected: int
) -> None:
    model = runner(tmp_path, MODEL.replace("0.0\n4.0", preference))
    result = model.run(1)
    scores = model.traces[0].policy_scores
    assert result["traces"][0]["action"] == scores[expected][0]
    assert scores[expected][1] < scores[1 - expected][1]


def test_repeated_rollout_does_not_penalize_preferred_action(tmp_path: Path) -> None:
    model = runner(tmp_path)
    result = model.run(6)
    assert list(result["action_distribution"].values()) == [1, 5]
    assert len({trace.action for trace in model.traces[1:]}) == 1
    assert all(trace.policy_scores == model.traces[1].policy_scores for trace in model.traces[1:])


def test_transition_change_changes_policy_choice(tmp_path: Path) -> None:
    text = MODEL.replace("# action=1\n0.0 0.0\n1.0 1.0", "# action=1\n1.0 1.0\n0.0 0.0")
    model = runner(tmp_path, text)
    model.run(1)
    scores = model.traces[0].policy_scores
    assert model.traces[0].action == scores[0][0]


def test_profile_trials_restart_from_prior_and_report_real_elapsed_time(tmp_path: Path) -> None:
    model = runner(tmp_path)
    traces, timing = model.run_with_profiling(num_steps=3, num_trials=2)
    assert len(traces) == 6
    assert traces[0]["beliefs_prior"] == traces[3]["beliefs_prior"]
    assert [t["trial"] for t in traces] == [0, 0, 0, 1, 1, 1]
    assert all(isinstance(t["action"], str) for t in traces)
    assert timing["total_ms"] > 0
    assert set(timing) == {"total_ms"}


@pytest.mark.parametrize("steps,trials", [(0, 1), (1, 0), (100, 101), (-1, 2), (1, True)])
def test_profile_limits_reject_invalid_work(tmp_path: Path, steps, trials) -> None:
    model = runner(tmp_path)
    with pytest.raises(ValueError):
        model.run_with_profiling(steps, trials)
    assert model.traces == []


def test_profiling_budget_bounds_combined_matrix_work(tmp_path: Path) -> None:
    size = 100
    identity = "\n".join(
        " ".join("1" if row == col else "0" for col in range(size)) for row in range(size)
    )
    likelihood = " ".join(["0.5"] * size)
    prior = "\n".join(["0.01"] * size)
    source = (
        "## ModelName\nBudget\n## State Space\n```gnn-matrices\n"
        f"A[[rows=2][cols={size}]]\n{likelihood}\n{likelihood}\n"
        f"B[[rows={size}][cols={size}][depth=2]]\n"
        f"# action=0\n{identity}\n# action=1\n{identity}\n"
        f"C[[rows=2][cols=1]]\n0\n0\nD[[rows={size}][cols=1]]\n{prior}\n```\n"
    )
    model = runner(tmp_path, source)
    with pytest.raises(ValueError, match="combined matrix-work budget"):
        model.run_with_profiling(1000, 5)
    assert model.traces == []
