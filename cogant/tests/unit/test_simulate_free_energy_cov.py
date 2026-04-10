"""Behavioral tests for cogant.simulate.free_energy.

Drives the principled matrix-based functions with handcrafted POMDP
matrices and exercises the FreeEnergyCalculator wrapper using a real
StateSpaceModel.
"""

from __future__ import annotations

import math

import pytest

from cogant.simulate.distributions import CategoricalDistribution
from cogant.simulate.free_energy import (
    FreeEnergyCalculator,
    bayesian_belief_update,
    expected_free_energy,
    uniform_distribution,
    variational_free_energy,
)
from cogant.statespace.compiler import (
    Action,
    ObservationModality,
    StateSpaceModel,
    Transition,
)
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType


# --------------------------- variational_free_energy ------------------- #


def test_vfe_zero_states_returns_zero():
    """An empty belief vector short-circuits to 0."""
    assert variational_free_energy([], [], [[1.0]]) == 0.0


def test_vfe_no_observation_model_reduces_to_kl():
    """When the likelihood matrix is empty VFE collapses to KL[Q||P]."""
    beliefs = [0.7, 0.3]
    prior = [0.5, 0.5]
    vfe = variational_free_energy(beliefs, prior, [])
    # KL[Q||P] = 0.7*log(0.7/0.5) + 0.3*log(0.3/0.5)
    expected = 0.7 * math.log(0.7 / 0.5) + 0.3 * math.log(0.3 / 0.5)
    assert vfe == pytest.approx(expected, abs=1e-9)


def test_vfe_uniform_observation_default():
    """When no observation is given, a uniform observation is assumed."""
    beliefs = [1.0, 0.0]
    prior = [0.5, 0.5]
    A = [[0.9, 0.1], [0.1, 0.9]]  # 2 obs x 2 states
    vfe = variational_free_energy(beliefs, prior, A)
    assert isinstance(vfe, float)


def test_vfe_with_explicit_observation_distribution():
    """An explicit observation distribution overrides the uniform default."""
    beliefs = [0.5, 0.5]
    prior = [0.5, 0.5]
    A = [[0.9, 0.1], [0.1, 0.9]]
    obs = [1.0, 0.0]  # observed o=0
    vfe = variational_free_energy(beliefs, prior, A, observation=obs)
    assert isinstance(vfe, float)


def test_vfe_prior_length_mismatch_raises():
    """A mismatched prior length raises ValueError."""
    with pytest.raises(ValueError, match="prior length"):
        variational_free_energy([0.5, 0.5], [0.5], [[1.0, 0.0]])


def test_vfe_likelihood_row_shape_mismatch_raises():
    """A row in the A matrix with wrong width raises ValueError."""
    with pytest.raises(ValueError, match="likelihood_matrix rows"):
        variational_free_energy(
            [0.5, 0.5], [0.5, 0.5], [[1.0]]  # row should have 2 entries
        )


def test_vfe_observation_length_mismatch_raises():
    """An observation vector of the wrong length raises ValueError."""
    with pytest.raises(ValueError, match="observation length"):
        variational_free_energy(
            [0.5, 0.5], [0.5, 0.5], [[1.0, 0.0], [0.0, 1.0]], observation=[1.0]
        )


# --------------------------- bayesian_belief_update -------------------- #


def test_bayesian_update_empty_prior_returns_empty():
    """Empty prior returns empty posterior."""
    assert bayesian_belief_update([], [[1.0]], 0) == []


def test_bayesian_update_normalizes_to_one():
    """Posterior probabilities sum to 1."""
    prior = [0.5, 0.5]
    A = [[0.9, 0.1], [0.1, 0.9]]
    posterior = bayesian_belief_update(prior, A, observation_index=0)
    assert sum(posterior) == pytest.approx(1.0, abs=1e-9)
    # Observing o=0 with A[0]=[0.9,0.1] biases toward state 0
    assert posterior[0] > posterior[1]


