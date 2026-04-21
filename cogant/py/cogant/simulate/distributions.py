"""
Probability distributions for Active Inference simulations.

Provides categorical distributions, transition matrices, and belief updates.
"""

import math
import random
from collections import defaultdict

from cogant.statespace.compiler import StateSpaceModel


class CategoricalDistribution:
    """Categorical probability distribution over discrete states."""

    def __init__(self, categories: list[str], probabilities: list[float] | None = None):
        """
        Initialize a categorical distribution.

        Args:
            categories: List of category names.
            probabilities: Optional list of probabilities (must sum to 1).
                          If None, uses uniform distribution.
        """
        self.categories = categories
        self.n = len(categories)

        # Handle empty categories case
        if self.n == 0:
            self.probabilities = []
            self.dist = {}
            return

        if probabilities is None:
            # Uniform distribution
            self.probabilities = [1.0 / self.n] * self.n
        else:
            if len(probabilities) != self.n:
                raise ValueError("Number of probabilities must match number of categories")
            total = sum(probabilities)
            if total <= 0:
                raise ValueError(f"Probabilities must be positive, got sum {total}")
            # Normalize to ensure exact sum of 1 (handles incomplete distributions)
            self.probabilities = [p / total for p in probabilities]

        # Build category -> probability mapping
        self.dist = dict(zip(categories, self.probabilities, strict=False))

    def sample(self) -> str:
        """Sample a category from the distribution.

        Returns:
            A sampled category name.
        """
        return random.choices(self.categories, weights=self.probabilities, k=1)[0]

    def log_prob(self, category: str) -> float:
        """Get log probability of a category.

        Args:
            category: Category name.

        Returns:
            log(P(category)). Returns -inf if category has 0 probability.
        """
        if category not in self.dist:
            raise KeyError(f"Unknown category: {category}")
        prob = self.dist[category]
        if prob <= 0:
            return float("-inf")
        return math.log(prob)

    def entropy(self) -> float:
        """Compute Shannon entropy of the distribution.

        Returns:
            Entropy in nats.
        """
        h = 0.0
        for prob in self.probabilities:
            if prob > 0:
                h -= prob * math.log(prob)
        return h

    def kl_divergence(self, other: "CategoricalDistribution") -> float:
        """Compute KL divergence to another distribution.

        Args:
            other: Another CategoricalDistribution with same categories.

        Returns:
            KL(self || other) in nats.
        """
        if set(self.categories) != set(other.categories):
            raise ValueError("Distributions must have same categories for KL divergence")

        kl = 0.0
        for cat in self.categories:
            p = self.dist[cat]
            q = other.dist[cat]
            if p > 0:
                if q <= 0:
                    return float("inf")
                kl += p * (math.log(p) - math.log(q))
        return kl

    def update(
        self, observation: str, likelihood: "CategoricalDistribution"
    ) -> "CategoricalDistribution":
        """Bayesian update: posterior ∝ likelihood × prior.

        Args:
            observation: The observed category.
            likelihood: P(observation | category) for each category.

        Returns:
            Updated posterior distribution.
        """
        if observation not in likelihood.categories:
            raise ValueError(f"Observation {observation} not in likelihood categories")

        # Posterior ∝ likelihood(obs|cat) × prior(cat)
        posterior_unnormalized = []
        for cat in self.categories:
            prior_cat = self.dist[cat]
            # P(obs | cat) from likelihood
            likelihood_obs_given_cat = likelihood.dist.get(cat, 1e-10)
            posterior_unnormalized.append(prior_cat * likelihood_obs_given_cat)

        # Normalize
        total = sum(posterior_unnormalized)
        if total <= 0:
            # If no valid posterior, return prior (avoid division by zero)
            return CategoricalDistribution(self.categories, self.probabilities)

        posterior_probs = [p / total for p in posterior_unnormalized]
        return CategoricalDistribution(self.categories, posterior_probs)

    def __repr__(self) -> str:
        """String representation."""
        items = [f"{cat}: {prob:.3f}" for cat, prob in self.dist.items()]
        return f"CategoricalDistribution({', '.join(items)})"


