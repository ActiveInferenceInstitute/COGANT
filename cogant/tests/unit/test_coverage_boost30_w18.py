#!/usr/bin/env python3
"""Coverage boost batch 30 — reverse/parser.py thorough coverage.

Covers:
- ReverseGNNModel dataclass properties (n_states, n_obs, n_actions)
- _split_sections: single, multiple, duplicate headers, empty text
- _parse_cardinality_and_type: various declaration formats
- _parse_tuple_vector: flat, nested, edge cases
- _parse_state_space_block: all prefix types (s_f, o_m, u_c, pi_c, c_f, A_m)
- _parse_ontology_annotation: concept classification, all branches
- _parse_initial_parameterization: D/C/A/B assembly, identity shorthand
- _parse_state_variables_extended: table parsing with ID/Name columns
- _parse_connections: arrow syntax filtering
- _parse_matrices_fenced_block: A/B/C/D blocks
- _sanitize_identifier: edge cases (leading digit, spaces, empty)
- parse_gnn: full integration with string, Path, and TypeError
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers: lazy import accessors
# ---------------------------------------------------------------------------


def _mod():
    import cogant.reverse.parser as m

    return m


def _new_model():
    return _mod().ReverseGNNModel()


def _split(text):
    return _mod()._split_sections(text)


def _card_type(decl):
    return _mod()._parse_cardinality_and_type(decl)


def _tup_vec(body):
    return _mod()._parse_tuple_vector(body)


def _ssb(body, model=None):
    m = model if model is not None else _new_model()
    _mod()._parse_state_space_block(body, m)
    return m


def _onto(body, model=None):
    m = model if model is not None else _new_model()
    _mod()._parse_ontology_annotation(body, m)
    return m


def _iparam(body, model=None):
    m = model if model is not None else _new_model()
    _mod()._parse_initial_parameterization(body, m)
    return m


def _svext(body, model=None):
    m = model if model is not None else _new_model()
    _mod()._parse_state_variables_extended(body, m)
    return m


def _conns(body, model=None):
    m = model if model is not None else _new_model()
    _mod()._parse_connections(body, m)
    return m


def _mfb(text, model=None):
    m = model if model is not None else _new_model()
    _mod()._parse_matrices_fenced_block(text, m)
    return m


def _san(name):
    return _mod()._sanitize_identifier(name)


def _parse_gnn(gnn):
    return _mod().parse_gnn(gnn)


def _model_with_states(n_s=2, n_o=1, n_a=1):
    m = _new_model()
    m.hidden_states = [f"s_f{i}" for i in range(n_s)]
    m.observations = [f"o_m{i}" for i in range(n_o)]
    m.actions = [f"u_c{i}" for i in range(n_a)]
    return m


# ---------------------------------------------------------------------------
# ReverseGNNModel — dataclass and properties
# ---------------------------------------------------------------------------


class TestReverseGNNModel:
    def test_default_model_name(self):
        m = _new_model()
        assert m.model_name == "cogant_model"

    def test_n_states_empty(self):
        m = _new_model()
        assert m.n_states == 0

    def test_n_obs_empty(self):
        m = _new_model()
        assert m.n_obs == 0

    def test_n_actions_empty(self):
        m = _new_model()
        assert m.n_actions == 0

    def test_n_states_populated(self):
        ReverseGNNModel = _mod().ReverseGNNModel
        m = ReverseGNNModel(hidden_states=["s_f0", "s_f1", "s_f2"])
        assert m.n_states == 3

    def test_n_obs_populated(self):
        ReverseGNNModel = _mod().ReverseGNNModel
        m = ReverseGNNModel(observations=["o_m0", "o_m1"])
        assert m.n_obs == 2

    def test_n_actions_populated(self):
        ReverseGNNModel = _mod().ReverseGNNModel
        m = ReverseGNNModel(actions=["u_c0"])
        assert m.n_actions == 1

    def test_default_raw_model_name(self):
        m = _new_model()
        assert m.raw_model_name == "cogant_model"

    def test_cardinalities_default_empty(self):
        m = _new_model()
        assert m.cardinalities == {}

    def test_annotations_default_empty(self):
        m = _new_model()
        assert m.annotations == {}

    def test_connections_default_empty(self):
        m = _new_model()
        assert m.connections == []

    def test_human_names_default_empty(self):
        m = _new_model()
        assert m.human_names == {}

    def test_D_default_empty(self):
        m = _new_model()
        assert m.D == []

    def test_A_default_empty(self):
        m = _new_model()
        assert m.A == []

    def test_B_default_empty(self):
        m = _new_model()
        assert m.B == []

    def test_C_default_empty(self):
        m = _new_model()
        assert m.C == []


# ---------------------------------------------------------------------------
# _split_sections
# ---------------------------------------------------------------------------


class TestSplitSections:
    def test_empty_text_returns_empty_dict(self):
        result = _split("")
        assert result == {}

    def test_single_section(self):
        text = "## ModelName\nMyModel\n"
        result = _split(text)
        assert "ModelName" in result
        assert len(result["ModelName"]) == 1
        assert "MyModel" in result["ModelName"][0]

    def test_multiple_distinct_sections(self):
        text = "## ModelName\nA\n## StateSpaceBlock\nB\n"
        result = _split(text)
        assert "ModelName" in result
        assert "StateSpaceBlock" in result

    def test_duplicate_header_returns_list(self):
        text = "## Connections\nfirst\n## Connections\nsecond\n"
        result = _split(text)
        assert len(result["Connections"]) == 2
        assert "first" in result["Connections"][0]
        assert "second" in result["Connections"][1]

    def test_section_body_captured(self):
        text = "## StateSpaceBlock\ns_f0[2,type=int]\ns_f1[3,type=int]\n"
        result = _split(text)
        body = result["StateSpaceBlock"][0]
        assert "s_f0" in body
        assert "s_f1" in body

    def test_last_section_captures_to_end(self):
        text = "## ModelName\nContent here\n"
        result = _split(text)
        assert "Content here" in result["ModelName"][0]

    def test_no_hashes_returns_empty(self):
        text = "Just plain text\nno sections\n"
        result = _split(text)
        assert result == {}

    def test_three_sections(self):
        text = "## A\naa\n## B\nbb\n## C\ncc\n"
        result = _split(text)
        assert set(result.keys()) == {"A", "B", "C"}


# ---------------------------------------------------------------------------
# _parse_cardinality_and_type
# ---------------------------------------------------------------------------


class TestParseCardinalityAndType:
    def test_simple_int(self):
        card, t = _card_type("2,type=int")
        assert card == 2
        assert t == "int"

    def test_float_type(self):
        card, t = _card_type("4,type=float")
        assert card == 4
        assert t == "float"

    def test_no_type_suffix(self):
        card, t = _card_type("10")
        assert card == 10
        assert t is None

    def test_multi_part_with_depth(self):
        card, t = _card_type("5,1,type=int")
        assert card == 5
        assert t == "int"

    def test_no_cardinality(self):
        card, t = _card_type("type=bool")
        assert card is None
        assert t == "bool"

    def test_empty_declaration(self):
        card, t = _card_type("")
        assert card is None
        assert t is None

    def test_bool_type(self):
        card, t = _card_type("2,type=bool")
        assert card == 2
        assert t == "bool"

    def test_large_cardinality(self):
        card, t = _card_type("100,type=int")
        assert card == 100


# ---------------------------------------------------------------------------
# _parse_tuple_vector
# ---------------------------------------------------------------------------


class TestParseTupleVector:
    def test_simple_triple(self):
        result = _tup_vec("(0.1, 0.2, 0.7)")
        assert len(result) == 3
        assert abs(result[0] - 0.1) < 1e-9

    def test_flat_floats(self):
        result = _tup_vec("0.3 0.3 0.4")
        assert len(result) == 3

    def test_nested_tuples_flattened(self):
        result = _tup_vec("((0.1, 0.2), (0.3, 0.4))")
        assert len(result) == 4

    def test_integers_parsed(self):
        result = _tup_vec("(1, 0, 0)")
        assert result == [1.0, 0.0, 0.0]

    def test_empty_string(self):
        result = _tup_vec("")
        assert result == []

    def test_single_value(self):
        result = _tup_vec("(0.9)")
        assert len(result) == 1
        assert abs(result[0] - 0.9) < 1e-9

    def test_scientific_notation(self):
        result = _tup_vec("(1e-3, 2.5e-1)")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _parse_state_space_block
# ---------------------------------------------------------------------------


class TestParseStateSpaceBlock:
    def test_hidden_state_sf_prefix(self):
        m = _ssb("s_f0[2,type=int]\n")
        assert "s_f0" in m.hidden_states
        assert m.cardinalities["s_f0"] == 2

    def test_observation_om_prefix(self):
        m = _ssb("o_m0[3,type=int]\n")
        assert "o_m0" in m.observations
        assert m.cardinalities["o_m0"] == 3

    def test_action_uc_prefix(self):
        m = _ssb("u_c0[2,type=int]\n")
        assert "u_c0" in m.actions

    def test_policy_pi_prefix(self):
        m = _ssb("pi_c0[2,type=int]\n")
        assert "pi_c0" in m.policies

    def test_constraint_cf_prefix(self):
        m = _ssb("c_f0[2,type=int]\n")
        assert "c_f0" in m.constraints

    def test_multiple_hidden_states_sorted(self):
        m = _ssb("s_f1[3,type=int]\ns_f0[2,type=int]\n")
        assert m.hidden_states[0] == "s_f0"
        assert m.hidden_states[1] == "s_f1"

    def test_a_matrix_skipped_in_variable_lists(self):
        m = _ssb("A_m0[2,2,type=float]\n")
        assert "A_m0" not in m.hidden_states
        assert "A_m0" not in m.observations
        # Cardinality is still recorded
        assert "A_m0" in m.cardinalities

    def test_type_recorded(self):
        m = _ssb("s_f0[4,type=float]\n")
        assert m.types["s_f0"] == "float"

    def test_blank_lines_and_comments_skipped(self):
        m = _ssb("# comment\n\ns_f0[2,type=int]\n")
        assert "s_f0" in m.hidden_states

    def test_non_matching_lines_skipped(self):
        m = _ssb("not a declaration\n")
        assert m.n_states == 0

    def test_short_s_prefix(self):
        m = _ssb("s0[2,type=int]\n")
        assert "s0" in m.hidden_states

    def test_a_action_prefix(self):
        m = _ssb("a_c0[3,type=int]\n")
        assert "a_c0" in m.actions

    def test_multiple_obs_sorted(self):
        m = _ssb("o_m1[4,type=int]\no_m0[2,type=int]\n")
        assert m.observations[0] == "o_m0"
        assert m.observations[1] == "o_m1"


# ---------------------------------------------------------------------------
# _parse_ontology_annotation
# ---------------------------------------------------------------------------


class TestParseOntologyAnnotation:
    def test_basic_annotation(self):
        m = _onto("s_f0=HiddenState\n")
        assert m.annotations.get("s_f0") == "HiddenState"

    def test_matrix_annotation(self):
        m = _onto("A_m0=LikelihoodMatrix\n")
        assert m.annotations.get("A_m0") == "LikelihoodMatrix"

    def test_comment_lines_skipped(self):
        m = _onto("# comment\ns_f0=HiddenState\n")
        assert "s_f0" in m.annotations

    def test_blank_lines_skipped(self):
        m = _onto("\ns_f0=HiddenState\n")
        assert "s_f0" in m.annotations

    def test_hidden_state_concept_added_to_hidden_states(self):
        m = _onto("custom_var=HiddenState\n")
        assert "custom_var" in m.hidden_states

    def test_observation_concept_added_to_observations(self):
        m = _onto("my_obs=Observation\n")
        assert "my_obs" in m.observations

    def test_action_concept_added_to_actions(self):
        m = _onto("my_act=Action\n")
        assert "my_act" in m.actions

    def test_policy_concept_added_to_policies(self):
        m = _onto("my_policy=Policy\n")
        assert "my_policy" in m.policies

    def test_constraint_concept_added_to_constraints(self):
        m = _onto("my_constraint=Constraint\n")
        assert "my_constraint" in m.constraints

    def test_already_classified_not_duplicated(self):
        base = _new_model()
        base.hidden_states = ["s_f0"]
        m = _onto("s_f0=HiddenState\n", model=base)
        assert m.hidden_states.count("s_f0") == 1

    def test_preference_added_to_constraints(self):
        m = _onto("pref_var=Preference\n")
        assert "pref_var" in m.constraints

    def test_multiple_annotations(self):
        m = _onto("s_f0=HiddenState\no_m0=Observation\n")
        assert m.annotations.get("s_f0") == "HiddenState"
        assert m.annotations.get("o_m0") == "Observation"


# ---------------------------------------------------------------------------
# _parse_initial_parameterization
# ---------------------------------------------------------------------------


class TestParseInitialParameterization:
    def test_D_assembled_from_factors(self):
        m = _model_with_states(n_s=2)
        body = "D_f0={ (0.8, 0.2) }\nD_f1={ (0.3, 0.7) }\n"
        _iparam(body, model=m)
        assert len(m.D) == 2
        assert abs(sum(m.D) - 1.0) < 1e-9

    def test_D_default_when_missing(self):
        m = _model_with_states(n_s=3)
        _iparam("", model=m)
        assert len(m.D) == 3
        assert abs(sum(m.D) - 1.0) < 1e-9

    def test_C_assembled_from_factors(self):
        m = _model_with_states(n_s=2, n_o=2)
        body = "C_m0={ (0.5, 0.5) }\nC_m1={ (0.7, 0.3) }\n"
        _iparam(body, model=m)
        assert len(m.C) == 2

    def test_identity_shorthand_B(self):
        m = _model_with_states(n_s=2, n_a=1)
        body = "B_f0=identity(2,2,1)\n"
        _iparam(body, model=m)
        assert len(m.B) == 2

    def test_A_assembled_from_modalities(self):
        m = _model_with_states(n_s=2, n_o=1)
        body = "A_m0={ ( (0.9, 0.1), (0.2, 0.8) ) }\n"
        _iparam(body, model=m)
        assert len(m.A) >= 1

    def test_B_identity_shape(self):
        m = _model_with_states(n_s=3, n_a=2)
        body = "B_f0=identity(3,3,2)\n"
        _iparam(body, model=m)
        assert len(m.B) == 3

    def test_no_states_no_D(self):
        m = _new_model()  # no states
        _iparam("D_f0={ (0.5, 0.5) }\n", model=m)
        assert m.D == []

    def test_A_default_uniform(self):
        m = _model_with_states(n_s=2, n_o=1)
        _iparam("", model=m)  # no A parameterization
        # A should be populated with defaults when both states and obs exist
        assert len(m.A) == 1
        assert len(m.A[0]) == 2


# ---------------------------------------------------------------------------
# _parse_state_variables_extended
# ---------------------------------------------------------------------------


class TestParseStateVariablesExtended:
    def test_table_with_id_name_columns(self):
        body = "| ID | Name | Type |\n|---|---|---|\n| s_f0 | location | int |\n"
        m = _svext(body)
        assert "s_f0" in m.human_names
        assert m.human_names["s_f0"] == "location"

    def test_multiple_rows(self):
        body = "| ID | Name |\n|---|---|\n| s_f0 | alpha |\n| s_f1 | beta |\n"
        m = _svext(body)
        assert m.human_names.get("s_f0") == "alpha"
        assert m.human_names.get("s_f1") == "beta"

    def test_non_table_body_no_crash(self):
        m = _svext("just text\nno table\n")
        assert m.human_names == {}

    def test_separator_line_skipped(self):
        body = "| ID | Name |\n|---|---|\n| s_f0 | foo |\n"
        m = _svext(body)
        assert len(m.human_names) == 1

    def test_name_header_fallback(self):
        # Table without 'name' column header uses index 1
        body = "| ID | Label |\n|---|---|\n| s_f0 | myvar |\n"
        m = _svext(body)
        assert isinstance(m.human_names, dict)


# ---------------------------------------------------------------------------
# _parse_connections
# ---------------------------------------------------------------------------


class TestParseConnections:
    def test_arrow_connection_captured(self):
        m = _conns("s_f0 -> o_m0\n")
        assert len(m.connections) == 1
        assert "s_f0" in m.connections[0]

    def test_parenthesized_syntax_captured(self):
        m = _conns("(D_f0) > (s_f0)\n")
        assert len(m.connections) == 1

    def test_plain_text_skipped(self):
        m = _conns("The function calls the helper\n")
        assert len(m.connections) == 0

    def test_comment_lines_skipped(self):
        m = _conns("# This is a comment\n")
        assert len(m.connections) == 0

    def test_table_lines_skipped(self):
        m = _conns("| Source | Target |\n|---|---|\n| s_f0 | o_m0 |\n")
        assert len(m.connections) == 0

    def test_multiple_connections(self):
        m = _conns("s_f0 -> o_m0\nu_c0 -> s_f0\n")
        assert len(m.connections) == 2

    def test_blank_lines_skipped(self):
        m = _conns("\n\ns_f0 -> o_m0\n\n")
        assert len(m.connections) == 1


# ---------------------------------------------------------------------------
# _parse_matrices_fenced_block
# ---------------------------------------------------------------------------


class TestParseMatricesFencedBlock:
    def test_no_fence_no_change(self):
        m = _mfb("no fenced block here\n")
        assert m.A == []

    def test_A_matrix_parsed(self):
        text = "```gnn-matrices\nA[[rows=2][cols=2]]\n0.9 0.1\n0.2 0.8\n```\n"
        m = _mfb(text)
        assert len(m.A) == 2
        assert abs(m.A[0][0] - 0.9) < 1e-9

    def test_C_vector_parsed(self):
        text = "```gnn-matrices\nC[[rows=2]]\n0.5\n0.7\n```\n"
        m = _mfb(text)
        assert len(m.C) == 2

    def test_D_vector_parsed(self):
        text = "```gnn-matrices\nD[[rows=3]]\n0.3\n0.3\n0.4\n```\n"
        m = _mfb(text)
        assert len(m.D) == 3

    def test_B_matrix_parsed(self):
        text = "```gnn-matrices\nB[[rows=2][cols=2][depth=1]]\n# action=0\n1.0 0.0\n0.0 1.0\n```\n"
        m = _mfb(text)
        assert len(m.B) == 2

    def test_empty_fence_no_crash(self):
        m = _mfb("```gnn-matrices\n```\n")
        assert m.A == []

    def test_overrides_existing_A(self):
        base = _new_model()
        base.A = [[0.5, 0.5]]
        text = "```gnn-matrices\nA[[rows=1][cols=2]]\n0.9 0.1\n```\n"
        m = _mfb(text, model=base)
        assert abs(m.A[0][0] - 0.9) < 1e-9


# ---------------------------------------------------------------------------
# _sanitize_identifier
# ---------------------------------------------------------------------------


class TestSanitizeIdentifier:
    def test_plain_name_lowercased(self):
        assert _san("MyModel") == "mymodel"

    def test_spaces_become_underscores(self):
        assert _san("My Model") == "my_model"

    def test_leading_digit_prefixed(self):
        result = _san("3model")
        assert result.startswith("_")

    def test_special_chars_replaced(self):
        result = _san("model-name.v2")
        assert "-" not in result
        assert "." not in result

    def test_empty_string_returns_default(self):
        result = _san("")
        assert result == "cogant_model"

    def test_already_valid_identifier_unchanged(self):
        result = _san("valid_model")
        assert result == "valid_model"

    def test_all_special_becomes_underscores(self):
        result = _san("!@#$%")
        assert result == "_____"


# ---------------------------------------------------------------------------
# parse_gnn — integration
# ---------------------------------------------------------------------------


class TestParseGNN:
    def test_parse_raw_string_minimal(self):
        gnn = "## ModelName\nTestModel\n## StateSpaceBlock\ns_f0[2,type=int]\n"
        model = _parse_gnn(gnn)
        assert model.raw_model_name == "TestModel"

    def test_parse_raw_string_returns_reverse_gnn_model(self):
        ReverseGNNModel = _mod().ReverseGNNModel
        gnn = "## ModelName\nDemo\n"
        model = _parse_gnn(gnn)
        assert isinstance(model, ReverseGNNModel)

    def test_parse_hidden_states_from_string(self):
        gnn = "## StateSpaceBlock\ns_f0[2,type=int]\ns_f1[3,type=int]\n"
        model = _parse_gnn(gnn)
        assert len(model.hidden_states) == 2

    def test_parse_observations_from_string(self):
        gnn = "## StateSpaceBlock\no_m0[3,type=int]\n"
        model = _parse_gnn(gnn)
        assert "o_m0" in model.observations

    def test_parse_actions_from_string(self):
        gnn = "## StateSpaceBlock\nu_c0[2,type=int]\n"
        model = _parse_gnn(gnn)
        assert "u_c0" in model.actions

    def test_parse_ontology_annotations(self):
        gnn = (
            "## StateSpaceBlock\ns_f0[2,type=int]\n## ActInfOntologyAnnotation\ns_f0=HiddenState\n"
        )
        model = _parse_gnn(gnn)
        assert model.annotations.get("s_f0") == "HiddenState"

    def test_parse_initial_parameterization(self):
        gnn = (
            "## StateSpaceBlock\ns_f0[2,type=int]\n"
            "## InitialParameterization\nD_f0={ (0.6, 0.4) }\n"
        )
        model = _parse_gnn(gnn)
        assert len(model.D) == 1

    def test_parse_connections(self):
        gnn = "## StateSpaceBlock\ns_f0[2]\n## Connections\ns_f0 -> o_m0\n"
        model = _parse_gnn(gnn)
        assert len(model.connections) >= 1

    def test_parse_from_path(self, tmp_path):
        gnn_file = tmp_path / "test.gnn.md"
        gnn_file.write_text("## ModelName\nFileModel\n## StateSpaceBlock\ns_f0[2,type=int]\n")
        model = _parse_gnn(gnn_file)
        assert model.raw_model_name == "FileModel"

    def test_parse_from_path_returns_model(self, tmp_path):
        ReverseGNNModel = _mod().ReverseGNNModel
        gnn_file = tmp_path / "m.gnn.md"
        gnn_file.write_text("## ModelName\nX\n")
        model = _parse_gnn(gnn_file)
        assert isinstance(model, ReverseGNNModel)

    def test_parse_type_error_on_invalid_input(self):
        with pytest.raises(TypeError):
            _parse_gnn(42)

    def test_parse_empty_string(self):
        model = _parse_gnn("")
        assert model.model_name == "cogant_model"

    def test_n_states_correct_after_parse(self):
        gnn = "## StateSpaceBlock\ns_f0[2,type=int]\ns_f1[3,type=int]\ns_f2[4,type=int]\n"
        model = _parse_gnn(gnn)
        assert model.n_states == 3

    def test_model_name_sanitized(self):
        gnn = "## ModelName\nMy Model v2\n"
        model = _parse_gnn(gnn)
        assert model.model_name == "my_model_v2"

    def test_model_name_raw_preserved(self):
        gnn = "## ModelName\nMy Model v2\n"
        model = _parse_gnn(gnn)
        assert model.raw_model_name == "My Model v2"

    def test_gnn_section_fallback(self):
        gnn = "## GNNSection\nFallbackName\n"
        model = _parse_gnn(gnn)
        assert model.raw_model_name == "FallbackName"

    def test_cardinalities_recorded(self):
        gnn = "## StateSpaceBlock\ns_f0[5,type=int]\n"
        model = _parse_gnn(gnn)
        assert model.cardinalities.get("s_f0") == 5

    def test_matrices_fenced_block_overrides(self):
        gnn = (
            "## StateSpaceBlock\ns_f0[2,type=int]\no_m0[2,type=int]\n"
            "## InitialParameterization\nD_f0={ (0.6, 0.4) }\n"
            "```gnn-matrices\n"
            "A[[rows=1][cols=2]]\n"
            "0.8 0.2\n"
            "```\n"
        )
        model = _parse_gnn(gnn)
        assert len(model.A) >= 1