def test_bayesian_update_index_out_of_range_raises():
    """An out-of-range observation index raises IndexError."""
    with pytest.raises(IndexError):
        bayesian_belief_update([0.5, 0.5], [[1.0, 0.0]], observation_index=5)


def test_bayesian_update_zero_likelihood_falls_back_to_prior():
    """When the row is all zeros the posterior equals the prior."""
    prior = [0.4, 0.6]
    A = [[0.0, 0.0]]
    posterior = bayesian_belief_update(prior, A, observation_index=0)
    assert posterior == [0.4, 0.6]


# --------------------------- expected_free_energy ---------------------- #


def test_efe_zero_states_returns_zero():
    """Empty belief vector short-circuits."""
    assert expected_free_energy([0], [], [[1.0]], [[[1.0]]], [0.0]) == 0.0


def test_efe_empty_policy_returns_zero():
    """Empty policy short-circuits."""
    assert expected_free_energy([], [0.5, 0.5], [[1.0, 0.0]], [[[1.0]]], [0.0]) == 0.0


def test_efe_no_observation_model_returns_zero():
    """No likelihood rows short-circuits."""
    assert expected_free_energy([0], [0.5, 0.5], [], [[[1.0]]], []) == 0.0


def test_efe_log_preferences_length_mismatch_raises():
    """A C vector of the wrong length raises ValueError."""
    with pytest.raises(ValueError, match="log_preferences length"):
        expected_free_energy(
            [0],
            [0.5, 0.5],
            [[1.0, 0.0], [0.0, 1.0]],
            [[[1.0], [0.0]], [[0.0], [1.0]]],
            log_preferences=[0.0],  # should be length 2
        )


def test_efe_returns_float_for_well_formed_inputs():
    """A well-formed call returns a finite float."""
    n_states, n_obs, n_actions = 2, 2, 1
    beliefs = [0.5, 0.5]
    A = [[0.9, 0.1], [0.1, 0.9]]
    # B[s_next][s][a]
    B = [[[1.0], [0.0]], [[0.0], [1.0]]]
    C = [0.0, 1.0]
    result = expected_free_energy([0, 0], beliefs, A, B, C)
    assert isinstance(result, float)
    assert math.isfinite(result)


# --------------------------- uniform_distribution ---------------------- #


def test_uniform_distribution_positive_n():
    """uniform_distribution sums to 1 for positive n."""
    d = uniform_distribution(4)
    assert len(d) == 4
    assert sum(d) == pytest.approx(1.0)
    assert all(x == pytest.approx(0.25) for x in d)


def test_uniform_distribution_zero_or_negative_returns_empty():
    """Non-positive n returns the empty list."""
    assert uniform_distribution(0) == []
    assert uniform_distribution(-3) == []


# --------------------------- FreeEnergyCalculator ---------------------- #


