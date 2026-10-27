"""Dependency-free categorical filtering and risk-plus-ambiguity planning.

Axes are A[observation][state] and B[next_state][state][action]. Zero
probabilities retain their mathematical meaning; impossible conditioning fails.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import NamedTuple

Vector = Sequence[float]
Matrix = Sequence[Vector]
Tensor = Sequence[Matrix]


def distribution(values: Vector, name: str = "distribution") -> None:
    """Require a finite, nonnegative, nonempty probability vector."""
    if not values or any(
        type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in values
    ):
        raise ValueError(f"{name} must be nonempty, finite and non-negative")
    if not math.isclose(math.fsum(values), 1.0, abs_tol=1e-6):
        raise ValueError(f"{name} must sum to 1.0")


def likelihood_matrix(matrix: Matrix, n_states: int) -> None:
    """Require one conditional outcome distribution for every state."""
    if not matrix or any(len(row) != n_states for row in matrix):
        raise ValueError("likelihood A has incompatible dimensions")
    for state in range(n_states):
        distribution([row[state] for row in matrix], "likelihood A column")


def kl_divergence(p: Vector, q: Vector) -> float:
    """Return KL(p || q), including infinity for unsupported positive mass."""
    distribution(p)
    distribution(q)
    if len(p) != len(q):
        raise ValueError("KL distributions have incompatible dimensions")
    if any(pi > 0 and qi == 0 for pi, qi in zip(p, q, strict=True)):
        return math.inf
    return math.fsum(
        pi * (math.log(pi) - math.log(qi)) for pi, qi in zip(p, q, strict=True) if pi > 0
    )


def posterior(prior: Vector, likelihood: Matrix, observation: int) -> list[float]:
    """Condition a predicted prior on one observed categorical outcome."""
    distribution(prior, "prior")
    likelihood_matrix(likelihood, len(prior))
    if type(observation) is not int or not 0 <= observation < len(likelihood):
        raise ValueError("observation index is outside the likelihood axis")
    weighted = [p * a for p, a in zip(prior, likelihood[observation], strict=True)]
    evidence = math.fsum(weighted)
    if evidence <= 0:
        raise ValueError("observation has zero evidence under the predicted prior")
    return [value / evidence for value in weighted]


def variational_free_energy(
    beliefs: Vector, prior: Vector, likelihood: Matrix, observation: Vector
) -> float:
    """Return KL(q || predicted prior) minus expected log likelihood."""
    complexity = kl_divergence(beliefs, prior)
    likelihood_matrix(likelihood, len(beliefs))
    distribution(observation, "observation")
    if len(observation) != len(likelihood):
        raise ValueError("observation distribution has incompatible dimensions")
    terms = []
    for o, weight in enumerate(observation):
        for s, probability in enumerate(beliefs):
            if weight > 0 and probability > 0:
                if likelihood[o][s] == 0:
                    return math.inf
                terms.append(weight * probability * math.log(likelihood[o][s]))
    return complexity - math.fsum(terms)


class CategoricalStep(NamedTuple):
    posterior: list[float]
    prediction: list[float]
    action: int
    policy_scores: list[float]
    free_energy: float
    observation: int


class CategoricalModel:
    """Validated matrix view shared by filtering, simulation and planning."""

    __slots__ = ("_A", "_B", "_C", "_D")

    def __init__(self, A: Matrix, B: Tensor, C: Vector, D: Vector) -> None:
        self._A, self._B, self._C, self._D = A, B, C, D
        distribution(self.D, "prior D")
        n = len(self.D)
        likelihood_matrix(self.A, n)
        if len(self.C) != len(self.A) or any(
            type(c) not in (int, float) or not math.isfinite(c) for c in self.C
        ):
            raise ValueError("log preferences C must be finite and match the observation axis")
        if len(self.B) != n or any(len(row) != n for row in self.B):
            raise ValueError("transition B has incompatible state dimensions")
        actions = len(self.B[0][0])
        if actions == 0 or any(len(cell) != actions for row in self.B for cell in row):
            raise ValueError("transition B requires a consistent nonempty action axis")
        for s in range(n):
            for action in range(actions):
                distribution([self.B[t][s][action] for t in range(n)], "transition B column")

    @property
    def A(self) -> Matrix:
        return self._A

    @property
    def B(self) -> Tensor:
        return self._B

    @property
    def C(self) -> Vector:
        return self._C

    @property
    def D(self) -> Vector:
        return self._D

    @property
    def n_actions(self) -> int:
        """Number of declared control actions."""
        return len(self.B[0][0])

    def observe(self, beliefs: Vector) -> list[float]:
        """Predict the categorical observation marginal A @ q."""
        self._beliefs(beliefs)
        return [math.fsum(a * q for a, q in zip(row, beliefs, strict=True)) for row in self.A]

    def predict(self, beliefs: Vector, action: int) -> list[float]:
        """Predict the next state marginal B[:,:,action] @ q."""
        self._beliefs(beliefs)
        if type(action) is not int or not 0 <= action < self.n_actions:
            raise ValueError("action index is outside the transition axis")
        return [
            math.fsum(cell[action] * q for cell, q in zip(row, beliefs, strict=True))
            for row in self.B
        ]

    def score(self, beliefs: Vector, policy: Sequence[int]) -> float:
        """Sum outcome-risk KL plus expected likelihood ambiguity over a policy."""
        self._beliefs(beliefs)
        if not policy:
            raise ValueError("policy must contain at least one action")
        offset = max(self.C)
        centered = [c - offset for c in self.C]
        log_normalizer = math.log(math.fsum(math.exp(c) for c in centered))
        log_preferences = [c - log_normalizer for c in centered]
        ambiguity = [
            -math.fsum(row[s] * math.log(row[s]) for row in self.A if row[s] > 0)
            for s in range(len(self.D))
        ]
        total = 0.0
        current = list(beliefs)
        for action in policy:
            current = self.predict(current, action)
            outcomes = self.observe(current)
            risk = math.fsum(
                p * (math.log(p) - c)
                for p, c in zip(outcomes, log_preferences, strict=True)
                if p > 0
            )
            total += risk + math.fsum(q * h for q, h in zip(current, ambiguity, strict=True))
        return total

    def action_scores(self, beliefs: Vector) -> list[float]:
        """Evaluate each one-step policy in declared action order."""
        return [self.score(beliefs, [action]) for action in range(self.n_actions)]

    def score_preference_gradient(self, beliefs: Vector, policy: Sequence[int]) -> list[float]:
        """Differentiate the fixed-policy score with respect to log preferences C.

        A, B, incoming beliefs and every action are held fixed. This is an
        analytic derivative of the model objective, not of discrete policy
        selection or source-program execution. No matrices are mutated.
        """
        self._beliefs(beliefs)
        if not policy:
            raise ValueError("policy must contain at least one action")
        offset = max(self.C)
        weights = [math.exp(c - offset) for c in self.C]
        normalizer = math.fsum(weights)
        preferred = [weight / normalizer for weight in weights]
        gradient = [0.0] * len(self.A)
        current = list(beliefs)
        for action in policy:
            current = self.predict(current, action)
            outcomes = self.observe(current)
            mass = math.fsum(outcomes)
            for outcome, probability in enumerate(outcomes):
                gradient[outcome] += mass * preferred[outcome] - probability
        return gradient

    def step(self, prior: Vector, observation: int | None = None) -> CategoricalStep:
        """Filter, score all one-step policies, then predict the selected action."""
        if observation is None:
            outcomes = self.observe(prior)
            observation = max(range(len(outcomes)), key=outcomes.__getitem__)
        updated = posterior(prior, self.A, observation)
        scores = self.action_scores(updated)
        action = min(range(self.n_actions), key=scores.__getitem__)
        observed = [float(i == observation) for i in range(len(self.A))]
        free_energy = variational_free_energy(updated, prior, self.A, observed)
        return CategoricalStep(
            updated, self.predict(updated, action), action, scores, free_energy, observation
        )

    def preference_score(self, outcomes: Vector) -> float:
        """Return expected log preference as a diagnostic, distinct from EFE."""
        distribution(outcomes, "outcomes")
        return math.fsum(c * p for c, p in zip(self.C, outcomes, strict=True))

    def _beliefs(self, beliefs: Vector) -> None:
        distribution(beliefs, "beliefs")
        if len(beliefs) != len(self.D):
            raise ValueError("beliefs have incompatible state dimensions")
