"""Independent numerical controls for fixed-policy log-preference gradients."""

from __future__ import annotations

import math

import pytest

from cogant.runtime.categorical import CategoricalModel


def model(preferences: list[float]) -> CategoricalModel:
    return CategoricalModel(
        [[0.7, 0.1], [0.2, 0.3], [0.1, 0.6]],
        [[[0.9, 0.2], [0.4, 0.7]], [[0.1, 0.8], [0.6, 0.3]]],
        preferences,
        [0.65, 0.35],
    )


@pytest.mark.parametrize("policy", [[0], [1], [0, 1, 1], [1, 0, 1, 0]])
@pytest.mark.parametrize("delta", [1e-4, 1e-5])
def test_gradient_matches_coordinate_central_differences(policy: list[int], delta: float) -> None:
    # Given: asymmetric stochastic matrices and nonuniform log preferences.
    preferences = [-0.7, 0.2, 1.1]
    candidate = model(preferences)
    reference = []
    for coordinate in range(len(preferences)):
        upper, lower = preferences.copy(), preferences.copy()
        upper[coordinate] += delta
        lower[coordinate] -= delta
        reference.append(
            (model(upper).score(candidate.D, policy) - model(lower).score(candidate.D, policy))
            / (2 * delta)
        )
    # When: differentiating the fixed-policy objective analytically.
    gradient = candidate.score_preference_gradient(candidate.D, policy)
    # Then: every observation-axis coordinate matches an independent perturbation.
    assert gradient == pytest.approx(reference, abs=2e-9)


def test_gradient_matches_hand_calculated_policy_order() -> None:
    # Given: identity and swap actions with preferred outcome probabilities 1/4, 3/4.
    candidate = CategoricalModel(
        [[1.0, 0.0], [0.0, 1.0]],
        [[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]],
        [0.0, math.log(3)],
        [1.0, 0.0],
    )
    # When: the policies visit outcomes (0,1) and (1,1), respectively.
    gradients = [candidate.score_preference_gradient(candidate.D, p) for p in ([0, 1], [1, 0])]
    # Then: horizon*preferred minus outcome counts retains temporal action order.
    assert gradients[0] == pytest.approx([-0.5, 0.5])
    assert gradients[1] == pytest.approx([0.5, -0.5])


@pytest.mark.parametrize("offset", [0.0, 1000.0, -1000.0])
def test_gradient_respects_log_preference_offset_invariance(offset: float) -> None:
    # Given: equivalent preference encodings and a fixed mixed policy.
    candidate = model([offset - 1, offset, offset + 1])
    reference = model([-1.0, 0.0, 1.0])
    # When: applying a common additive offset to all preferences.
    gradient = candidate.score_preference_gradient(candidate.D, [1, 0, 0])
    # Then: the sensitivity is unchanged and has no component along that offset.
    assert gradient == pytest.approx(reference.score_preference_gradient(reference.D, [1, 0, 0]))
    assert math.fsum(gradient) == pytest.approx(0, abs=1e-14)


def test_gradient_remains_finite_for_saturated_preferences() -> None:
    # Given: finite logits whose ordinary exponentials overflow or underflow.
    candidate = model([-1000.0, 0.0, 1000.0])
    # When: computing sensitivity in the saturated regime.
    gradient = candidate.score_preference_gradient(candidate.D, [1])
    # Then: the limiting preferred outcome has probability one.
    assert gradient == pytest.approx([-0.325, -0.2625, 0.5875])


def test_gradient_tracks_probability_mass_within_admission_tolerance() -> None:
    # Given: stochastic columns accepted within the kernel's sum tolerance.
    candidate = CategoricalModel([[1.0000005]], [[[1.0]]], [0.0], [1.0])
    # When: differentiating a one-outcome score, whose log softmax is constant.
    gradient = candidate.score_preference_gradient(candidate.D, [0])
    # Then: rounding tolerance cannot create a spurious preference derivative.
    assert gradient == [0.0]


@pytest.mark.parametrize("policy", [[], [-1], [2], [True]])
def test_gradient_rejects_invalid_policies(policy: list[int]) -> None:
    # Given: a model with exactly two declared actions.
    candidate = model([0.0, 0.0, 0.0])
    # When / Then: empty policies and invalid action indices cannot produce a derivative.
    with pytest.raises(ValueError):
        candidate.score_preference_gradient(candidate.D, policy)


@pytest.mark.parametrize("beliefs", [[], [1.0], [0.5, 0.6], [-0.1, 1.1], [math.nan, 0.5]])
def test_gradient_rejects_invalid_beliefs(beliefs: list[float]) -> None:
    # Given: an admitted model with a two-state belief axis.
    candidate = model([0.0, 0.0, 0.0])
    # When / Then: malformed beliefs fail through the shared numerical contract.
    with pytest.raises(ValueError):
        candidate.score_preference_gradient(beliefs, [0])