def _state_space() -> StateSpaceModel:
    """Build a small 2-state, 2-action StateSpaceModel."""
    return StateSpaceModel(
        id="m1",
        schema_name="test",
        variables={
            "s0": StateVariable(
                id="s0",
                name="s0",
                var_type=StateVariableType.BOOLEAN,
                node_id="n1",
            ),
            "s1": StateVariable(
                id="s1",
                name="s1",
                var_type=StateVariableType.BOOLEAN,
                node_id="n1",
            ),
        },
        observations={
            "o1": ObservationModality(
                id="o1", name="o1", source_node_id="n1", modality_type="event"
            )
        },
        actions={
            "a0": Action(id="a0", name="a0", controller_id="n1", effects=["s0"]),
            "a1": Action(id="a1", name="a1", controller_id="n1", effects=["s1"]),
        },
        transitions={
            "t0": Transition(
                id="t0",
                source_state={"s0": "true"},
                target_state={"s1": "true"},
                action_id="a0",
            )
        },
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def test_calculator_initializes_with_state_space():
    """Constructor caches states, actions, and transition matrix."""
    fec = FreeEnergyCalculator(_state_space())
    assert "s0" in fec.states
    assert "a0" in fec.actions
    assert fec.transition_matrix is not None


def test_calculator_variational_free_energy_default_likelihood():
    """VFE returns a finite float using the built-in default likelihood."""
    fec = FreeEnergyCalculator(_state_space())
    beliefs = CategoricalDistribution(fec.states, [0.5, 0.5])
    vfe = fec.variational_free_energy(beliefs, "s0")
    assert math.isfinite(vfe)


def test_calculator_variational_free_energy_with_explicit_likelihood():
    """VFE accepts an explicit likelihood mapping."""
    fec = FreeEnergyCalculator(_state_space())
    beliefs = CategoricalDistribution(fec.states, [0.7, 0.3])
    likelihood = {"s0": CategoricalDistribution(fec.states, [0.9, 0.1])}
    vfe = fec.variational_free_energy(beliefs, "s0", likelihood_model=likelihood)
    assert math.isfinite(vfe)


def test_calculator_expected_free_energy_empty_policy_is_inf():
    """Empty policy returns +inf."""
    fec = FreeEnergyCalculator(_state_space())
    beliefs = CategoricalDistribution(fec.states, [0.5, 0.5])
    assert fec.expected_free_energy(beliefs, []) == float("inf")


def test_calculator_expected_free_energy_unknown_action_is_inf():
    """A policy referencing an unknown action returns +inf."""
    fec = FreeEnergyCalculator(_state_space())
    beliefs = CategoricalDistribution(fec.states, [0.5, 0.5])
    assert fec.expected_free_energy(beliefs, ["bogus"]) == float("inf")


def test_calculator_expected_free_energy_with_known_policy():
    """A valid policy returns a finite EFE."""
    fec = FreeEnergyCalculator(_state_space())
    beliefs = CategoricalDistribution(fec.states, [0.5, 0.5])
    efe = fec.expected_free_energy(beliefs, ["a0", "a1"], horizon=2)
    assert math.isfinite(efe)


def test_calculator_surprisal_complexity_accuracy():
    """surprisal/complexity/accuracy each return finite floats."""
    fec = FreeEnergyCalculator(_state_space())
    beliefs = CategoricalDistribution(fec.states, [0.6, 0.4])
    s = fec.surprisal("s0", beliefs)
    c = fec.complexity(beliefs)
    a = fec.accuracy("s0", beliefs)
    assert math.isfinite(s)
    assert math.isfinite(c)
    assert math.isfinite(a)


def test_calculator_complexity_with_explicit_prior():
    """Passing an explicit prior overrides the uniform default."""
    fec = FreeEnergyCalculator(_state_space())
    posterior = CategoricalDistribution(fec.states, [0.9, 0.1])
    prior = CategoricalDistribution(fec.states, [0.5, 0.5])
    c = fec.complexity(posterior, prior=prior)
    assert c > 0


def test_calculator_predict_beliefs_unknown_action_returns_input():
    """_predict_beliefs returns the input unchanged for unknown actions."""
    fec = FreeEnergyCalculator(_state_space())
    beliefs = CategoricalDistribution(fec.states, [0.6, 0.4])
    result = fec._predict_beliefs(beliefs, "ghost")
    assert result is beliefs


def test_calculator_predict_beliefs_known_action_returns_distribution():
    """_predict_beliefs with a real action returns a new distribution."""
    fec = FreeEnergyCalculator(_state_space())
    beliefs = CategoricalDistribution(fec.states, [0.6, 0.4])
    result = fec._predict_beliefs(beliefs, "a0")
    assert isinstance(result, CategoricalDistribution)
    assert sum(result.probabilities) == pytest.approx(1.0, abs=1e-6)


def test_calculator_policy_ranking_returns_sorted_list():
    """policy_ranking sorts actions by EFE ascending."""
    fec = FreeEnergyCalculator(_state_space())
    beliefs = CategoricalDistribution(fec.states, [0.5, 0.5])
    ranking = fec.policy_ranking(beliefs, ["a0", "a1"], horizon=1)
    assert len(ranking) == 2
    # Sorted ascending by EFE
    assert ranking[0][1] <= ranking[1][1]
