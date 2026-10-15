"""Categorical free-energy API backed by the shared dependency-free kernel."""

from __future__ import annotations

from collections.abc import Sequence

from cogant.runtime.categorical import CategoricalModel, posterior
from cogant.runtime.categorical import variational_free_energy as categorical_vfe
from cogant.simulate.distributions import CategoricalDistribution
from cogant.statespace.compiler import StateSpaceModel


def variational_free_energy(
    beliefs: Sequence[float],
    prior: Sequence[float],
    likelihood_matrix: Sequence[Sequence[float]],
    observation: Sequence[float] | None = None,
) -> float:
    """Evaluate F against an explicit predicted prior and observation distribution."""
    if observation is None:
        raise ValueError("variational free energy requires an explicit observation distribution")
    return categorical_vfe(beliefs, prior, likelihood_matrix, observation)


def bayesian_belief_update(
    prior: Sequence[float],
    likelihood_matrix: Sequence[Sequence[float]],
    observation_index: int,
) -> list[float]:
    """Condition on an observed index; reject observations with zero evidence."""
    return posterior(prior, likelihood_matrix, observation_index)


def expected_free_energy(
    policy_action_sequence: Sequence[int],
    beliefs: Sequence[float],
    likelihood_matrix: Sequence[Sequence[float]],
    transition_tensor: Sequence[Sequence[Sequence[float]]],
    log_preferences: Sequence[float],
) -> float:
    """Sum risk KL(predicted outcomes || softmax(C)) and expected ambiguity."""
    model = CategoricalModel(likelihood_matrix, transition_tensor, log_preferences, beliefs)
    return model.score(beliefs, policy_action_sequence)


def uniform_distribution(n: int) -> list[float]:
    """Construct an explicitly requested uniform categorical distribution."""
    if n <= 0:
        raise ValueError("distribution dimension must be positive")
    return [1.0 / n] * n


class FreeEnergyCalculator:
    """Calculate from compiled matrices, preserving the state's declared axis order."""

    def __init__(self, state_space: StateSpaceModel, matrices: CategoricalModel | None = None):
        self.state_space = state_space
        self.states = list(state_space.variables)
        self.actions = list(state_space.actions)
        self.observations = list(state_space.observations)
        if matrices is None:
            raise ValueError("FreeEnergyCalculator requires explicit A/B/C/D matrices")
        self.model = matrices

    def _beliefs(self, beliefs: CategoricalDistribution) -> list[float]:
        if set(beliefs.categories) != set(self.states):
            raise ValueError("belief categories must match the model state axis")
        return [beliefs.dist[state] for state in self.states]

    def _likelihood(
        self, likelihood_model: dict[str, CategoricalDistribution] | None
    ) -> Sequence[Sequence[float]]:
        if likelihood_model is None:
            return self.model.A
        if set(likelihood_model) != set(self.observations):
            raise ValueError("likelihood keys must match the observation axis")
        return [self._beliefs(likelihood_model[o]) for o in self.observations]

    def variational_free_energy(
        self,
        beliefs: CategoricalDistribution,
        observation: str,
        likelihood_model: dict[str, CategoricalDistribution] | None = None,
    ) -> float:
        """Evaluate posterior free energy against the model's initial prior D."""
        observation_index = self.observations.index(observation)
        observed = [float(i == observation_index) for i in range(len(self.observations))]
        return categorical_vfe(
            self._beliefs(beliefs), self.model.D, self._likelihood(likelihood_model), observed
        )

    def expected_free_energy(
        self,
        beliefs: CategoricalDistribution,
        policy: list[str],
        horizon: int = 3,
        likelihood_model: dict[str, CategoricalDistribution] | None = None,
    ) -> float:
        """Sum the specified candidate policy up to a positive finite horizon."""
        if horizon <= 0:
            raise ValueError("horizon must be positive")
        model = CategoricalModel(
            self._likelihood(likelihood_model), self.model.B, self.model.C, self.model.D
        )
        return model.score(
            self._beliefs(beliefs), [self.actions.index(a) for a in policy[:horizon]]
        )

    def surprisal(
        self,
        observation: str,
        beliefs: CategoricalDistribution,
        likelihood_model: dict[str, CategoricalDistribution] | None = None,
    ) -> float:
        """Return negative log marginal evidence of the observation."""
        import math

        row = self._likelihood(likelihood_model)[self.observations.index(observation)]
        evidence = sum(p * a for p, a in zip(self._beliefs(beliefs), row, strict=True))
        return -math.log(evidence) if evidence > 0 else math.inf

    def complexity(
        self, posterior: CategoricalDistribution, prior: CategoricalDistribution | None = None
    ) -> float:
        """Return KL(q || prior), using the model D when no prior is supplied."""
        from cogant.runtime.categorical import kl_divergence

        reference = self.model.D if prior is None else self._beliefs(prior)
        return kl_divergence(self._beliefs(posterior), reference)

    def accuracy(
        self,
        observation: str,
        beliefs: CategoricalDistribution,
        likelihood_model: dict[str, CategoricalDistribution] | None = None,
    ) -> float:
        """Return expected log likelihood for the observed outcome."""
        return self.complexity(beliefs) - self.variational_free_energy(
            beliefs, observation, likelihood_model
        )

    def policy_ranking(
        self,
        beliefs: CategoricalDistribution,
        available_actions: list[str],
        horizon: int = 3,
        likelihood_model: dict[str, CategoricalDistribution] | None = None,
    ) -> list[tuple[str, float]]:
        """Rank candidate one-action policies by risk plus ambiguity, stably."""
        return sorted(
            [
                (a, self.expected_free_energy(beliefs, [a], horizon, likelihood_model))
                for a in available_actions
            ],
            key=lambda item: item[1],
        )

    def _predict_beliefs(
        self, beliefs: CategoricalDistribution, action: str
    ) -> CategoricalDistribution:
        predicted = self.model.predict(self._beliefs(beliefs), self.actions.index(action))
        return CategoricalDistribution(self.states, predicted)


__all__ = [
    "variational_free_energy",
    "expected_free_energy",
    "bayesian_belief_update",
    "uniform_distribution",
    "FreeEnergyCalculator",
]
