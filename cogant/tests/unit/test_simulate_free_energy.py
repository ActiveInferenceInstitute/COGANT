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


def test_vfe_zero_states_rejects_invalid_input():
    from cogant.simulate.free_energy import variational_free_energy

    with pytest.raises(ValueError, match="nonempty"):
        variational_free_energy([], [], [[1.0]], [1.0])


def test_vfe_no_observation_model_rejects_invalid_input():
    from cogant.simulate.free_energy import variational_free_energy

    with pytest.raises(ValueError, match="likelihood"):
        variational_free_energy([0.7, 0.3], [0.5, 0.5], [], [])


def test_vfe_uniform_observation_rejects_invalid_input():
    from cogant.simulate.free_energy import variational_free_energy

    with pytest.raises(ValueError, match="explicit observation"):
        variational_free_energy([1.0, 0.0], [0.5, 0.5], [[0.9, 0.1], [0.1, 0.9]])


def test_vfe_with_explicit_observation_distribution():
    beliefs = [0.5, 0.5]
    prior = [0.5, 0.5]
    A = [[0.9, 0.1], [0.1, 0.9]]
    obs = [1.0, 0.0]  # observed o=0
    vfe = variational_free_energy(beliefs, prior, A, observation=obs)
    assert isinstance(vfe, float)


def test_vfe_prior_length_mismatch_raises():
    from cogant.simulate.free_energy import variational_free_energy

    with pytest.raises(ValueError, match="incompatible dimensions"):
        variational_free_energy([0.5, 0.5], [1.0], [[0.9, 0.1], [0.1, 0.9]], [1.0, 0.0])


def test_vfe_likelihood_row_shape_mismatch_raises():
    from cogant.simulate.free_energy import variational_free_energy

    with pytest.raises(ValueError, match="likelihood"):
        variational_free_energy([0.5, 0.5], [0.5, 0.5], [[1.0]], [1.0])


def test_vfe_observation_length_mismatch_raises():
    from cogant.simulate.free_energy import variational_free_energy

    with pytest.raises(ValueError, match="observation distribution"):
        variational_free_energy([0.5, 0.5], [0.5, 0.5], [[1.0, 0.0], [0.0, 1.0]], [1.0])


# --------------------------- bayesian_belief_update -------------------- #


def test_bayesian_update_empty_prior_rejects_invalid_input():
    from cogant.simulate.free_energy import bayesian_belief_update

    with pytest.raises(ValueError, match="nonempty"):
        bayesian_belief_update([], [[1.0]], 0)


def test_bayesian_update_normalizes_to_one():
    """Posterior probabilities sum to 1."""
    prior = [0.5, 0.5]
    A = [[0.9, 0.1], [0.1, 0.9]]
    posterior = bayesian_belief_update(prior, A, observation_index=0)
    assert sum(posterior) == pytest.approx(1.0, abs=1e-9)
    # Observing o=0 with A[0]=[0.9,0.1] biases toward state 0
    assert posterior[0] > posterior[1]


def test_bayesian_update_index_out_of_range_raises():
    from cogant.simulate.free_energy import bayesian_belief_update

    with pytest.raises(ValueError, match="observation index"):
        bayesian_belief_update([0.5, 0.5], [[0.9, 0.1], [0.1, 0.9]], 5)


def test_bayesian_update_zero_likelihood_rejects_invalid_input():
    from cogant.simulate.free_energy import bayesian_belief_update

    with pytest.raises(ValueError, match="zero evidence"):
        bayesian_belief_update([0.4, 0.6], [[0.0, 0.0], [1.0, 1.0]], 0)


# --------------------------- expected_free_energy ---------------------- #


def test_efe_zero_states_rejects_invalid_input():
    from cogant.simulate.free_energy import expected_free_energy

    with pytest.raises(ValueError, match="nonempty"):
        expected_free_energy([0], [], [[1.0]], [[[1.0]]], [0.0])


def test_efe_empty_policy_rejects_invalid_input():
    from cogant.simulate.free_energy import expected_free_energy

    with pytest.raises(ValueError, match="policy"):
        expected_free_energy([], [0.5, 0.5], [[1.0, 1.0]], [[[1.0], [0.0]], [[0.0], [1.0]]], [0.0])


def test_efe_no_observation_model_rejects_invalid_input():
    from cogant.simulate.free_energy import expected_free_energy

    with pytest.raises(ValueError, match="likelihood"):
        expected_free_energy([0], [0.5, 0.5], [], [[[1.0], [0.0]], [[0.0], [1.0]]], [])


def test_efe_log_preferences_length_mismatch_raises():
    from cogant.simulate.free_energy import expected_free_energy

    with pytest.raises(ValueError, match="preferences"):
        expected_free_energy(
            [0], [0.5, 0.5], [[1.0, 0.0], [0.0, 1.0]], [[[1.0], [0.0]], [[0.0], [1.0]]], [0.0]
        )


