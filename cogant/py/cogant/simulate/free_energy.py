"""
Free energy calculations for Active Inference.

Implements variational free energy, expected free energy, and related quantities.
"""

import math
from typing import Dict, List, Optional, Any
from collections import defaultdict

from cogant.statespace.compiler import StateSpaceModel
from cogant.simulate.distributions import CategoricalDistribution, TransitionMatrix


class FreeEnergyCalculator:
    """Compute free energy quantities for Active Inference."""

    def __init__(self, state_space: StateSpaceModel):
        """
        Initialize the calculator.

        Args:
            state_space: The compiled state space model.
        """
        self.state_space = state_space
        self.states = list(state_space.variables.keys())
        self.actions = list(state_space.actions.keys())
        self.transition_matrix = TransitionMatrix.from_state_space(state_space)

    def variational_free_energy(
        self,
        beliefs: CategoricalDistribution,
        observation: str,
        likelihood_model: Optional[Dict[str, CategoricalDistribution]] = None,
    ) -> float:
        """
        Compute variational free energy.

        VFE = KL(Q(s) || P(s)) - E_Q[log P(o|s)]
            = complexity - accuracy

        Where:
        - Q(s) = beliefs (variational distribution)
        - P(s) = prior (uniform for simplicity)
        - P(o|s) = likelihood of observation given state
        - Complexity = KL divergence (how different beliefs are from prior)
        - Accuracy = expected log likelihood (how well beliefs predict observation)

        Minimizing VFE drives both:
        1. Model evidence maximization (fit observation better)
        2. Parsimony (keep beliefs close to prior)

        Args:
            beliefs: Prior beliefs over states Q(s).
            observation: Observed value o.
            likelihood_model: Optional P(o|s) for each state.

        Returns:
            Variational free energy (in nats). Lower is better.
        """
        # Accuracy term: E_Q[log P(o|s)]
        # This is the expected log likelihood of the observation
        accuracy = self._accuracy(observation, beliefs, likelihood_model)

        # Complexity term: KL(Q(s) || P(s))
        # How far the beliefs are from the prior (regularization term)
        # For simplicity, use uniform prior P(s)
        uniform_prior = CategoricalDistribution(beliefs.categories)
        complexity = beliefs.kl_divergence(uniform_prior)

        # VFE = complexity - accuracy
        # When accuracy is large (good prediction), VFE is smaller
        # When complexity is large (beliefs far from prior), VFE is larger
        vfe = complexity - accuracy
        return vfe

    def expected_free_energy(
        self,
        beliefs: CategoricalDistribution,
        policy: List[str],
        horizon: int = 3,
        likelihood_model: Optional[Dict[str, CategoricalDistribution]] = None,
    ) -> float:
        """
        Compute expected free energy for a policy.

        EFE = sum over horizon of [KL(Q_future || P_future) - E_Q[log P(o|s)]]
            = sum of (complexity - accuracy) for each step in the policy

        Lower EFE is better, indicating a policy that:
        1. Reduces uncertainty (low complexity term)
        2. Makes good predictions (high accuracy term)

        Args:
            beliefs: Current beliefs over states.
            policy: Sequence of actions to evaluate.
            horizon: Planning horizon (default 3).
            likelihood_model: Optional likelihood model.

        Returns:
            Expected free energy of the policy (lower is better).
        """
        if not policy:
            return float("inf")

        efe = 0.0
        current_beliefs = beliefs

        for step, action in enumerate(policy[:horizon]):
            if action not in self.actions:
                return float("inf")

            # Expected next state distribution after taking action
            expected_next_beliefs = self._predict_beliefs(current_beliefs, action)

            # Generate expected observation (most likely under current beliefs)
            expected_obs = max(current_beliefs.dist.items(), key=lambda x: x[1])[0]

            # Compute VFE for this step
            # VFE = complexity - accuracy
            # where complexity = KL(Q||P_prior) and accuracy = E_Q[log P(o|s)]
            step_vfe = self.variational_free_energy(
                expected_next_beliefs, expected_obs, likelihood_model
            )
            efe += step_vfe

            # Move to next step
            current_beliefs = expected_next_beliefs

        # Return average over horizon
        return efe / len(policy[:horizon]) if policy else float("inf")

    def surprisal(
        self,
        observation: str,
        beliefs: CategoricalDistribution,
        likelihood_model: Optional[Dict[str, CategoricalDistribution]] = None,
    ) -> float:
        """
        Compute surprisal (negative log likelihood) of observation.

        Surprisal = -log P(o) = -log E_Q[P(o|s)]

        Args:
            observation: Observed value.
            beliefs: Current beliefs over states.
            likelihood_model: Optional likelihood model.

        Returns:
            Surprisal in nats.
        """
        accuracy = self._accuracy(observation, beliefs, likelihood_model)
        return -accuracy

    def complexity(
        self,
        posterior: CategoricalDistribution,
        prior: Optional[CategoricalDistribution] = None,
    ) -> float:
        """
        Compute complexity (KL divergence).

        Complexity = KL(Q(s) || P(s))

        Args:
            posterior: Q(s), posterior beliefs.
            prior: P(s), prior distribution. If None, uses uniform.

        Returns:
            KL divergence in nats.
        """
        if prior is None:
            prior = CategoricalDistribution(posterior.categories)
        return posterior.kl_divergence(prior)

    def accuracy(
        self,
        observation: str,
        beliefs: CategoricalDistribution,
        likelihood_model: Optional[Dict[str, CategoricalDistribution]] = None,
    ) -> float:
        """
        Compute accuracy (expected log likelihood).

        Accuracy = E_Q[log P(o|s)]

        Args:
            observation: Observed value.
            beliefs: Current beliefs over states.
            likelihood_model: Optional likelihood model.

        Returns:
            Accuracy (expected log likelihood) in nats.
        """
        return self._accuracy(observation, beliefs, likelihood_model)

    def _accuracy(
        self,
        observation: str,
        beliefs: CategoricalDistribution,
        likelihood_model: Optional[Dict[str, CategoricalDistribution]] = None,
    ) -> float:
        """Internal accuracy computation.

        If no explicit likelihood model is provided, assumes:
        - P(o|s) = 0.9 if o == s (high likelihood when observation matches state)
        - P(o|s) = 0.1 / (n-1) otherwise (low likelihood for mismatches)

        Args:
            observation: Observed value.
            beliefs: Current beliefs.
            likelihood_model: Optional explicit likelihood model.

        Returns:
            Expected log likelihood.
        """
        accuracy = 0.0

        if likelihood_model and observation in likelihood_model:
            # Use explicit likelihood model
            likelihood_dist = likelihood_model[observation]
            for state in beliefs.categories:
                belief_prob = beliefs.dist[state]
                likelihood_prob = likelihood_dist.dist.get(state, 1e-10)
                if likelihood_prob > 0:
                    accuracy += belief_prob * math.log(likelihood_prob)
        else:
            # Use default likelihood model
            n = len(beliefs.categories)
            for state in beliefs.categories:
                belief_prob = beliefs.dist[state]
                # P(obs | state) is high if obs == state
                if observation == state:
                    likelihood_prob = 0.9
                else:
                    likelihood_prob = 0.1 / max(1, n - 1)

                if likelihood_prob > 0:
                    accuracy += belief_prob * math.log(likelihood_prob)

        return accuracy

    def _predict_beliefs(
        self, beliefs: CategoricalDistribution, action: str
    ) -> CategoricalDistribution:
        """Predict next belief state after action.

        Args:
            beliefs: Current beliefs.
            action: Action to take.

        Returns:
            Next beliefs distribution.
        """
        if action not in self.actions:
            return beliefs

        # Compute expected next state distribution
        next_state_probs = [0.0] * len(self.states)

        for i, state in enumerate(self.states):
            belief_s = beliefs.dist[state]
            next_dist = self.transition_matrix.get_next_state_dist(state, action)

            for j, next_state in enumerate(self.states):
                next_state_probs[j] += belief_s * next_dist.probabilities[j]

        return CategoricalDistribution(self.states, next_state_probs)

    def policy_ranking(
        self,
        beliefs: CategoricalDistribution,
        available_actions: List[str],
        horizon: int = 3,
        likelihood_model: Optional[Dict[str, CategoricalDistribution]] = None,
    ) -> List[tuple]:
        """
        Rank policies by expected free energy.

        Args:
            beliefs: Current beliefs.
            available_actions: List of available actions.
            horizon: Planning horizon.
            likelihood_model: Optional likelihood model.

        Returns:
            List of (action, EFE_score) tuples, sorted by score (lowest is best).
        """
        rankings = []

        for action in available_actions:
            policy = [action]
            efe = self.expected_free_energy(
                beliefs, policy, horizon, likelihood_model
            )
            rankings.append((action, efe))

        # Sort by EFE (ascending: lower is better)
        return sorted(rankings, key=lambda x: x[1])
