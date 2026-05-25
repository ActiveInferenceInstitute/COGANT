"""Targeted branch tests for ``cogant.gnn.runner``.

Targets the residual uncovered branches in ``runner.py``:

* Lines 180-181 — ``_load_active_inference_models`` exception branch.
* Lines 273-275 — Active-Inference step loop exception handler.
* Line 424 — Trace truncation marker (``len(traces) > 30``).
* Line 523 — ``_update_beliefs`` empty prior_beliefs early return.
* Lines 678-688 — ``_compute_coverage_score``.
* Lines 773 / 789 — Positive-path assessment markers (multiple actions /
  belief convergence).
* Lines 798 / 800 — Positive-count branches in
  ``_assess_model_quality`` (3+ ✓ → "good", 2 ✓ → "decent").
* Lines 826-903 — ``run_with_profiling`` end-to-end.

All tests use real GNN packages on disk (``tmp_path`` fixture) and
real ``GNNModelRunner`` instances. No mocks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cogant.gnn.runner import ExecutionTrace, GNNModelRunner

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------- helpers


def _write_minimal_package(
    tmp_path: Path,
    *,
    with_transitions: bool = False,
    with_preferences: bool = False,
    n_actions: int = 2,
    n_observations: int = 2,
    n_variables: int = 2,
    bad_transitions: bool = False,
) -> Path:
    """Write a minimal GNN package directory."""
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    manifest = {
        "version": "1.0",
        "name": "test_pkg",
    }
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest))

    model: dict[str, Any] = {"type": "active_inference", "version": "1"}
    (pkg_dir / "model.gnn.json").write_text(json.dumps(model))

    state_space: dict[str, Any] = {
        "variables": [
            {"name": f"var_{i}", "type": "discrete"} for i in range(n_variables)
        ],
        "observations": [
            {"name": f"var_{i}", "type": "discrete"} for i in range(n_observations)
        ],
        "actions": [{"name": f"act_{i}"} for i in range(n_actions)],
    }
    (pkg_dir / "state_space.json").write_text(json.dumps(state_space))

    if with_transitions:
        if bad_transitions:
            # Write a broken JSON to trip the exception branch.
            (pkg_dir / "transitions.json").write_text("{not valid json")
        else:
            (pkg_dir / "transitions.json").write_text(json.dumps({"transitions": []}))
    if with_preferences:
        (pkg_dir / "preferences.json").write_text(json.dumps({"preferences": []}))

    return pkg_dir


# ============================================================ load_package edge cases


class TestLoadPackageExceptionPath:
    """Cover lines 180-181: malformed transitions.json triggers the broad except."""

    def test_load_with_bad_transitions_json(self, tmp_path: Path) -> None:
        pkg = _write_minimal_package(
            tmp_path, with_transitions=True, bad_transitions=True
        )
        runner = GNNModelRunner()
        # Bad JSON inside transitions.json triggers JSONDecodeError, which
        # is logged at warning level and not propagated.
        manifest = runner.load_package(str(pkg))
        assert manifest["version"] == "1.0"

    def test_load_with_valid_optional_files(self, tmp_path: Path) -> None:
        pkg = _write_minimal_package(
            tmp_path, with_transitions=True, with_preferences=True
        )
        runner = GNNModelRunner()
        manifest = runner.load_package(str(pkg))
        assert manifest["version"] == "1.0"

    def test_load_missing_manifest_raises(self, tmp_path: Path) -> None:
        pkg = tmp_path / "empty"
        pkg.mkdir()
        runner = GNNModelRunner()
        with pytest.raises(FileNotFoundError, match="Manifest not found"):
            runner.load_package(str(pkg))


# ============================================================ run() exception path


class TestRunStepException:
    """Cover lines 273-275: a step raising an exception stops the loop cleanly.

    The path is reached when one of the per-step helpers raises. We
    monkey-patch ``_compute_transition`` to raise on the second call.
    """

    def test_run_step_exception_stops_loop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pkg = _write_minimal_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(pkg))

        original = runner._compute_transition
        call_count = {"n": 0}

        def fake_transition(state, action):  # type: ignore[no-untyped-def]
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise RuntimeError("forced for coverage")
            return original(state, action)

        monkeypatch.setattr(runner, "_compute_transition", fake_transition)
        result = runner.run(steps=10)
        # Loop broke after the first successful step.
        assert result["steps_completed"] == 1


# ============================================================ trace truncation


class TestTraceTruncation:
    """Cover line 424: ``len(traces) > 30`` adds a truncation marker."""

    def test_report_truncates_at_30_traces(self, tmp_path: Path) -> None:
        pkg = _write_minimal_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(pkg))
        result = runner.run(steps=35)
        report = runner.generate_execution_report(trace=result)
        # Truncation marker is appended when more than 30 steps run.
        assert "more steps" in report

    def test_report_no_truncation_below_30_traces(self, tmp_path: Path) -> None:
        pkg = _write_minimal_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(pkg))
        result = runner.run(steps=5)
        report = runner.generate_execution_report(trace=result)
        # No truncation marker for short runs.
        assert "more steps" not in report


# ============================================================ _update_beliefs empty


class TestUpdateBeliefsEmpty:
    """Cover line 523: ``_update_beliefs`` returns the prior unchanged when empty."""

    def test_empty_prior_returns_empty(self) -> None:
        runner = GNNModelRunner()
        result = runner._update_beliefs({}, "any_obs")
        assert result == {}


# ============================================================ coverage score


class TestComputeCoverageScore:
    """Cover lines 678-688: ``_compute_coverage_score`` branches."""

    def test_no_state_space_default(self) -> None:
        runner = GNNModelRunner()
        # state_space is the empty dict by default.
        runner.state_space = {}
        score = runner._compute_coverage_score([])
        assert score == 0.5

    def test_zero_total_possible_states_default(self) -> None:
        runner = GNNModelRunner()
        # state_space exists but has no observations or variables.
        runner.state_space = {"variables": [], "observations": []}
        score = runner._compute_coverage_score([])
        assert score == 0.5

    def test_coverage_caps_at_1(self) -> None:
        runner = GNNModelRunner()
        runner.state_space = {
            "variables": [{"name": "v0"}, {"name": "v1"}],
            "observations": [{"name": "o0"}, {"name": "o1"}],
        }
        # 4 possible states. Provide 5 traces → coverage > 1 → capped at 1.0.
        traces = [
            {"state": {"v0": i}} for i in range(5)
        ]
        score = runner._compute_coverage_score(traces)
        assert score == 1.0

    def test_coverage_partial(self) -> None:
        runner = GNNModelRunner()
        runner.state_space = {
            "variables": [{"name": "v0"}, {"name": "v1"}, {"name": "v2"}, {"name": "v3"}],
            "observations": [{"name": "o0"}, {"name": "o1"}, {"name": "o2"}, {"name": "o3"}],
        }
        # 16 possible states; 4 unique traces → 0.25.
        traces = [
            {"state": {"v0": 0}},
            {"state": {"v0": 1}},
            {"state": {"v0": 2}},
            {"state": {"v0": 3}},
        ]
        score = runner._compute_coverage_score(traces)
        assert score == pytest.approx(0.25)


# ============================================================ assessment branches


class TestAssessmentMultiplePositiveBranches:
    """Cover positive-path lines 773 (action diversity) and 789 (belief convergence)
    plus 798 (3+ ✓ → "good") and 800 (2 ✓ → "decent")."""

    def test_assessment_with_action_diversity_and_convergence(self) -> None:
        runner = GNNModelRunner()
        # Construct synthetic traces / fe_trajectory / stats so that the
        # assessment hits the success-side branches.
        stats = {
            "unique_states": 3,
            "unique_actions": 4,  # >1 → ✓ diverse actions
            "uncertainty_reduction": 0.5,  # >0 → ✓ converging
        }
        fe_trajectory = [3.0, 2.5, 2.0, 1.5, 1.0]  # decreasing → ✓ minimized
        report = runner._assess_model_quality(
            traces=[{}],
            fe_trajectory=fe_trajectory,
            stats=stats,
        )
        # All four ✓ markers should appear.
        assert "Policy evaluation produced diverse actions" in report
        assert "Beliefs converging" in report
        # 4+ ✓ → 3+ branch → "good"
        assert "Model demonstrates good Active Inference dynamics" in report

    def test_assessment_with_two_positive_signs(self) -> None:
        """Stats arranged so exactly 2 of 4 ✓ markers appear → "decent" path."""
        runner = GNNModelRunner()
        stats = {
            "unique_states": 2,  # >1 → ✓ states
            "unique_actions": 1,  # not >1 → ⚠
            "uncertainty_reduction": 0.0,  # not >0 → ⚠
        }
        fe_trajectory = [1.0, 0.5]  # final < initial → ✓ minimized
        report = runner._assess_model_quality(
            traces=[{}],
            fe_trajectory=fe_trajectory,
            stats=stats,
        )
        # Exactly 2 ✓ → "decent" branch (line 800).
        assert "decent Active Inference behavior" in report

    def test_assessment_with_zero_positive_signs(self) -> None:
        """Stats arranged so no ✓ markers appear → "needs refinement" path."""
        runner = GNNModelRunner()
        stats = {
            "unique_states": 1,
            "unique_actions": 1,
            "uncertainty_reduction": -0.1,
        }
        fe_trajectory = [0.5, 1.0]  # final > initial → ⚠
        report = runner._assess_model_quality(
            traces=[{}],
            fe_trajectory=fe_trajectory,
            stats=stats,
        )
        assert "needs refinement" in report


# ============================================================ run_with_profiling


class TestRunWithProfiling:
    """Cover lines 826-903: ``run_with_profiling`` end-to-end."""

    def test_run_with_profiling_default(self, tmp_path: Path) -> None:
        pkg = _write_minimal_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(pkg))
        traces, timing = runner.run_with_profiling(num_steps=3, num_trials=1)
        # 3 steps × 1 trial → 3 trace entries.
        assert len(traces) == 3
        # Timing dict has all expected keys.
        for key in (
            "belief_update_ms",
            "policy_eval_ms",
            "action_select_ms",
            "state_update_ms",
            "observation_ms",
            "total_ms",
        ):
            assert key in timing
            assert timing[key] >= 0.0

    def test_run_with_profiling_multiple_trials(self, tmp_path: Path) -> None:
        pkg = _write_minimal_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(pkg))
        traces, timing = runner.run_with_profiling(num_steps=2, num_trials=3)
        # 2 × 3 = 6 traces.
        assert len(traces) == 6
        # Total time should be positive.
        assert timing["total_ms"] >= 0.0

    def test_profiling_traces_include_step_numbers(self, tmp_path: Path) -> None:
        pkg = _write_minimal_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(pkg))
        traces, _ = runner.run_with_profiling(num_steps=2, num_trials=2)
        # Step numbers run 0..3 across trials.
        steps = [t["step"] for t in traces]
        assert steps == [0, 1, 2, 3]


# ============================================================ ExecutionTrace


class TestExecutionTraceDefaults:
    def test_minimal_construction(self) -> None:
        trace = ExecutionTrace(step=0, state={"x": 1})
        assert trace.step == 0
        assert trace.beliefs == {}
        assert trace.beliefs_prior == {}
        assert trace.policy_scores == []
        assert trace.predicted_state == {}

    def test_to_dict_includes_all_fields(self) -> None:
        trace = ExecutionTrace(
            step=1,
            state={"x": 1},
            action="act",
            observation="obs",
            reward=0.5,
            beliefs={"s1": 0.7, "s2": 0.3},
            free_energy_before=1.0,
            free_energy_after=0.5,
            policy_scores=[("a1", 0.1)],
            action_rationale="why",
            predicted_state={"x": 2},
        )
        d = trace.to_dict()
        assert d["step"] == 1
        assert d["action"] == "act"
        assert d["observation"] == "obs"
        assert d["reward"] == 0.5
        assert d["beliefs"] == {"s1": 0.7, "s2": 0.3}
        assert d["free_energy_before"] == 1.0
        assert d["free_energy_after"] == 0.5
        assert d["policy_scores"] == [("a1", 0.1)]
        assert d["action_rationale"] == "why"
        assert d["predicted_state"] == {"x": 2}


# ============================================================ generate_execution_report


class TestReportEdgeCases:
    def test_empty_report_when_no_traces(self) -> None:
        runner = GNNModelRunner()
        report = runner.generate_execution_report()
        assert "No traces to report" in report

    def test_report_uses_runner_state_when_no_trace_arg(self, tmp_path: Path) -> None:
        pkg = _write_minimal_package(tmp_path)
        runner = GNNModelRunner()
        runner.load_package(str(pkg))
        runner.run(steps=3)
        report = runner.generate_execution_report()
        assert "GNN Model Execution Report" in report
        assert "Steps Completed" in report


# ============================================================ run() not loaded


class TestRunRequiresPackage:
    def test_run_without_load_raises(self) -> None:
        runner = GNNModelRunner()
        with pytest.raises(RuntimeError, match="Package not loaded"):
            runner.run(steps=1)


# ============================================================ default fallbacks


class TestPrivateMethodDefaults:
    """Cover the empty-state-space default-return branches.

    Lines 453, 463, 482, 543, 582, 586, 621, 711.
    """

    def test_initialize_beliefs_default(self) -> None:
        """Cover line 453: empty state_space → ``{"state_0": 0.5, "state_1": 0.5}``."""
        runner = GNNModelRunner()
        result = runner._initialize_beliefs()
        assert result == {"state_0": 0.5, "state_1": 0.5}

    def test_initialize_state_default(self) -> None:
        """Cover line 463: empty state_space → ``{"initial": True}``."""
        runner = GNNModelRunner()
        result = runner._initialize_state()
        assert result == {"initial": True}

    def test_generate_observation_default(self) -> None:
        """Cover line 482: empty state_space → ``"obs_0"``."""
        runner = GNNModelRunner()
        result = runner._generate_observation({"x": 1})
        assert result == "obs_0"

    def test_compute_vfe_empty_beliefs(self) -> None:
        """Cover line 543: empty beliefs → 0.0 VFE."""
        runner = GNNModelRunner()
        assert runner._compute_vfe({}, "any_obs") == 0.0

    def test_evaluate_policies_no_state_space(self) -> None:
        """Cover line 582: no state_space → []."""
        runner = GNNModelRunner()
        runner.state_space = {}
        assert runner._evaluate_policies({"s1": 0.5, "s2": 0.5}) == []

    def test_evaluate_policies_no_actions(self) -> None:
        """Cover line 586: empty actions list → []."""
        runner = GNNModelRunner()
        runner.state_space = {"actions": []}
        assert runner._evaluate_policies({"s1": 0.5, "s2": 0.5}) == []

    def test_select_action_no_policy_scores(self) -> None:
        """Cover line 621: empty policy_scores → ``("default_action", ...)``."""
        runner = GNNModelRunner()
        action, rationale = runner._select_action_active_inference(
            beliefs={"s1": 0.5, "s2": 0.5}, policy_scores=[]
        )
        assert action == "default_action"
        assert "No actions" in rationale

    def test_compute_statistics_no_traces(self) -> None:
        """Cover line 711: no traces → {}."""
        runner = GNNModelRunner()
        runner.traces = []
        assert runner._compute_statistics() == {}


class TestUpdateBeliefsZeroTotal:
    """Cover line 523: when total likelihood is 0, return prior unchanged."""

    def test_update_beliefs_with_zero_priors_returns_unchanged(self) -> None:
        runner = GNNModelRunner()
        # All-zero prior → posterior_unnormalized totals 0 → fallback returns prior.
        # Note: prior_beliefs must be truthy (not empty dict) to reach this path.
        prior = {"s1": 0.0, "s2": 0.0}
        result = runner._update_beliefs(prior, "any_obs")
        assert result == prior


# ============================================================ alias


class TestLoadGNNPackageAlias:
    """The module-level ``load_gnn_package`` alias works as a function."""

    def test_alias_loads_package(self, tmp_path: Path) -> None:
        from cogant.gnn.runner import load_gnn_package

        pkg = _write_minimal_package(tmp_path)
        manifest = load_gnn_package(str(pkg))
        assert manifest["version"] == "1.0"
