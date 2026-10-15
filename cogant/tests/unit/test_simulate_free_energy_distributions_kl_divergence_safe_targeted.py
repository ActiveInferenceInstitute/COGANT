#!/usr/bin/env python3
"""Targeted branch tests — simulate/free_energy.py and simulate/distributions.py.

Covers:
- simulate/free_energy.py: exact zero support, explicit observations,
  invalid-input controls, bayesian_belief_update, expected_free_energy,
  uniform_distribution, FreeEnergyCalculator (basic)
- simulate/distributions.py: CategoricalDistribution (init/uniform/sample/
  log_prob/entropy/kl_divergence/update), TransitionMatrix (init/set_transition/
  get_next_state_dist)
"""

import math

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# simulate/free_energy.py — module-level functions
# ---------------------------------------------------------------------------


class TestExactLikelihoodSupport:
    def test_certain_observation_has_zero_free_energy(self):
        from cogant.simulate.free_energy import variational_free_energy

        assert variational_free_energy([1.0], [1.0], [[1.0]], [1.0]) == 0.0

    def test_zero_likelihood_has_infinite_free_energy(self):
        from cogant.simulate.free_energy import variational_free_energy

        assert math.isinf(variational_free_energy([1.0], [1.0], [[0.0], [1.0]], [1.0, 0.0]))

    def test_half_likelihood_matches_surprisal(self):
        from cogant.simulate.free_energy import variational_free_energy

        value = variational_free_energy([1.0], [1.0], [[0.5], [0.5]], [1.0, 0.0])
        assert value == pytest.approx(math.log(2.0))


class TestVariationalFreeEnergy:
    def test_empty_beliefs_rejected(self):
        from cogant.simulate.free_energy import variational_free_energy

        with pytest.raises(ValueError, match="nonempty"):
            variational_free_energy([], [], [[1.0]], [1.0])

    def test_kl_only_no_obs(self):
        from cogant.simulate.free_energy import variational_free_energy

        with pytest.raises(ValueError, match="likelihood"):
            variational_free_energy([0.8, 0.2], [0.5, 0.5], [], [])

    def test_with_likelihood_and_observation(self):
        from cogant.simulate.free_energy import variational_free_energy

        beliefs = [0.6, 0.4]
        prior = [0.5, 0.5]
        # A: 2 observations, 2 states
        likelihood = [[0.8, 0.2], [0.2, 0.8]]
        obs = [1.0, 0.0]  # Observed obs index 0
        result = variational_free_energy(beliefs, prior, likelihood, obs)
        assert isinstance(result, float)

    def test_observation_none_rejects_invalid_input(self):
        from cogant.simulate.free_energy import variational_free_energy

        with pytest.raises(ValueError, match="explicit observation"):
            variational_free_energy([0.5, 0.5], [0.5, 0.5], [[0.7, 0.3], [0.3, 0.7]], None)

    def test_prior_mismatch_raises(self):
        from cogant.simulate.free_energy import variational_free_energy

        with pytest.raises(ValueError):
            variational_free_energy(
                [0.5, 0.5], [0.3, 0.3, 0.4], [[0.7, 0.3], [0.3, 0.7]], [1.0, 0.0]
            )

    def test_likelihood_row_mismatch_raises(self):
        from cogant.simulate.free_energy import variational_free_energy

        with pytest.raises(ValueError):
            variational_free_energy([0.5, 0.5], [0.5, 0.5], [[0.7]], [1.0])

    def test_observation_mismatch_raises(self):
        from cogant.simulate.free_energy import variational_free_energy

        with pytest.raises(ValueError):
            variational_free_energy(
                [0.5, 0.5],
                [0.5, 0.5],
                [[0.7, 0.3], [0.3, 0.7]],
                [1.0],  # length 1, but n_obs=2
            )


class TestBayesianBeliefUpdate:
    def test_empty_prior_rejects_invalid_input(self):
        from cogant.simulate.free_energy import bayesian_belief_update

        with pytest.raises(ValueError, match="nonempty"):
            bayesian_belief_update([], [[1.0]], 0)

    def test_basic_update_normalizes(self):
        from cogant.simulate.free_energy import bayesian_belief_update

        prior = [0.5, 0.5]
        likelihood = [[0.9, 0.1], [0.1, 0.9]]
        result = bayesian_belief_update(prior, likelihood, 0)
        assert len(result) == 2
        assert abs(sum(result) - 1.0) < 1e-9
        # State 0 should have higher posterior given obs 0
        assert result[0] > result[1]

    def test_out_of_range_obs_raises(self):
        from cogant.simulate.free_energy import bayesian_belief_update

        with pytest.raises(ValueError, match="observation index"):
            bayesian_belief_update([0.5, 0.5], [[0.9, 0.1], [0.1, 0.9]], 5)

    def test_zero_likelihood_rejects_invalid_input(self):
        from cogant.simulate.free_energy import bayesian_belief_update

        with pytest.raises(ValueError, match="zero evidence"):
            bayesian_belief_update([0.5, 0.5], [[0.0, 0.0], [1.0, 1.0]], 0)


