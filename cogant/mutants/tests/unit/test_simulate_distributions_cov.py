"""Behavioral tests for cogant.simulate.distributions.

Exercises CategoricalDistribution arithmetic (entropy, KL divergence,
Bayesian update, sampling determinism via seeding) and TransitionMatrix
construction.
"""

from __future__ import annotations

import math
import random

import pytest

from cogant.simulate.distributions import CategoricalDistribution, TransitionMatrix
from cogant.statespace.compiler import Action, StateSpaceModel, Transition
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType

# --------------------------- CategoricalDistribution -------------------- #


def test_uniform_distribution_defaults():
    """Without explicit probabilities, each category gets 1/n."""
    d = CategoricalDistribution(["a", "b", "c", "d"])
    assert d.probabilities == [0.25] * 4
    assert d.dist == {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}


def test_explicit_probabilities_are_normalized():
    """Non-normalized probabilities get rescaled to sum to 1."""
    d = CategoricalDistribution(["a", "b"], [2.0, 3.0])
    # 2/5 and 3/5
    assert d.dist["a"] == pytest.approx(0.4)
    assert d.dist["b"] == pytest.approx(0.6)


def test_empty_categories_produces_empty_distribution():
    """Empty category list is a legitimate edge case."""
    d = CategoricalDistribution([])
    assert d.n == 0
    assert d.probabilities == []
    assert d.dist == {}


def test_mismatched_probability_count_raises():
    with pytest.raises(ValueError):
        CategoricalDistribution(["a", "b"], [0.5])


def test_zero_probability_sum_raises():
    with pytest.raises(ValueError):
        CategoricalDistribution(["a", "b"], [0.0, 0.0])


def test_sample_with_fixed_seed_is_deterministic():
    """Seeding the stdlib RNG makes sampling deterministic."""
    d = CategoricalDistribution(["a", "b", "c"], [0.1, 0.8, 0.1])
    random.seed(42)
    s1 = [d.sample() for _ in range(100)]
    random.seed(42)
    s2 = [d.sample() for _ in range(100)]
    assert s1 == s2
    # Given the 0.8 weight, 'b' should dominate
    assert s1.count("b") > s1.count("a")
    assert s1.count("b") > s1.count("c")


def test_log_prob_returns_log_of_probability():
    d = CategoricalDistribution(["a", "b"], [0.25, 0.75])
    assert d.log_prob("a") == pytest.approx(math.log(0.25))
    assert d.log_prob("b") == pytest.approx(math.log(0.75))


def test_log_prob_unknown_category_raises():
    d = CategoricalDistribution(["a", "b"])
    with pytest.raises(KeyError):
        d.log_prob("c")


def test_log_prob_zero_probability_returns_neg_inf():
    """A category can legitimately have probability 0 after an update."""
    # Normalisation of [1, 0] gives [1.0, 0.0] which is allowed.
    d = CategoricalDistribution(["a", "b"], [1.0, 0.0])
    assert d.log_prob("b") == float("-inf")


def test_entropy_uniform_matches_log_n():
    """Uniform distribution has entropy log(n)."""
    d = CategoricalDistribution(["a", "b", "c", "d"])
    assert d.entropy() == pytest.approx(math.log(4))


def test_entropy_degenerate_distribution_is_zero():
    """A distribution placing all mass on one category has zero entropy."""
    d = CategoricalDistribution(["a", "b"], [1.0, 0.0])
    assert d.entropy() == 0.0


def test_kl_divergence_to_self_is_zero():
    d = CategoricalDistribution(["a", "b"], [0.3, 0.7])
    assert d.kl_divergence(d) == pytest.approx(0.0)


def test_kl_divergence_nonzero_for_different_distributions():
    p = CategoricalDistribution(["a", "b"], [0.9, 0.1])
    q = CategoricalDistribution(["a", "b"], [0.5, 0.5])
    assert p.kl_divergence(q) > 0


def test_kl_divergence_returns_inf_when_q_has_zero_and_p_positive():
    p = CategoricalDistribution(["a", "b"], [0.5, 0.5])
    q = CategoricalDistribution(["a", "b"], [1.0, 0.0])
    assert p.kl_divergence(q) == float("inf")


