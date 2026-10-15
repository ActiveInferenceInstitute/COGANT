import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from cogant.statespace import FiniteModel, FiniteModelSpec, compile_finite_model
from cogant.statespace.finite_spec import FiniteModelError

pytestmark = pytest.mark.unit
SPEC = Path(__file__).parents[2] / "examples" / "finite_models" / "toggle.json"


@pytest.mark.parametrize("field", ["states", "actions", "observations"])
@pytest.mark.parametrize("labels", [[], ["off", "off"], [""]])
def test_invalid_domains_are_rejected(field: str, labels: list[str]) -> None:
    data = json.loads(SPEC.read_text())
    data[field] = labels

    with pytest.raises(ValidationError):
        FiniteModelSpec.model_validate(data)


@pytest.mark.parametrize("field", ["transitions", "likelihoods", "prior"])
def test_missing_probability_mass_is_rejected(field: str) -> None:
    data = json.loads(SPEC.read_text())
    data[field] = data[field][1:]

    with pytest.raises(ValidationError):
        FiniteModelSpec.model_validate(data)


@pytest.mark.parametrize("field", ["transitions", "likelihoods", "prior", "preferences"])
def test_duplicate_rows_are_rejected(field: str) -> None:
    data = json.loads(SPEC.read_text())
    data[field].append(data[field][0])

    with pytest.raises(ValidationError):
        FiniteModelSpec.model_validate(data)


@pytest.mark.parametrize("probability", [-0.1, 1.1, float("nan"), float("inf"), True, "1"])
def test_invalid_probability_values_are_rejected(probability: float | bool | str) -> None:
    data = json.loads(SPEC.read_text())
    data["transitions"][0]["probability"] = probability

    with pytest.raises(ValidationError):
        FiniteModelSpec.model_validate(data)


@pytest.mark.parametrize(
    "field,key",
    [
        ("transitions", "state"),
        ("transitions", "action"),
        ("transitions", "next_state"),
        ("likelihoods", "state"),
        ("likelihoods", "observation"),
        ("prior", "state"),
        ("preferences", "observation"),
    ],
)
def test_unknown_references_are_rejected(field: str, key: str) -> None:
    data = json.loads(SPEC.read_text())
    data[field][0][key] = "undeclared"

    with pytest.raises(ValidationError):
        FiniteModelSpec.model_validate(data)


@pytest.mark.parametrize("budget", [15])
def test_allocation_limit_rejects_before_materializing_matrices(budget: int) -> None:
    spec = FiniteModelSpec.model_validate_json(SPEC.read_text())

    with pytest.raises(FiniteModelError):
        compile_finite_model(spec, max_entries=budget)


@pytest.mark.parametrize("field", ["A", "B", "C", "D"])
def test_matrix_axis_mismatches_are_rejected(field: str) -> None:
    spec = FiniteModelSpec.model_validate_json(SPEC.read_text())
    data = compile_finite_model(spec).model_dump(mode="json")
    data[field] = data[field][1:]

    with pytest.raises(ValidationError):
        FiniteModel.model_validate(data)


def test_probability_normalization_is_checked_on_artifact_import() -> None:
    spec = FiniteModelSpec.model_validate_json(SPEC.read_text())
    data = compile_finite_model(spec).model_dump(mode="json")
    data["B"][0][0][0] = 0.5

    with pytest.raises(ValidationError):
        FiniteModel.model_validate(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "2.0"),
        ("name", ""),
        ("undeclared_option", True),
    ],
)
def test_specification_version_and_unknown_fields_are_checked(
    field: str, value: str | bool
) -> None:
    data = json.loads(SPEC.read_text())
    data[field] = value

    with pytest.raises(ValidationError):
        FiniteModelSpec.model_validate(data)


@pytest.mark.parametrize("field", ["A", "B"])
def test_inner_matrix_shape_is_checked(field: str) -> None:
    spec = FiniteModelSpec.model_validate_json(SPEC.read_text())
    data = compile_finite_model(spec).model_dump(mode="json")
    data[field][0] = []

    with pytest.raises(ValidationError):
        FiniteModel.model_validate(data)


def test_action_axis_shape_is_checked() -> None:
    spec = FiniteModelSpec.model_validate_json(SPEC.read_text())
    data = compile_finite_model(spec).model_dump(mode="json")
    data["B"][0][0] = []

    with pytest.raises(ValidationError):
        FiniteModel.model_validate(data)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_log_preferences_require_finite_numeric_values(value: float | bool) -> None:
    data = json.loads(SPEC.read_text())
    data["preferences"][0]["log_preference"] = value

    with pytest.raises(ValidationError):
        FiniteModelSpec.model_validate(data)


def test_exact_allocation_budget_is_admitted() -> None:
    spec = FiniteModelSpec.model_validate_json(SPEC.read_text())

    model = compile_finite_model(spec, max_entries=16)

    assert model.states == ("off", "on")


@pytest.mark.parametrize("budget", [0, -1, float("nan"), float("inf"), 0.5, True, "100"])
def test_non_integer_allocation_limits_are_rejected(budget: float | bool | str) -> None:
    spec = FiniteModelSpec.model_validate_json(SPEC.read_text())

    with pytest.raises(ValidationError):
        compile_finite_model(spec, max_entries=budget)
