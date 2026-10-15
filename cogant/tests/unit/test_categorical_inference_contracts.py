import math

import pytest

from cogant.runtime.loop import AgentRuntime
from cogant.simulate.free_energy import bayesian_belief_update, expected_free_energy


def test_informative_likelihood_has_lower_risk_and_ambiguity_than_aliasing() -> None:
    # Given: identical outcome marginals with different state information.
    belief = [0.5, 0.5]
    transition = [[[1.0], [0.0]], [[0.0], [1.0]]]
    informative = [[1.0, 0.0], [0.0, 1.0]]
    aliased = [[0.5, 0.5], [0.5, 0.5]]
    # When: the same candidate action is evaluated under each likelihood.
    scores = [
        expected_free_energy([0], belief, a, transition, [0.0, 0.0]) for a in (informative, aliased)
    ]
    # Then: risk is zero for both; only the aliased model has ambiguity.
    assert scores == pytest.approx([0.0, math.log(2.0)])


def test_policy_score_is_invariant_to_a_constant_log_preference_offset() -> None:
    # Given: a deterministic model and two equivalent preference encodings.
    a = [[1.0, 0.0], [0.0, 1.0]]
    b = [[[1.0], [0.0]], [[0.0], [1.0]]]
    # When: preferences receive a common additive constant.
    scores = [
        expected_free_energy([0], [0.25, 0.75], a, b, c) for c in ([0.0, 2.0], [1000.0, 1002.0])
    ]
    # Then: softmax preferences and the categorical objective are unchanged.
    assert scores[0] == pytest.approx(scores[1])


def test_observation_with_zero_evidence_is_rejected() -> None:
    # Given: the second observation cannot occur under any state.
    likelihood = [[1.0, 1.0], [0.0, 0.0]]
    # When / Then: conditioning cannot manufacture a posterior.
    with pytest.raises(ValueError, match="evidence"):
        bayesian_belief_update([0.5, 0.5], likelihood, 1)


@pytest.mark.parametrize("observation", [-1, 2])
def test_runtime_rejects_an_observation_outside_its_axis(observation: int) -> None:
    # Given: a two-outcome categorical model.
    runtime = AgentRuntime.from_matrices_dict(
        {
            "A": [[1.0, 0.0], [0.0, 1.0]],
            "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
            "C": [0.0, 0.0],
            "D": [0.8, 0.2],
        }
    )
    # When / Then: negative indexing and silent observation substitution fail.
    with pytest.raises((IndexError, ValueError), match="observation"):
        runtime.step([0.8, 0.2], observation)


def test_runtime_free_energy_refers_to_filtering_before_control() -> None:
    # Given: observation zero identifies state zero; preferences favor flipping.
    runtime = AgentRuntime.from_matrices_dict(
        {
            "A": [[1.0, 0.0], [0.0, 1.0]],
            "B": [[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]],
            "C": [0.0, 10.0],
            "D": [0.8, 0.2],
        }
    )
    # When: filtering and action selection run in one perception-action cycle.
    result = runtime.step([0.8, 0.2], 0)
    # Then: optimal filtering F equals negative log observation evidence.
    assert result.action == 1
    assert result.free_energy == pytest.approx(-math.log(0.8))
