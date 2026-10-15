#!/usr/bin/env python3
"""Targeted branch tests — reverse/parser.py helper functions and gnn/runner.py
deeper Active Inference methods.

Covers:
- reverse/parser.py: _split_sections, _parse_cardinality_and_type, _parse_tuple_vector,
  _parse_state_space_block, parse_gnn (str input, Path input, full GNN block),
  ReverseGNNModel properties (n_states, n_obs, n_actions), _sanitize_identifier
- gnn/runner.py: matrix likelihood and prior sensitivity of posterior beliefs
"""

import pytest

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
        from cogant.reverse.parser import ReverseGNNModel, _parse_state_space_block

        model = ReverseGNNModel()
        body = "s_f0[2,1,type=int]\ns_f1[3,1,type=int]\n"
        _parse_state_space_block(body, model)
        assert len(model.hidden_states) == 2
        assert "s_f0" in model.hidden_states
        assert "s_f1" in model.hidden_states

    def test_parse_state_space_block_observations(self):
        from cogant.reverse.parser import ReverseGNNModel, _parse_state_space_block

        model = ReverseGNNModel()
        body = "o_m0[4,1]\no_m1[2,1]\n"
        _parse_state_space_block(body, model)
        assert len(model.observations) == 2

    def test_parse_state_space_block_actions(self):
        from cogant.reverse.parser import ReverseGNNModel, _parse_state_space_block

        model = ReverseGNNModel()
        body = "u_c0[3,1]\n"
        _parse_state_space_block(body, model)
        assert len(model.actions) == 1

    def test_parse_state_space_block_cardinalities(self):
        from cogant.reverse.parser import ReverseGNNModel, _parse_state_space_block

        model = ReverseGNNModel()
        body = "s_f0[5,1,type=str]\n"
        _parse_state_space_block(body, model)
        assert model.cardinalities.get("s_f0") == 5

    def test_parse_state_space_block_comment_lines_skipped(self):
        from cogant.reverse.parser import ReverseGNNModel, _parse_state_space_block

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
        from cogant.reverse.parser import ReverseGNNModel, _parse_state_space_block

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
        gnn_file.write_text("## ModelName\nPathModel\n\n## StateSpaceBlock\ns_f0[2,1]\n")
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


class TestGNNModelRunnerActiveInference:
    @pytest.mark.parametrize(
        "prior,expected",
        [
            ("0.75\n0.25", [27 / 29, 2 / 29]),
            ("0.5\n0.5", [9 / 11, 2 / 11]),
            ("0.0\n1.0", [0.0, 1.0]),
        ],
    )
    def test_posterior_changes_with_exported_prior(self, tmp_path, prior, expected):
        from tests.gnn_execution_fixture import MODEL, runner

        model = runner(tmp_path, MODEL.replace("0.75\n0.25", prior))
        model.run(1)
        assert list(model.traces[0].beliefs.values()) == pytest.approx(expected)
        assert sum(model.traces[0].predicted_state.values()) == pytest.approx(1.0)