class TestExpectedFreeEnergy:
    def test_empty_beliefs_rejects_invalid_input(self):
        from cogant.simulate.free_energy import expected_free_energy

        with pytest.raises(ValueError, match="nonempty"):
            expected_free_energy([0], [], [[1.0]], [[[1.0]]], [0.0])

    def test_empty_policy_rejects_invalid_input(self):
        from cogant.simulate.free_energy import expected_free_energy

        with pytest.raises(ValueError, match="policy"):
            expected_free_energy(
                [], [0.5, 0.5], [[1.0, 1.0]], [[[1.0], [0.0]], [[0.0], [1.0]]], [0.0]
            )

    def test_log_prefs_mismatch_raises(self):
        from cogant.simulate.free_energy import expected_free_energy

        with pytest.raises(ValueError, match="preferences"):
            expected_free_energy(
                [0], [0.5, 0.5], [[1.0, 1.0]], [[[1.0], [0.0]], [[0.0], [1.0]]], [0.1, 0.2]
            )


class TestUniformDistribution:
    def test_uniform_dist_sum(self):
        from cogant.simulate.free_energy import uniform_distribution

        result = uniform_distribution(4)
        assert len(result) == 4
        assert abs(sum(result) - 1.0) < 1e-9
        assert all(abs(p - 0.25) < 1e-9 for p in result)

    def test_uniform_dist_zero_or_negative(self):
        from cogant.simulate.free_energy import uniform_distribution

        for dimension in (0, -1):
            with pytest.raises(ValueError, match="positive"):
                uniform_distribution(dimension)


# ---------------------------------------------------------------------------
# simulate/distributions.py — CategoricalDistribution
# ---------------------------------------------------------------------------


class TestCategoricalDistribution:
    def test_init_uniform(self):
        from cogant.simulate.distributions import CategoricalDistribution

        dist = CategoricalDistribution(["a", "b", "c"])
        assert len(dist.categories) == 3
        assert abs(sum(dist.probabilities) - 1.0) < 1e-9
        assert all(abs(p - 1 / 3) < 1e-9 for p in dist.probabilities)

    def test_init_with_probs(self):
        from cogant.simulate.distributions import CategoricalDistribution

        dist = CategoricalDistribution(["a", "b"], [0.7, 0.3])
        assert abs(dist.probabilities[0] - 0.7) < 1e-9

    def test_sample_returns_category(self):
        from cogant.simulate.distributions import CategoricalDistribution

        dist = CategoricalDistribution(["x", "y", "z"])
        sample = dist.sample()
        assert sample in ["x", "y", "z"]

    def test_log_prob_known_category(self):
        from cogant.simulate.distributions import CategoricalDistribution

        dist = CategoricalDistribution(["a", "b"], [0.8, 0.2])
        lp = dist.log_prob("a")
        assert abs(lp - math.log(0.8)) < 1e-9

    def test_log_prob_unknown_category_raises(self):
        from cogant.simulate.distributions import CategoricalDistribution

        dist = CategoricalDistribution(["a", "b"])
        with pytest.raises(KeyError):
            dist.log_prob("z")

    def test_entropy_uniform(self):
        from cogant.simulate.distributions import CategoricalDistribution

        dist = CategoricalDistribution(["a", "b"])
        entropy = dist.entropy()
        assert abs(entropy - math.log(2)) < 1e-9

    def test_entropy_deterministic(self):
        from cogant.simulate.distributions import CategoricalDistribution

        dist = CategoricalDistribution(["a", "b"], [1.0, 0.0])
        entropy = dist.entropy()
        assert entropy == 0.0

    def test_kl_divergence_same_dist(self):
        from cogant.simulate.distributions import CategoricalDistribution

        dist = CategoricalDistribution(["a", "b"])
        kl = dist.kl_divergence(dist)
        assert abs(kl) < 1e-9

    def test_update_bayesian(self):
        from cogant.simulate.distributions import CategoricalDistribution

        prior = CategoricalDistribution(["a", "b"], [0.5, 0.5])
        # Likelihood: P(observation="a" | category) for each category
        likelihood = CategoricalDistribution(["a", "b"], [0.9, 0.1])
        updated = prior.update("a", likelihood)
        # After update with high likelihood for "a", p(a) should be higher
        assert updated.probabilities[0] > 0.5


# ---------------------------------------------------------------------------
# simulate/distributions.py — TransitionMatrix
# ---------------------------------------------------------------------------


class TestTransitionMatrix:
    def test_init(self):
        from cogant.simulate.distributions import TransitionMatrix

        tm = TransitionMatrix(states=["s0", "s1"], actions=["a0", "a1"])
        assert tm is not None

    def test_set_and_get_transition(self):
        from cogant.simulate.distributions import TransitionMatrix

        tm = TransitionMatrix(states=["s0", "s1"], actions=["a0"])
        tm.set_transition(state="s0", action="a0", next_state="s1", prob=0.8)
        dist = tm.get_next_state_dist("s0", "a0")
        probs = dist.probabilities
        assert abs(sum(probs) - 1.0) < 1e-9
        # s1 should have higher probability (0.8)
        assert probs[dist.categories.index("s1")] > probs[dist.categories.index("s0")]
