import itertools
from pathlib import Path

import pytest

from cogant.statespace import (
    FiniteModel,
    FiniteModelSpec,
    compile_finite_model,
    verify_finite_model,
)

pytestmark = pytest.mark.unit
SPEC = Path(__file__).parents[2] / "examples" / "finite_models" / "toggle.json"


@pytest.fixture
def toggle() -> FiniteModelSpec:
    return FiniteModelSpec.model_validate_json(SPEC.read_text())


def test_transition_columns_match_an_independent_toggle_program(toggle: FiniteModelSpec) -> None:
    model = compile_finite_model(toggle)

    for state, action in itertools.product(range(2), range(2)):
        expected = state ^ action
        actual = [model.B[target][state][action] for target in range(2)]
        assert actual == [float(target == expected) for target in range(2)]


def test_compiled_trace_matches_a_plain_python_state_machine(toggle: FiniteModelSpec) -> None:
    model = compile_finite_model(toggle)
    belief = list(model.D)
    reference_state = 0

    for action in (1, 0, 1, 1, 0, 1):
        reference_state ^= action
        belief = [
            sum(model.B[target][state][action] * belief[state] for state in range(2))
            for target in range(2)
        ]
        assert belief == [float(state == reference_state) for state in range(2)]


def test_runtime_uses_declared_preferences_to_select_the_on_action(toggle: FiniteModelSpec) -> None:
    runtime = compile_finite_model(toggle).to_runtime()

    step = runtime.step([1.0, 0.0], obs_idx=0)

    assert step.action == 1
    assert step.state_dist == [0.0, 1.0]


def test_json_roundtrip_preserves_the_full_compiled_model(toggle: FiniteModelSpec) -> None:
    model = compile_finite_model(toggle)

    restored = FiniteModel.model_validate_json(model.model_dump_json())

    assert restored == model
    assert verify_finite_model(toggle, restored).passed


def test_checker_rejects_a_wrong_but_column_stochastic_transition(toggle: FiniteModelSpec) -> None:
    data = compile_finite_model(toggle).model_dump(mode="json")
    data["B"][0][0][1], data["B"][1][0][1] = 1.0, 0.0
    wrong = FiniteModel.model_validate(data)

    report = verify_finite_model(toggle, wrong)

    assert not report.passed
    assert report.mismatch_count == 2
    assert report.checked_entries == 16


@pytest.mark.parametrize("field", ["A", "C", "D", "source_sha256", "states", "name"])
def test_checker_catches_likelihood_preference_prior_and_identity_drift(
    toggle: FiniteModelSpec, field: str
) -> None:
    data = compile_finite_model(toggle).model_dump(mode="json")
    changes = {
        "A": [[0.0, 0.0], [1.0, 1.0]],
        "C": [5.0, 0.0],
        "D": [0.0, 1.0],
        "source_sha256": "0" * 64,
        "states": ["on", "off"],
        "name": "different model",
    }
    data[field] = changes[field]

    report = verify_finite_model(toggle, FiniteModel.model_validate(data))

    assert not report.passed
    assert report.mismatch_count > 0


def test_sparse_stochastic_rows_keep_their_probabilities_and_declared_axes() -> None:
    spec = FiniteModelSpec.model_validate(
        {
            "name": "noisy sensor",
            "states": ["z", "a"],
            "actions": ["wait"],
            "observations": ["same"],
            "transitions": [
                {"state": "z", "action": "wait", "next_state": "z", "probability": 0.25},
                {"state": "z", "action": "wait", "next_state": "a", "probability": 0.75},
                {"state": "a", "action": "wait", "next_state": "a"},
            ],
            "likelihoods": [
                {"state": "z", "observation": "same"},
                {"state": "a", "observation": "same"},
            ],
            "prior": [{"state": "z", "probability": 0.4}, {"state": "a", "probability": 0.6}],
        }
    )

    model = compile_finite_model(spec)

    assert model.states == ("z", "a")
    assert model.A == ((1.0, 1.0),)
    assert model.B == (((0.25,), (0.0,)), ((0.75,), (1.0,)))
    assert model.C == (0.0,)
    assert model.D == (0.4, 0.6)
    assert verify_finite_model(spec, model).passed


@pytest.mark.parametrize("actions", list(itertools.product(range(2), repeat=5)))
def test_aliased_counter_trace_matches_bounded_integer_logic(actions: tuple[int, ...]) -> None:
    source = SPEC.with_name("counter.json")
    model = compile_finite_model(FiniteModelSpec.model_validate_json(source.read_text()))
    belief, reference_state = list(model.D), 0

    for action in actions:
        reference_state = min(reference_state + 1, 2) if action == 0 else 0
        belief = [
            sum(model.B[target][state][action] * belief[state] for state in range(3))
            for target in range(3)
        ]
        observed = [sum(row[state] * belief[state] for state in range(3)) for row in model.A]
        assert belief == [float(state == reference_state) for state in range(3)]
        assert observed == [float(reference_state < 2), float(reference_state == 2)]


def test_runtime_mutation_preserves_the_compiled_artifact(toggle: FiniteModelSpec) -> None:
    model = compile_finite_model(toggle)
    original = model.model_dump_json()
    runtime = model.to_runtime()

    runtime.A[0][0] = 0.5
    runtime.B[0][0][0] = 0.5
    runtime.C[0] = 5.0
    runtime.D[0] = 0.5

    assert model.model_dump_json() == original


def test_verification_counts_all_differences_when_counterexamples_are_bounded() -> None:
    labels = [str(index) for index in range(20)]
    spec = FiniteModelSpec.model_validate(
        {
            "name": "cycle",
            "states": labels,
            "actions": ["advance"],
            "observations": ["seen"],
            "transitions": [
                {"state": label, "action": "advance", "next_state": labels[(index + 1) % 20]}
                for index, label in enumerate(labels)
            ],
            "likelihoods": [{"state": label, "observation": "seen"} for label in labels],
            "prior": [{"state": "0", "probability": 1.0}],
        }
    )
    data = compile_finite_model(spec).model_dump(mode="json")
    data["B"] = [[[float(target == state)] for state in range(20)] for target in range(20)]

    report = verify_finite_model(spec, FiniteModel.model_validate(data))

    assert not report.passed
    assert report.mismatch_count == 40
    assert len(report.counterexamples) == 32
    assert report.checked_entries == 441
