"""Wave-20 coverage tests for cogant.reverse.planner.

Targets the PackagePlan helper methods and edge branches that the
existing tests don't reach:

* ``PackagePlan.validate`` — all five validation branches (lines 155-219)
* ``PackagePlan.diff`` — every diff branch including matrix-flag and
  scaffold differences (lines 233-286)
* ``PackagePlan.to_json`` / ``from_json`` round-trip (lines 295-360)
* ``_node_to_dict`` / ``_dict_to_node`` direct calls (lines 365, 378)
* ``_to_identifier`` digit-prefix branch (line 427)
* ``plan_package`` context-annotation branch (lines 636-648)

All tests use real ReverseGNNModel and PackagePlan instances.
"""

from __future__ import annotations

import json

from cogant.reverse.parser import ReverseGNNModel
from cogant.reverse.planner import (
    NodePlan,
    PackagePlan,
    _to_identifier,
    plan_package,
)

# --------------------------------------------------------------------------- #
# _to_identifier — digit prefix branch (line 427)
# --------------------------------------------------------------------------- #


def test_to_identifier_prefixes_digit_start_with_var():
    """Identifiers starting with a digit get a ``var_`` prefix."""
    assert _to_identifier("123abc", "fallback") == "var_123abc"


def test_to_identifier_returns_fallback_for_empty_input():
    assert _to_identifier("", "slot_x") == "slot_x"


def test_to_identifier_returns_fallback_when_sanitization_empties():
    """A name made of only forbidden chars sanitizes to empty → fallback."""
    assert _to_identifier("!!!---", "s_f0") == "s_f0"


def test_to_identifier_strips_role_suffix():
    """The ``- Hidden State`` suffix pattern is stripped before sanitization."""
    assert _to_identifier("Calculator - Hidden State", "fb") == "calculator"


def test_to_identifier_lowercases_result():
    assert _to_identifier("MixedCASE", "fb") == "mixedcase"


# --------------------------------------------------------------------------- #
# PackagePlan.validate — every issue branch (lines 155-219)
# --------------------------------------------------------------------------- #


def test_validate_minimal_handcrafted_clean_plan_returns_no_issues():
    """A minimal hand-built plan with no scaffolds passes validation."""
    plan = PackagePlan(package_name="clean")
    n_state = NodePlan(slot="s_f0", name="x", role="HIDDEN_STATE")
    n_obs = NodePlan(slot="o_m0", name="get_y", role="OBSERVATION")
    n_act = NodePlan(slot="u_c0", name="update_z", role="ACTION")
    plan.nodes = [n_state, n_obs, n_act]
    plan.state_vars = [n_state]
    plan.obs_functions = [n_obs]
    plan.action_methods = [n_act]
    assert plan.validate() == []


def test_validate_detects_duplicate_names():
    plan = PackagePlan(package_name="dup_test")
    n1 = NodePlan(slot="s1", name="same", role="HIDDEN_STATE")
    n2 = NodePlan(slot="s2", name="same", role="HIDDEN_STATE")
    plan.nodes = [n1, n2]
    plan.state_vars = [n1, n2]
    issues = plan.validate()
    assert any("Duplicate node names" in issue for issue in issues)


def test_validate_detects_unrecognized_role():
    plan = PackagePlan(package_name="bad_role")
    bad_node = NodePlan(slot="x", name="x_func", role="UNKNOWN_ROLE")
    plan.nodes = [bad_node]
    issues = plan.validate()
    assert any("unrecognized role" in issue for issue in issues)


def test_validate_detects_subset_node_not_in_main_list():
    plan = PackagePlan(package_name="orphan")
    main_node = NodePlan(slot="m", name="main", role="HIDDEN_STATE")
    orphan_node = NodePlan(slot="o", name="orphan", role="HIDDEN_STATE")
    plan.nodes = [main_node]
    plan.state_vars = [main_node, orphan_node]  # orphan not in nodes
    issues = plan.validate()
    assert any("not in main nodes list" in issue for issue in issues)


def test_validate_detects_state_var_with_wrong_role():
    plan = PackagePlan(package_name="wrong_role")
    bad = NodePlan(slot="s", name="s_func", role="OBSERVATION")  # wrong role
    plan.nodes = [bad]
    plan.state_vars = [bad]
    issues = plan.validate()
    assert any("expected HIDDEN_STATE" in issue for issue in issues)


def test_validate_detects_obs_var_with_wrong_role():
    plan = PackagePlan(package_name="wrong_obs")
    bad = NodePlan(slot="o", name="o_func", role="ACTION")
    plan.nodes = [bad]
    plan.obs_functions = [bad]
    issues = plan.validate()
    assert any("expected OBSERVATION" in issue for issue in issues)


def test_validate_detects_action_var_with_wrong_role():
    plan = PackagePlan(package_name="wrong_action")
    bad = NodePlan(slot="a", name="a_func", role="POLICY")
    plan.nodes = [bad]
    plan.action_methods = [bad]
    issues = plan.validate()
    assert any("expected ACTION" in issue for issue in issues)