def test_kl_divergence_requires_matching_categories():
    p = CategoricalDistribution(["a", "b"])
    q = CategoricalDistribution(["a", "c"])
    with pytest.raises(ValueError):
        p.kl_divergence(q)


def test_bayesian_update_shifts_mass_toward_observation():
    """Posterior over categories given an observation is proportional to
    prior × likelihood.
    """
    prior = CategoricalDistribution(["a", "b"], [0.5, 0.5])
    # Likelihood indicates 'a' is more consistent with the observation
    likelihood = CategoricalDistribution(["a", "b"], [0.9, 0.1])
    posterior = prior.update("a", likelihood)

    assert posterior.dist["a"] > 0.5
    assert posterior.dist["b"] < 0.5
    # Probabilities are still normalized
    assert sum(posterior.probabilities) == pytest.approx(1.0)


def test_bayesian_update_unknown_observation_raises():
    prior = CategoricalDistribution(["a", "b"])
    likelihood = CategoricalDistribution(["a", "b"])
    with pytest.raises(ValueError):
        prior.update("c", likelihood)


def test_repr_contains_all_categories():
    d = CategoricalDistribution(["x", "y"], [0.2, 0.8])
    text = repr(d)
    assert "x" in text
    assert "y" in text


# --------------------------- TransitionMatrix --------------------------- #


def test_transition_matrix_default_is_uniform():
    """Unset transitions return a uniform distribution over states."""
    m = TransitionMatrix(["s0", "s1"], ["a0"])
    dist = m.get_next_state_dist("s0", "a0")
    assert dist.dist == {"s0": 0.5, "s1": 0.5}


def test_transition_matrix_set_transition_normalizes_remainder():
    """Setting one transition's probability redistributes the rest uniformly."""
    m = TransitionMatrix(["s0", "s1", "s2"], ["a0"])
    m.set_transition("s0", "a0", "s1", 0.8)
    dist = m.get_next_state_dist("s0", "a0")
    assert dist.dist["s1"] == pytest.approx(0.8)
    # Remaining 0.2 split between s0 and s2 → 0.1 each
    assert dist.dist["s0"] == pytest.approx(0.1)
    assert dist.dist["s2"] == pytest.approx(0.1)


def test_transition_matrix_rejects_unknown_state_or_action():
    m = TransitionMatrix(["s0"], ["a0"])
    with pytest.raises(ValueError):
        m.set_transition("bogus", "a0", "s0", 1.0)
    with pytest.raises(ValueError):
        m.set_transition("s0", "bogus", "s0", 1.0)
    with pytest.raises(ValueError):
        m.set_transition("s0", "a0", "bogus", 1.0)
    with pytest.raises(ValueError):
        m.get_next_state_dist("bogus", "a0")
    with pytest.raises(ValueError):
        m.get_next_state_dist("s0", "bogus")


def test_transition_matrix_repr_includes_counts():
    m = TransitionMatrix(["s0", "s1"], ["a0", "a1"])
    assert "2 states" in repr(m)
    assert "2 actions" in repr(m)


def _minimal_state_space() -> StateSpaceModel:
    return StateSpaceModel(
        id="m",
        schema_name="m",
        variables={
            "s0": StateVariable(
                id="s0", name="s0", var_type=StateVariableType.BOOLEAN, node_id="n0"
            ),
            "s1": StateVariable(
                id="s1", name="s1", var_type=StateVariableType.BOOLEAN, node_id="n1"
            ),
        },
        observations={},
        actions={"a0": Action(id="a0", name="a0", controller_id="c0")},
        transitions={
            "s0_s1": Transition(
                id="s0_s1",
                source_state={"s0": "pre"},
                target_state={"s1": "post"},
                action_id="a0",
            )
        },
        likelihoods={},
        preferences={},
        time_regime=TimeRegime.SYNCHRONOUS,
    )


def test_transition_matrix_from_state_space_builds_matrix():
    """from_state_space constructs the matrix without raising."""
    ss = _minimal_state_space()
    m = TransitionMatrix.from_state_space(ss)
    assert set(m.states) == {"s0", "s1"}
    assert m.actions == ["a0"]