def test_efe_returns_float_for_well_formed_inputs():
    """A well-formed call returns a finite float."""
    _n_states, _n_obs, _n_actions = 2, 2, 1
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


def test_uniform_distribution_rejects_nonpositive_dimension():
    for dimension in (0, -3):
        with pytest.raises(ValueError, match="positive"):
            uniform_distribution(dimension)


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
            ),
            "o2": ObservationModality(
                id="o2", name="o2", source_node_id="n1", modality_type="event"
            ),
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


def _calculator():
    from cogant.runtime.categorical import CategoricalModel

    matrices = CategoricalModel(
        [[0.9, 0.1], [0.1, 0.9]],
        [[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]],
        [0.0, 1.0],
        [0.5, 0.5],
    )
    return FreeEnergyCalculator(_state_space(), matrices=matrices)


def test_calculator_initializes_with_state_space():
    fec = _calculator()
    assert "s0" in fec.states
    assert "a0" in fec.actions
    assert fec.model.B is not None


def test_calculator_variational_free_energy_default_likelihood():
    fec = _calculator()
    beliefs = CategoricalDistribution(fec.states, [0.5, 0.5])
    vfe = fec.variational_free_energy(beliefs, "o1")
    assert math.isfinite(vfe)


def test_calculator_variational_free_energy_with_explicit_likelihood():
    """VFE accepts an explicit likelihood mapping."""
    fec = _calculator()
    beliefs = CategoricalDistribution(fec.states, [0.7, 0.3])
    likelihood = {
        "o1": CategoricalDistribution(fec.states, [0.9, 0.1]),
        "o2": CategoricalDistribution(fec.states, [0.1, 0.9]),
    }
    vfe = fec.variational_free_energy(beliefs, "o1", likelihood_model=likelihood)
    assert math.isfinite(vfe)


def test_calculator_expected_free_energy_empty_policy_raises():
    fec = _calculator()
    beliefs = CategoricalDistribution(fec.states, [0.5, 0.5])
    with pytest.raises(ValueError, match="policy"):
        fec.expected_free_energy(beliefs, [])


def test_calculator_expected_free_energy_unknown_action_raises():
    fec = _calculator()
    beliefs = CategoricalDistribution(fec.states, [0.5, 0.5])
    with pytest.raises(ValueError):
        fec.expected_free_energy(beliefs, ["bogus"])


def test_calculator_expected_free_energy_with_known_policy():
    """A valid policy returns a finite EFE."""
    fec = _calculator()
    beliefs = CategoricalDistribution(fec.states, [0.5, 0.5])
    efe = fec.expected_free_energy(beliefs, ["a0", "a1"], horizon=2)
    assert math.isfinite(efe)


def test_calculator_surprisal_complexity_accuracy():
    """surprisal/complexity/accuracy each return finite floats."""
    fec = _calculator()
    beliefs = CategoricalDistribution(fec.states, [0.6, 0.4])
    s = fec.surprisal("o1", beliefs)
    c = fec.complexity(beliefs)
    a = fec.accuracy("o1", beliefs)
    assert math.isfinite(s)
    assert math.isfinite(c)
    assert math.isfinite(a)


def test_calculator_complexity_with_explicit_prior():
    fec = _calculator()
    posterior = CategoricalDistribution(fec.states, [0.9, 0.1])
    prior = CategoricalDistribution(fec.states, [0.5, 0.5])
    c = fec.complexity(posterior, prior=prior)
    assert c > 0


def test_calculator_predict_beliefs_unknown_action_raises():
    fec = _calculator()
    beliefs = CategoricalDistribution(fec.states, [0.6, 0.4])
    with pytest.raises(ValueError):
        fec._predict_beliefs(beliefs, "ghost")


def test_calculator_predict_beliefs_known_action_returns_distribution():
    """_predict_beliefs with a real action returns a new distribution."""
    fec = _calculator()
    beliefs = CategoricalDistribution(fec.states, [0.6, 0.4])
    result = fec._predict_beliefs(beliefs, "a0")
    assert isinstance(result, CategoricalDistribution)
    assert sum(result.probabilities) == pytest.approx(1.0, abs=1e-6)


def test_calculator_policy_ranking_returns_sorted_list():
    """policy_ranking sorts actions by EFE ascending."""
    fec = _calculator()
    beliefs = CategoricalDistribution(fec.states, [0.5, 0.5])
    ranking = fec.policy_ranking(beliefs, ["a0", "a1"], horizon=1)
    assert len(ranking) == 2
    # Sorted ascending by EFE
    assert ranking[0][1] <= ranking[1][1]