def test_validate_detects_invalid_package_name_keyword():
    plan = PackagePlan(package_name="class")  # 'class' is a Python keyword
    issues = plan.validate()
    assert any("not a valid Python identifier" in issue for issue in issues)


def test_validate_detects_invalid_package_name_non_identifier():
    plan = PackagePlan(package_name="123-bad")
    issues = plan.validate()
    assert any("not a valid Python identifier" in issue for issue in issues)


# --------------------------------------------------------------------------- #
# PackagePlan.diff — each diff branch (lines 233-286)
# --------------------------------------------------------------------------- #


def test_diff_identical_plans_returns_empty_string():
    p1 = PackagePlan(package_name="same")
    p2 = PackagePlan(package_name="same")
    assert p1.diff(p2) == ""


def test_diff_detects_package_name_difference():
    p1 = PackagePlan(package_name="alpha")
    p2 = PackagePlan(package_name="beta")
    diff = p1.diff(p2)
    assert "package_name" in diff
    assert "'alpha'" in diff and "'beta'" in diff


def test_diff_detects_role_count_differences():
    p1 = PackagePlan(package_name="m1")
    p2 = PackagePlan(package_name="m1")
    n = NodePlan(slot="x", name="x_state", role="HIDDEN_STATE")
    p1.state_vars = [n]
    p1.nodes = [n]
    diff = p1.diff(p2)
    assert "HIDDEN_STATE" in diff
    assert "1 vs 0" in diff


def test_diff_detects_scaffold_constraint_differences():
    p1 = PackagePlan(package_name="m")
    p2 = PackagePlan(package_name="m")
    n = NodePlan(slot="s", name="check_s", role="CONSTRAINT")
    p1.scaffold_constraint_checks = [n]
    diff = p1.diff(p2)
    assert "scaffold_constraint_checks" in diff


def test_diff_detects_scaffold_policy_differences():
    p1 = PackagePlan(package_name="m")
    p2 = PackagePlan(package_name="m")
    n = NodePlan(slot="p", name="route_p", role="POLICY")
    p1.scaffold_policy_functions = [n]
    diff = p1.diff(p2)
    assert "scaffold_policy_functions" in diff


def test_diff_detects_matrix_flag_differences():
    p1 = PackagePlan(package_name="m", has_A_matrix=True, has_B_tensor=False)
    p2 = PackagePlan(package_name="m", has_A_matrix=False, has_B_tensor=True)
    diff = p1.diff(p2)
    assert "has_A_matrix" in diff
    assert "has_B_tensor" in diff


def test_diff_detects_all_four_matrix_flags():
    p1 = PackagePlan(
        package_name="m",
        has_A_matrix=True,
        has_B_tensor=True,
        has_C_vector=True,
        has_D_vector=True,
    )
    p2 = PackagePlan(package_name="m")
    diff = p1.diff(p2)
    for flag in ["has_A_matrix", "has_B_tensor", "has_C_vector", "has_D_vector"]:
        assert flag in diff


# --------------------------------------------------------------------------- #
# PackagePlan.to_json / from_json round-trip (lines 295-360)
# --------------------------------------------------------------------------- #


def test_to_json_returns_valid_json_string():
    model = ReverseGNNModel(
        model_name="json_model",
        hidden_states=["s_f0"],
        observations=["o_m0"],
        actions=["u_c0"],
        cardinalities={"s_f0": 2, "o_m0": 2, "u_c0": 2},
    )
    plan = plan_package(model)
    out = plan.to_json()
    parsed = json.loads(out)
    assert parsed["package_name"] == "json_model"
    assert "nodes" in parsed
    assert "state_vars" in parsed
    assert "has_A_matrix" in parsed


def test_from_json_round_trip_preserves_structure():
    model = ReverseGNNModel(
        model_name="rt_model",
        raw_model_name="rt_model",
        hidden_states=["s_f0", "s_f1"],
        observations=["o_m0"],
        actions=["u_c0"],
        cardinalities={"s_f0": 2, "s_f1": 3, "o_m0": 2, "u_c0": 2},
        types={"s_f0": "int", "o_m0": "int", "u_c0": "int"},
    )
    original = plan_package(model)
    serialized = original.to_json()
    restored = PackagePlan.from_json(serialized)

    assert restored.package_name == original.package_name
    assert restored.raw_model_name == original.raw_model_name
    assert len(restored.state_vars) == len(original.state_vars)
    assert len(restored.obs_functions) == len(original.obs_functions)
    assert len(restored.action_methods) == len(original.action_methods)
    assert restored.has_A_matrix == original.has_A_matrix
    assert restored.has_B_tensor == original.has_B_tensor
    assert restored.has_C_vector == original.has_C_vector
    assert restored.has_D_vector == original.has_D_vector


def test_from_json_handles_minimal_payload():
    """from_json supplies defaults for missing fields."""
    minimal = json.dumps({})
    plan = PackagePlan.from_json(minimal)
    assert plan.package_name == "cogant_model"
    assert plan.raw_model_name == "cogant_model"
    assert plan.has_A_matrix is False
    assert plan.has_B_tensor is False
    assert plan.has_C_vector is False
    assert plan.has_D_vector is False
    assert plan.nodes == []


