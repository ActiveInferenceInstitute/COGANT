"""
Free energy calculations for Active Inference.

This module provides two layers:

1. **Principled, matrix-based functions** (``variational_free_energy``,
   ``expected_free_energy``, ``bayesian_belief_update``) that operate directly
   on POMDP matrices ``A`` (likelihood), ``B`` (transition), ``C`` (log
   preferences) and ``D`` (prior). These are the canonical implementations
   used by ``cogant.simulate.runner.ModelRunner`` when the caller provides
   explicit generative-model matrices.

2. **FreeEnergyCalculator** — a convenience class that wraps a
   ``StateSpaceModel`` and exposes VFE / EFE methods on top of the
   ``CategoricalDistribution`` abstraction. Preserved for backward
   compatibility with existing call sites that don't have A/B/C/D matrices.

The principled implementations follow:

    VFE  = KL[Q(s) || P(s)] - E_Q[log P(o|s)]
    EFE  = sum_tau [ epistemic_value(tau) - pragmatic_value(tau) ]
         where epistemic = H[P(o|pi, tau)] (entropy of predicted observations)
               pragmatic = C . P(o|pi, tau) (expected log preference)

Lower VFE/EFE is better.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from cogant.simulate.distributions import CategoricalDistribution, TransitionMatrix
from cogant.statespace.compiler import StateSpaceModel

# Numerical floor to avoid log(0).
_EPSILON = 1e-12


# =========================================================================
# Principled matrix-based API (primary interface used by ModelRunner)
# =========================================================================


def _safe_log(x: float) -> float:
    """Log with a small floor to avoid -inf."""
    return math.log(max(x, _EPSILON))


def variational_free_energy(
    beliefs: Sequence[float],
    prior: Sequence[float],
    likelihood_matrix: Sequence[Sequence[float]],
    observation: Sequence[float] | None = None,
) -> float:
    """Compute variational free energy F = KL[Q||P] - E_Q[log P(o|s)].

    This is the principled, matrix-based VFE used by Active Inference
    agents. Lower VFE = better model fit.

    Args:
        beliefs: Current posterior Q(s) over hidden states. Must be a valid
            probability distribution (non-negative, sums to ~1).
        prior: Prior P(s) (the D vector). Same shape as ``beliefs``.
        likelihood_matrix: A matrix where ``A[o][s] = P(observation o |
            state s)``. Shape is ``[n_obs, n_states]``.
        observation: Current observation distribution. If ``None``, a
            uniform distribution over observations is assumed (maximum
            uncertainty about the observation).

    Returns:
        Variational free energy (nats). Lower is better.
    """
    n_states = len(beliefs)
    if n_states == 0:
        return 0.0

    if len(prior) != n_states:
        raise ValueError(f"prior length {len(prior)} does not match beliefs length {n_states}")

    n_obs = len(likelihood_matrix)
    if n_obs == 0:
        # No observation model — VFE reduces to KL term only.
        kl = 0.0
        for s in range(n_states):
            q = beliefs[s]
            p = prior[s]
            if q > 0:
                kl += q * (_safe_log(q) - _safe_log(p))
        return kl

    for row in likelihood_matrix:
        if len(row) != n_states:
            raise ValueError("likelihood_matrix rows must have n_states entries")

    if observation is None:
        observation = [1.0 / n_obs] * n_obs
    elif len(observation) != n_obs:
        raise ValueError(f"observation length {len(observation)} does not match n_obs {n_obs}")

    # KL[Q || P]: complexity.
    kl = 0.0
    for s in range(n_states):
        q = beliefs[s]
        p = prior[s]
        if q > 0:
            kl += q * (_safe_log(q) - _safe_log(p))

    # E_Q[log P(o|s)]: expected log likelihood under current belief,
    # marginalised over the observation distribution.
    expected_log_lik = 0.0
    for s in range(n_states):
        q = beliefs[s]
        if q <= 0:
            continue
        inner = 0.0
        for o in range(n_obs):
            inner += observation[o] * _safe_log(likelihood_matrix[o][s])
        expected_log_lik += q * inner

    return kl - expected_log_lik


def bayesian_belief_update(
    prior: Sequence[float],
    likelihood_matrix: Sequence[Sequence[float]],
    observation_index: int,
) -> list[float]:
    """Exact Bayesian posterior under a categorical observation.

    Discrete update: posterior proportional to likelihood times prior (see source).

    Args:
        prior: Prior over state indices (categorical).
        likelihood_matrix: Rows are observations, columns states (see implementation).
        observation_index: The index of the observed outcome.

    Returns:
        Posterior distribution over states.
    """
    n_states = len(prior)
    if n_states == 0:
        return []
    if not (0 <= observation_index < len(likelihood_matrix)):
        raise IndexError(f"observation_index {observation_index} out of range")

    row = likelihood_matrix[observation_index]
    unnorm = [row[s] * prior[s] for s in range(n_states)]
    total = sum(unnorm)
    if total <= 0:
        # Fall back to the prior when the observation has zero likelihood.
        return [float(p) for p in prior]
    return [u / total for u in unnorm]


def expected_free_energy(
    policy_action_sequence: Sequence[int],
    beliefs: Sequence[float],
    likelihood_matrix: Sequence[Sequence[float]],
    transition_tensor: Sequence[Sequence[Sequence[float]]],
    log_preferences: Sequence[float],
) -> float:
    """Compute expected free energy for a policy over a planning horizon.

        EFE(π) = sum_τ [ epistemic_value(τ) - pragmatic_value(τ) ]

    where:
      * ``epistemic_value`` is the entropy of the predicted observation
        distribution H[P(o | π, τ)] — rewards exploration / uncertainty
        reduction.
      * ``pragmatic_value`` is C · P(o | π, τ) — rewards reaching preferred
        outcomes (C is the log-preference vector).

    Lower EFE = preferred policy.

    Args:
        policy_action_sequence: Sequence of action indices to evaluate.
        beliefs: Current belief vector over discrete states.
        likelihood_matrix: Observation-by-state likelihood table (rows: observations).
        transition_tensor: Transition dynamics (next state, current state, action).
        log_preferences: Per-observation log-preference vector.

    Returns:
        Expected free energy (nats). Lower is better.
    """
    n_states = len(beliefs)
    if n_states == 0:
        return 0.0

    n_obs = len(likelihood_matrix)
    if n_obs == 0 or not policy_action_sequence:
        return 0.0

    if len(log_preferences) != n_obs:
        raise ValueError(f"log_preferences length {len(log_preferences)} != n_obs {n_obs}")

    current = list(beliefs)
    total_efe = 0.0

    for action_idx in policy_action_sequence:
        # Predict next state distribution under this action:
        #   s'_dist[s'] = sum_s B[s'][s][a] * current[s]
        next_beliefs = [0.0] * n_states
        for s_next in range(n_states):
            acc = 0.0
            row = transition_tensor[s_next]
            for s in range(n_states):
                acc += row[s][action_idx] * current[s]
            next_beliefs[s_next] = acc

        # Predicted observation distribution:
        #   pred_obs[o] = sum_s A[o][s] * next_beliefs[s]
        pred_obs = [0.0] * n_obs
        for o in range(n_obs):
            acc = 0.0
            a_row = likelihood_matrix[o]
            for s in range(n_states):
                acc += a_row[s] * next_beliefs[s]
            pred_obs[o] = acc

        # Epistemic value: entropy of predicted observations.
        epistemic = 0.0
        for o in range(n_obs):
            p = pred_obs[o]
            if p > 0:
                epistemic -= p * _safe_log(p)

        # Pragmatic value: expected log preference.
        pragmatic = 0.0
        for o in range(n_obs):
            pragmatic += log_preferences[o] * pred_obs[o]

        total_efe += epistemic - pragmatic
        current = next_beliefs

    return total_efe


def uniform_distribution(n: int) -> list[float]:
    """Return a uniform distribution of length ``n``."""
    if n <= 0:
        return []
    return [1.0 / n] * n


# =========================================================================
# Class-based convenience wrapper (back-compat with existing callers)
# =========================================================================


class FreeEnergyCalculator:
    """Compute free energy quantities for Active Inference.

    Thin convenience wrapper over a ``StateSpaceModel`` that exposes
    distribution-based VFE / EFE. For new code, prefer the principled
    matrix-based functions ``variational_free_energy`` and
    ``expected_free_energy`` defined at module scope.
    """

    def __init__(self, state_space: StateSpaceModel):
        """Initialize the calculator.

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
        likelihood_model: dict[str, CategoricalDistribution] | None = None,
    ) -> float:
        """Compute variational free energy VFE = complexity - accuracy.

        Args:
            beliefs: Q(s), variational posterior over states.
            observation: Observed value.
            likelihood_model: Optional explicit P(o|s).

        Returns:
            VFE in nats. Lower is better.
        """
        accuracy = self._accuracy(observation, beliefs, likelihood_model)
        uniform_prior = CategoricalDistribution(beliefs.categories)
        complexity = beliefs.kl_divergence(uniform_prior)
        return complexity - accuracy

    def expected_free_energy(
        self,
        beliefs: CategoricalDistribution,
        policy: list[str],
        horizon: int = 3,
        likelihood_model: dict[str, CategoricalDistribution] | None = None,
    ) -> float:
        """Compute expected free energy for a policy (averaged over horizon)."""
        if not policy:
            return float("inf")

        efe = 0.0
        current_beliefs = beliefs

        for action in policy[:horizon]:
            if action not in self.actions:
                return float("inf")

            expected_next_beliefs = self._predict_beliefs(current_beliefs, action)
            expected_obs = max(current_beliefs.dist.items(), key=lambda x: x[1])[0]

            step_vfe = self.variational_free_energy(
                expected_next_beliefs, expected_obs, likelihood_model
            )
            efe += step_vfe
            current_beliefs = expected_next_beliefs

        return efe / len(policy[:horizon]) if policy else float("inf")

    def surprisal(
        self,
        observation: str,
        beliefs: CategoricalDistribution,
        likelihood_model: dict[str, CategoricalDistribution] | None = None,
    ) -> float:
        """Surprisal = -log P(o) ≈ -E_Q[log P(o|s)]."""
        return -self._accuracy(observation, beliefs, likelihood_model)

    def complexity(
        self,
        posterior: CategoricalDistribution,
        prior: CategoricalDistribution | None = None,
    ) -> float:
        """Complexity = KL(Q||P). Prior defaults to uniform."""
        if prior is None:
            prior = CategoricalDistribution(posterior.categories)
        return posterior.kl_divergence(prior)

    def accuracy(
        self,
        observation: str,
        beliefs: CategoricalDistribution,
        likelihood_model: dict[str, CategoricalDistribution] | None = None,
    ) -> float:
        """Accuracy = E_Q[log P(o|s)]."""
        return self._accuracy(observation, beliefs, likelihood_model)

    def _accuracy(
        self,
        observation: str,
        beliefs: CategoricalDistribution,
        likelihood_model: dict[str, CategoricalDistribution] | None = None,
    ) -> float:
        """Internal accuracy computation.

        If no explicit likelihood is provided, falls back to a default
        model where ``P(o|s) = 0.9`` when ``o == s`` and low otherwise.
        """
        accuracy = 0.0

        if likelihood_model and observation in likelihood_model:
            likelihood_dist = likelihood_model[observation]
            for state in beliefs.categories:
                belief_prob = beliefs.dist[state]
                likelihood_prob = likelihood_dist.dist.get(state, _EPSILON)
                if likelihood_prob > 0:
                    accuracy += belief_prob * math.log(likelihood_prob)
        else:
            n = len(beliefs.categories)
            for state in beliefs.categories:
                belief_prob = beliefs.dist[state]
                likelihood_prob = 0.9 if observation == state else 0.1 / max(1, n - 1)
                if likelihood_prob > 0:
                    accuracy += belief_prob * math.log(likelihood_prob)

        return accuracy

    def _predict_beliefs(
        self, beliefs: CategoricalDistribution, action: str
    ) -> CategoricalDistribution:
        """Predict next beliefs after taking an action."""
        if action not in self.actions:
            return beliefs

        next_state_probs = [0.0] * len(self.states)
        for _i, state in enumerate(self.states):
            belief_s = beliefs.dist[state]
            next_dist = self.transition_matrix.get_next_state_dist(state, action)
            for j in range(len(self.states)):
                next_state_probs[j] += belief_s * next_dist.probabilities[j]

        return CategoricalDistribution(self.states, next_state_probs)

    def policy_ranking(
        self,
        beliefs: CategoricalDistribution,
        available_actions: list[str],
        horizon: int = 3,
        likelihood_model: dict[str, CategoricalDistribution] | None = None,
    ) -> list[tuple[str, float]]:
        """Rank policies by expected free energy (ascending — lower is better)."""
        rankings = []
        for action in available_actions:
            efe = self.expected_free_energy(beliefs, [action], horizon, likelihood_model)
            rankings.append((action, efe))
        return sorted(rankings, key=lambda x: x[1])


__all__ = [
    "variational_free_energy",
    "expected_free_energy",
    "bayesian_belief_update",
    "uniform_distribution",
    "FreeEnergyCalculator",
]
