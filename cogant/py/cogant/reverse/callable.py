"""Parsed GNN matrix operations using the shared categorical numerical kernel."""

from __future__ import annotations

from cogant.reverse.matrices import _validate_matrix_semantics
from cogant.reverse.parser import ReverseGNNModel, parse_gnn
from cogant.runtime.categorical import CategoricalModel


class MatrixFunctions:
    """Copied source matrices with categorical filtering and policy operations."""

    def __init__(self, model: ReverseGNNModel) -> None:
        _validate_matrix_semantics(model)
        n_states = model.n_states
        n_obs = model.n_obs
        n_actions = model.n_actions

        A = [list(row) for row in model.A]
        B = [[list(cell) for cell in row] for row in model.B]
        C = list(model.C)
        D = list(model.D)

        self._A = A
        self._B = B
        self._C = C
        self._D = D
        self._n_states = n_states
        self._n_obs = n_obs
        self._n_actions = n_actions

        self.A = A
        self.B = B
        self.C = C
        self.D = D

    def _categorical(self) -> CategoricalModel:
        return CategoricalModel(self.A, self.B, self.C, self.D)

    def likelihood(self, state_dist: list[float]) -> list[float]:
        return self._categorical().observe(state_dist)

    def transition(self, state_dist: list[float], action: int = 0) -> list[float]:
        return self._categorical().predict(state_dist, action)

    def preference_score(self, obs_dist: list[float]) -> float:
        return self._categorical().preference_score(obs_dist)

    def prior(self) -> list[float]:
        """Return D vector (initial state prior)."""
        return list(self._D)

    def expected_free_energy(self, state_dist: list[float], action: int) -> float:
        """Evaluate one-step outcome risk plus expected likelihood ambiguity."""
        return self._categorical().score(state_dist, [action])

    def score_preference_gradient(self, state_dist: list[float], policy: list[int]) -> list[float]:
        """Return fixed-policy score sensitivity along the C observation axis."""
        return self._categorical().score_preference_gradient(state_dist, policy)

    def best_action(self, state_dist: list[float]) -> int:
        """Return argmin EFE over the declared action axis."""
        if self._n_actions == 0:
            raise ValueError("policy selection requires at least one action")
        best_a = 0
        best_efe = float("inf")
        for a in range(self._n_actions):
            efe = self.expected_free_energy(state_dist, a)
            if efe < best_efe:
                best_efe = efe
                best_a = a
        return best_a

    @classmethod
    def from_gnn_text(cls, gnn_text: str) -> MatrixFunctions:
        model = parse_gnn(gnn_text)
        return cls(model)


def make_matrix_functions(model: ReverseGNNModel) -> MatrixFunctions:
    return MatrixFunctions(model)


__all__ = ["MatrixFunctions", "make_matrix_functions"]