def test_from_json_skips_unknown_state_var_names():
    """get_nodes filters out names not present in the nodes dict."""
    payload = {
        "package_name": "skip_test",
        "nodes": [
            {
                "slot": "s_f0",
                "name": "real",
                "role": "HIDDEN_STATE",
                "python_type": "int",
                "module": "state.py",
                "cardinality": 2,
                "initial_value": "0",
            }
        ],
        "state_vars": ["real", "ghost"],  # 'ghost' is not in nodes
    }
    plan = PackagePlan.from_json(json.dumps(payload))
    assert len(plan.state_vars) == 1
    assert plan.state_vars[0].name == "real"


# --------------------------------------------------------------------------- #
# _node_to_dict / _dict_to_node direct calls
# --------------------------------------------------------------------------- #


def test_node_to_dict_serializes_all_fields():
    n = NodePlan(
        slot="s_f0",
        name="ident",
        role="HIDDEN_STATE",
        python_type="int",
        module="state.py",
        cardinality=4,
        initial_value="0",
    )
    d = PackagePlan._node_to_dict(n)
    assert d == {
        "slot": "s_f0",
        "name": "ident",
        "role": "HIDDEN_STATE",
        "python_type": "int",
        "module": "state.py",
        "cardinality": 4,
        "initial_value": "0",
    }


def test_dict_to_node_round_trip():
    d = {
        "slot": "u_c0",
        "name": "act_x",
        "role": "ACTION",
        "python_type": "bool",
        "module": "act.py",
        "cardinality": 2,
        "initial_value": "False",
    }
    n = PackagePlan._dict_to_node(d)
    assert n.slot == "u_c0"
    assert n.name == "act_x"
    assert n.role == "ACTION"
    assert n.python_type == "bool"
    assert n.module == "act.py"
    assert n.cardinality == 2
    assert n.initial_value == "False"


def test_dict_to_node_uses_defaults_for_missing_keys():
    n = PackagePlan._dict_to_node({})
    assert n.slot == ""
    assert n.name == ""
    assert n.role == ""
    assert n.python_type == "float"
    assert n.module == ""
    assert n.cardinality == 0
    assert n.initial_value == "0.0"


# --------------------------------------------------------------------------- #
# plan_package context-annotation branch (lines 636-648)
# --------------------------------------------------------------------------- #


def test_plan_package_emits_context_node_for_context_annotation():
    """A non-hidden/obs/action variable annotated as Context produces a CONTEXT node."""
    model = ReverseGNNModel(
        model_name="ctx_model",
        hidden_states=["s_f0"],
        observations=["o_m0"],
        actions=["u_c0"],
        cardinalities={"s_f0": 2, "o_m0": 2, "u_c0": 2},
        annotations={"env_var": "Context"},  # not in any role list
    )
    plan = plan_package(model)
    assert len(plan.context_functions) >= 1
    ctx_names = [n.name for n in plan.context_functions]
    assert any(name.startswith("context_") for name in ctx_names)


def test_plan_package_emits_context_node_for_time_annotation():
    """``Time`` lowercased equals 'time' → also produces a CONTEXT node."""
    model = ReverseGNNModel(
        model_name="time_model",
        hidden_states=["s_f0"],
        observations=["o_m0"],
        actions=["u_c0"],
        annotations={"clock": "Time"},
    )
    plan = plan_package(model)
    assert len(plan.context_functions) >= 1
    assert any(n.role == "CONTEXT" for n in plan.context_functions)


def test_plan_package_skips_annotation_when_var_already_in_role_list():
    """A variable that's also a hidden state is not duplicated as CONTEXT."""
    model = ReverseGNNModel(
        model_name="skip_model",
        hidden_states=["s_f0"],
        observations=["o_m0"],
        actions=["u_c0"],
        annotations={"s_f0": "Context"},  # collides with hidden state
    )
    plan = plan_package(model)
    # No context_function emitted for s_f0 since it's already a state var
    ctx_slots = {n.slot for n in plan.context_functions}
    assert "s_f0" not in ctx_slots


def test_plan_package_ignores_unrelated_annotations():
    """Annotations that aren't context-like are ignored entirely."""
    model = ReverseGNNModel(
        model_name="m",
        hidden_states=["s_f0"],
        observations=["o_m0"],
        actions=["u_c0"],
        annotations={"some_var": "RandomConcept"},
    )
    plan = plan_package(model)
    ctx_slots = {n.slot for n in plan.context_functions}
    assert "some_var" not in ctx_slots


def test_plan_package_without_observations_still_produces_scaffolds():
    """plan_package with empty obs/action lists still produces minimum scaffolds."""
    model = ReverseGNNModel(
        model_name="bare",
        hidden_states=["s_f0"],
    )
    plan = plan_package(model)
    # Minimum 2 policies, 2 contexts even on a degenerate model
    assert len(plan.scaffold_policy_functions) >= 2
    assert len(plan.scaffold_context_classes) >= 2