class TransitionMatrix:
    """Transition probabilities between states under actions."""

    def __init__(self, states: list[str], actions: list[str]):
        """
        Initialize a transition matrix.

        Args:
            states: List of state names.
            actions: List of action names.
        """
        self.states = states
        self.actions = actions
        # transitions[action][state] = CategoricalDistribution over next states
        self.transitions: dict[str, dict[str, CategoricalDistribution]] = {
            action: {} for action in actions
        }

    def set_transition(self, state: str, action: str, next_state: str, prob: float) -> None:
        """Set a single transition probability.

        Args:
            state: Current state.
            action: Action taken.
            next_state: Resulting state.
            prob: Probability of transition.
        """
        if state not in self.states:
            raise ValueError(f"Unknown state: {state}")
        if action not in self.actions:
            raise ValueError(f"Unknown action: {action}")
        if next_state not in self.states:
            raise ValueError(f"Unknown next_state: {next_state}")

        if state not in self.transitions[action]:
            # Create new distribution for this state (uniform)
            n = len(self.states)
            self.transitions[action][state] = CategoricalDistribution(self.states, [1.0 / n] * n)

        # Update the distribution
        current_dist = self.transitions[action][state]
        probs = list(current_dist.probabilities)
        idx = self.states.index(next_state)

        # Set the probability for this transition
        # Adjust other probabilities to sum to 1
        probs[idx] = prob
        remaining_prob = 1.0 - prob
        other_indices = [i for i in range(len(self.states)) if i != idx]
        if other_indices:
            other_prob = remaining_prob / len(other_indices)
            for i in other_indices:
                probs[i] = other_prob

        self.transitions[action][state] = CategoricalDistribution(self.states, probs)

    def get_next_state_dist(self, state: str, action: str) -> CategoricalDistribution:
        """Get the distribution over next states.

        Args:
            state: Current state.
            action: Action taken.

        Returns:
            CategoricalDistribution over next states.
        """
        if state not in self.states:
            raise ValueError(f"Unknown state: {state}")
        if action not in self.actions:
            raise ValueError(f"Unknown action: {action}")

        if state not in self.transitions[action]:
            # Default: uniform transition
            return CategoricalDistribution(self.states)

        return self.transitions[action][state]

    @classmethod
    def from_state_space(cls, state_space: StateSpaceModel) -> "TransitionMatrix":
        """Build a transition matrix from a StateSpaceModel.

        Args:
            state_space: The compiled state space model.

        Returns:
            TransitionMatrix with inferred probabilities from transitions.
        """
        states = list(state_space.variables.keys())
        actions = list(state_space.actions.keys())

        matrix = cls(states, actions)

        # Count transitions to estimate probabilities
        transition_counts: dict[tuple[str, str, str], int] = defaultdict(int)

        for trans_id, trans in state_space.transitions.items():
            if trans.action_id:
                # Extract state identifiers from transition source/target
                # For simplicity, use the transition IDs themselves as state proxies
                action_id = trans.action_id
                source = trans_id.split("_")[0] if "_" in trans_id else "s0"
                target = trans_id.split("_")[1] if "_" in trans_id else "s1"

                # Normalize to valid state/action IDs
                if action_id in actions:
                    transition_counts[(source, action_id, target)] += 1

        # Convert counts to probabilities
        action_state_counts: dict[tuple[str, str], int] = defaultdict(int)
        for (source, action, _target), count in transition_counts.items():
            action_state_counts[(action, source)] += count

        for (source, action, target), count in transition_counts.items():
            total = action_state_counts[(action, source)]
            if total > 0:
                prob = count / total
                if source in states and target in states and action in actions:
                    matrix.set_transition(source, action, target, prob)

        return matrix

    def __repr__(self) -> str:
        """String representation."""
        return f"TransitionMatrix({len(self.states)} states, {len(self.actions)} actions)"
