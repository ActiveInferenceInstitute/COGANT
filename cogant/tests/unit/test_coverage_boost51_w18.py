#!/usr/bin/env python3
"""Coverage boost batch 51 — reverse/parser.py helper functions and gnn/runner.py
deeper Active Inference methods.

Covers:
- reverse/parser.py: _split_sections, _parse_cardinality_and_type, _parse_tuple_vector,
  _parse_state_space_block, parse_gnn (str input, Path input, full GNN block),
  ReverseGNNModel properties (n_states, n_obs, n_actions), _sanitize_identifier
- gnn/runner.py: _update_beliefs, _compute_vfe, _evaluate_policies,
  _compute_transition, _compute_reward, _count_unique_states, _count_unique_actions,
  _entropy, generate_execution_report (no-trace path, with beliefs_history)
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# reverse/parser.py — low-level helper functions
# ---------------------------------------------------------------------------

class TestReverseParseSplitSections:
    def test_split_empty_string(self):
        from cogant.reverse.parser import _split_sections
        result = _split_sections("")
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_split_single_section(self):
        from cogant.reverse.parser import _split_sections
        text = "## ModelName\nMyModel\n"
        result = _split_sections(text)
        assert "ModelName" in result
        assert isinstance(result["ModelName"], list)
        assert len(result["ModelName"]) == 1

    def test_split_multiple_sections(self):
        from cogant.reverse.parser import _split_sections
        text = "## ModelName\nDemo\n\n## StateSpaceBlock\ns_f0[2,1]\n"
        result = _split_sections(text)
        assert "ModelName" in result
        assert "StateSpaceBlock" in result

    def test_split_duplicate_section(self):
        from cogant.reverse.parser import _split_sections
        text = "## Connections\nedge1\n\n## Connections\nedge2\n"
        result = _split_sections(text)
        assert "Connections" in result
        # Should have two bodies for the duplicate section
        assert len(result["Connections"]) == 2


class TestReverseParseCardinalityAndType:
    def test_cardinality_only(self):
        from cogant.reverse.parser import _parse_cardinality_and_type
        card, type_str = _parse_cardinality_and_type("10,1")
        assert card == 10
        assert type_str is None

    def test_cardinality_with_type(self):
        from cogant.reverse.parser import _parse_cardinality_and_type
        card, type_str = _parse_cardinality_and_type("5,1,type=int")
        assert card == 5
        assert type_str == "int"

    def test_type_only_no_digit(self):
        from cogant.reverse.parser import _parse_cardinality_and_type
        card, type_str = _parse_cardinality_and_type("type=float")
        assert card is None
        assert type_str == "float"

    def test_empty_string(self):
        from cogant.reverse.parser import _parse_cardinality_and_type
        card, type_str = _parse_cardinality_and_type("")
        assert card is None
        assert type_str is None


class TestReverseParseVectorAndStateSpace:
    def test_parse_tuple_vector_basic(self):
        from cogant.reverse.parser import _parse_tuple_vector
        result = _parse_tuple_vector("(0.1, 0.2, 0.7)")
        assert len(result) == 3
        assert abs(result[0] - 0.1) < 1e-9
        assert abs(result[2] - 0.7) < 1e-9

    def test_parse_tuple_vector_empty(self):
        from cogant.reverse.parser import _parse_tuple_vector
        result = _parse_tuple_vector("")
        assert result == []

    def test_parse_tuple_vector_nested(self):
        from cogant.reverse.parser import _parse_tuple_vector
        result = _parse_tuple_vector("((0.5, 0.5), (0.3, 0.7))")
        assert len(result) == 4

    def test_parse_state_space_block_hidden_states(self):
        from cogant.reverse.parser import _parse_state_space_block, ReverseGNNModel
        model = ReverseGNNModel()
        body = "s_f0[2,1,type=int]\ns_f1[3,1,type=int]\n"
        _parse_state_space_block(body, model)
        assert len(model.hidden_states) == 2
        assert "s_f0" in model.hidden_states
        assert "s_f1" in model.hidden_states

    def test_parse_state_space_block_observations(self):
        from cogant.reverse.parser import _parse_state_space_block, ReverseGNNModel
        model = ReverseGNNModel()
        body = "o_m0[4,1]\no_m1[2,1]\n"
        _parse_state_space_block(body, model)
        assert len(model.observations) == 2

    def test_parse_state_space_block_actions(self):
        from cogant.reverse.parser import _parse_state_space_block, ReverseGNNModel
        model = ReverseGNNModel()
        body = "u_c0[3,1]\n"
        _parse_state_space_block(body, model)
        assert len(model.actions) == 1

    def test_parse_state_space_block_cardinalities(self):
        from cogant.reverse.parser import _parse_state_space_block, ReverseGNNModel
        model = ReverseGNNModel()
        body = "s_f0[5,1,type=str]\n"
        _parse_state_space_block(body, model)
        assert model.cardinalities.get("s_f0") == 5

    def test_parse_state_space_block_comment_lines_skipped(self):
        from cogant.reverse.parser import _parse_state_space_block, ReverseGNNModel
        model = ReverseGNNModel()
        body = "# This is a comment\ns_f0[2,1]\n"
        _parse_state_space_block(body, model)
        assert len(model.hidden_states) == 1


class TestReverseGNNModelProperties:
    def test_n_states_empty(self):
        from cogant.reverse.parser import ReverseGNNModel
        model = ReverseGNNModel()
        assert model.n_states == 0

    def test_n_obs_empty(self):
        from cogant.reverse.parser import ReverseGNNModel
        model = ReverseGNNModel()
        assert model.n_obs == 0

    def test_n_actions_empty(self):
        from cogant.reverse.parser import ReverseGNNModel
        model = ReverseGNNModel()
        assert model.n_actions == 0

    def test_n_states_after_parse(self):
        from cogant.reverse.parser import _parse_state_space_block, ReverseGNNModel
        model = ReverseGNNModel()
        _parse_state_space_block("s_f0[2,1]\ns_f1[3,1]\n", model)
        assert model.n_states == 2

    def test_model_default_fields(self):
        from cogant.reverse.parser import ReverseGNNModel
        model = ReverseGNNModel()
        assert isinstance(model.raw_model_name, str)
        assert isinstance(model.model_name, str)
        assert isinstance(model.hidden_states, list)
        assert isinstance(model.annotations, dict)
        assert isinstance(model.cardinalities, dict)


class TestParseGNN:
    def test_parse_gnn_empty_string(self):
        from cogant.reverse.parser import parse_gnn
        model = parse_gnn("")
        assert model.n_states == 0

    def test_parse_gnn_with_model_name(self):
        from cogant.reverse.parser import parse_gnn
        gnn = "## ModelName\nMyDemo\n"
        model = parse_gnn(gnn)
        assert model.raw_model_name == "MyDemo"

    def test_parse_gnn_with_state_space_block(self):
        from cogant.reverse.parser import parse_gnn
        gnn = (
            "## ModelName\nDemo\n\n"
            "## StateSpaceBlock\n"
            "s_f0[2,1,type=int]\n"
            "o_m0[3,1,type=int]\n"
            "u_c0[2,1]\n"
        )
        model = parse_gnn(gnn)
        assert model.n_states == 1
        assert model.n_obs == 1
        assert model.n_actions == 1

    def test_parse_gnn_from_path(self, tmp_path):
        from cogant.reverse.parser import parse_gnn
        gnn_file = tmp_path / "demo.gnn.md"
        gnn_file.write_text(
            "## ModelName\nPathModel\n\n"
            "## StateSpaceBlock\n"
            "s_f0[2,1]\n"
        )
        model = parse_gnn(gnn_file)
        assert model.raw_model_name == "PathModel"
        assert model.n_states == 1

    def test_parse_gnn_type_error(self):
        from cogant.reverse.parser import parse_gnn
        with pytest.raises(TypeError):
            parse_gnn(42)  # type: ignore[arg-type]

    def test_parse_gnn_sanitize_identifier(self):
        from cogant.reverse.parser import _sanitize_identifier
        result = _sanitize_identifier("My Model With Spaces!")
        # Identifier should be valid Python identifier chars
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# gnn/runner.py — Active Inference helper methods
# ---------------------------------------------------------------------------

def _make_runner_with_state():
    """Return a GNNModelRunner with minimal state loaded."""
    from cogant.gnn.runner import GNNModelRunner
    runner = GNNModelRunner()
    runner.package_dir = Path("/nonexistent")
    runner.manifest = {}
    runner.state_space = {
        "variables": {"s_f0": {"values": ["low", "high"]}, "s_f1": {"values": ["off", "on"]}},
        "observations": {"o_m0": {"values": ["obs_a", "obs_b"]}},
    }
    runner.observations = {}
    runner.actions = ["action_a", "action_b"]
    runner.preferences = {}
    runner.traces = []
    runner.beliefs_history = []
    runner.free_energy_trajectory = []
    runner.action_counts = {}
    return runner


class TestGNNModelRunnerActiveInference:
    def test_update_beliefs_empty(self):
        runner = _make_runner_with_state()
        result = runner._update_beliefs({}, "obs_0")
        assert result == {}

    def test_update_beliefs_normalizes(self):
        runner = _make_runner_with_state()
        prior = {"state_a": 0.5, "state_b": 0.5}
        posterior = runner._update_beliefs(prior, "state_a")
        total = sum(posterior.values())
        assert abs(total - 1.0) < 1e-9
        assert isinstance(posterior, dict)

    def test_update_beliefs_matching_obs(self):
        runner = _make_runner_with_state()
        prior = {"state_a": 0.5, "state_b": 0.5}
        posterior = runner._update_beliefs(prior, "state_a")
        # "state_a" matches obs, should have higher posterior weight
        assert posterior["state_a"] > posterior["state_b"]

    def test_compute_vfe_empty_beliefs(self):
        runner = _make_runner_with_state()
        vfe = runner._compute_vfe({}, "obs")
        assert vfe == 0.0

    def test_compute_vfe_returns_float(self):
        runner = _make_runner_with_state()
        beliefs = {"state_a": 0.6, "state_b": 0.4}
        vfe = runner._compute_vfe(beliefs, "state_a")
        assert isinstance(vfe, float)

    def test_evaluate_policies_no_state_space(self):
        from cogant.gnn.runner import GNNModelRunner
        runner = GNNModelRunner()
        runner.state_space = {}
        runner.actions = []
        result = runner._evaluate_policies({"s0": 1.0})
        assert result == []

    def test_evaluate_policies_returns_list(self):
        runner = _make_runner_with_state()
        beliefs = {"state_a": 0.5, "state_b": 0.5}
        result = runner._evaluate_policies(beliefs)
        assert isinstance(result, list)

    def test_compute_transition_adds_key(self):
        runner = _make_runner_with_state()
        state = {"x": 1.0, "y": 2.0}
        new_state = runner._compute_transition(state, "action_a")
        assert "step_result_action_a" in new_state

    def test_compute_transition_increments_numeric(self):
        runner = _make_runner_with_state()
        state = {"x": 1.0}
        new_state = runner._compute_transition(state, "move")
        assert new_state["x"] > 1.0

    def test_compute_reward_changed_state(self):
        runner = _make_runner_with_state()
        state = {"x": 1}
        new_state = {"x": 2}
        reward = runner._compute_reward(state, "act", new_state)
        assert reward == 0.1

    def test_compute_reward_unchanged_state(self):
        runner = _make_runner_with_state()
        state = {"x": 1}
        reward = runner._compute_reward(state, "act", state)
        assert reward == 0.0

    def test_count_unique_states_empty(self):
        runner = _make_runner_with_state()
        result = runner._count_unique_states([])
        assert result == 0

    def test_count_unique_states(self):
        runner = _make_runner_with_state()
        traces = [
            {"state": {"x": 1}},
            {"state": {"x": 2}},
            {"state": {"x": 1}},  # duplicate
        ]
        result = runner._count_unique_states(traces)
        assert result == 2

    def test_count_unique_actions_empty(self):
        runner = _make_runner_with_state()
        result = runner._count_unique_actions([])
        assert result == 0

    def test_count_unique_actions(self):
        runner = _make_runner_with_state()
        traces = [
            {"action": "act_a"},
            {"action": "act_b"},
            {"action": "act_a"},  # duplicate
        ]
        result = runner._count_unique_actions(traces)
        assert result == 2

    def test_entropy_uniform(self):
        runner = _make_runner_with_state()
        dist = {"a": 0.5, "b": 0.5}
        entropy = runner._entropy(dist)
        import math
        assert abs(entropy - math.log(2)) < 1e-9

    def test_entropy_deterministic(self):
        runner = _make_runner_with_state()
        dist = {"a": 1.0, "b": 0.0}
        entropy = runner._entropy(dist)
        assert entropy == 0.0

    def test_generate_execution_report_no_traces(self):
        runner = _make_runner_with_state()
        report = runner.generate_execution_report()
        assert isinstance(report, str)
        assert "No traces" in report or "GNN" in report

    def test_generate_execution_report_with_trace_dict(self):
        runner = _make_runner_with_state()
        trace = {
            "traces": [{"step": 0, "action": "act", "observation": "obs", "free_energy_after": 0.5, "reward": 0.1, "beliefs": {}}],
            "statistics": {"mean_reward": 0.1},
            "free_energy_trajectory": [1.0, 0.5],
            "action_distribution": {"act": 1},
            "total_reward": 0.1,
            "avg_reward": 0.1,
        }
        runner.beliefs_history = [{"state_a": 0.5, "state_b": 0.5}]
        report = runner.generate_execution_report(trace=trace)
        assert isinstance(report, str)
        assert "GNN" in report
