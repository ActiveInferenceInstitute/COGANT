"""``TransitionMatrix.from_state_space`` must reproduce the empirical counts.

When one (source, action) pair leads to several targets, the estimated
row must be the normalised count vector. Building it through repeated
``set_transition`` calls re-spread the remaining mass uniformly on every
call, overwriting the probabilities set by earlier calls, so only the
last target kept its estimate and unobserved targets received mass.
"""

from __future__ import annotations

import pytest

from cogant.runtime.categorical import CategoricalModel
from cogant.simulate.distributions import CategoricalDistribution, TransitionMatrix
from cogant.simulate.free_energy import FreeEnergyCalculator
from cogant.statespace.compiler import Action, ObservationModality, StateSpaceModel, Transition
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType


def _state_space(transitions: dict[str, Transition]) -> StateSpaceModel:
    variables = {
        vid: StateVariable(id=vid, name=vid, var_type=StateVariableType.DISCRETE, node_id=vid)
        for vid in ("v1", "v2", "v3")
    }
    return StateSpaceModel(
        id="ss",
        schema_name="counts",
        time_regime=TimeRegime.SYNCHRONOUS,
        variables=variables,
        observations={},
        actions={"a1": Action(id="a1", name="a1", controller_id="ctrl", effects=[])},
        transitions=transitions,
        likelihoods={},
        preferences={},
    )


def _trans(tid: str, source: list[str], target: list[str]) -> Transition:
    return Transition(
        id=tid,
        source_state=dict.fromkeys(source, "pre"),
        target_state=dict.fromkeys(target, "post"),
        action_id="a1",
    )


def test_multi_target_transition_splits_mass_only_over_observed_targets() -> None:
    ss = _state_space({"t1": _trans("t1", ["v1"], ["v2", "v3"])})

    dist = TransitionMatrix.from_state_space(ss).get_next_state_dist("v1", "a1")

    assert dist.dist == pytest.approx({"v1": 0.0, "v2": 0.5, "v3": 0.5})


def test_repeated_transitions_yield_count_proportional_row() -> None:
    ss = _state_space(
        {
            "t1": _trans("t1", ["v1"], ["v2"]),
            "t2": _trans("t2", ["v1"], ["v2"]),
            "t3": _trans("t3", ["v1"], ["v3"]),
        }
    )

    dist = TransitionMatrix.from_state_space(ss).get_next_state_dist("v1", "a1")

    assert dist.dist == pytest.approx({"v1": 0.0, "v2": 2 / 3, "v3": 1 / 3})


def test_unobserved_source_rows_stay_uniform() -> None:
    ss = _state_space({"t1": _trans("t1", ["v1"], ["v2", "v3"])})

    dist = TransitionMatrix.from_state_space(ss).get_next_state_dist("v2", "a1")

    assert dist.probabilities == pytest.approx([1 / 3, 1 / 3, 1 / 3])


def test_free_energy_predicted_beliefs_follow_estimated_transitions() -> None:
    ss = _state_space({"t1": _trans("t1", ["v1"], ["v2", "v3"])})
    ss.observations["o"] = ObservationModality(
        id="o", name="Observed outcome", source_node_id="sensor", modality_type="sensor"
    )
    states = list(ss.variables)
    estimated = TransitionMatrix.from_state_space(ss)
    columns = [estimated.get_next_state_dist(source, "a1").dist for source in states]
    matrices = CategoricalModel(
        A=[[1.0] * len(states)],
        B=[[[column[target]] for column in columns] for target in states],
        C=[0.0],
        D=[1 / len(states)] * len(states),
    )
    calc = FreeEnergyCalculator(ss, matrices)

    predicted = calc._predict_beliefs(CategoricalDistribution(["v1", "v2", "v3"], [1, 0, 0]), "a1")

    assert predicted.dist == pytest.approx({"v1": 0.0, "v2": 0.5, "v3": 0.5})


def test_free_energy_requires_explicit_observation_and_prior_matrices() -> None:
    ss = _state_space({})
    with pytest.raises(ValueError, match="explicit A/B/C/D"):
        FreeEnergyCalculator(ss)
