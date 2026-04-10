"""Runtime-callable Active Inference matrix functions from a parsed GNN.

Unlike :func:`cogant.reverse.matrices.render_matrices_module` (which
generates Python source code for embedding in a synthesized package),
this module provides Python closures that operate directly on in-memory
matrices from a :class:`ReverseGNNModel`. No ``exec()``, no code
generation — just plain function calls.

The algorithms are **numerically identical** to those emitted by
``render_matrices_module``: the same forward equation for likelihood,
the same normalize-after-multiply for transition, the same dot product
for preference scoring. This ensures that any code path using
``MatrixFunctions`` produces the same results as the generated module.

Typical usage::

    from cogant.reverse.parser import parse_gnn
    from cogant.reverse.callable import MatrixFunctions

    mf = MatrixFunctions.from_gnn_text(open("model.gnn.md").read())
    obs = mf.likelihood([0.5, 0.3, 0.2])
    action = mf.best_action([0.5, 0.3, 0.2])
"""

from __future__ import annotations

from typing import List

from cogant.reverse.parser import ReverseGNNModel, parse_gnn


class MatrixFunctions:
    """Runtime-callable Active Inference matrix functions from a parsed GNN.

    Unlike render_matrices_module (which generates Python source),
    these are Python closures that can be called directly without exec().
    """

    def __init__(self, model: ReverseGNNModel) -> None:
        n_states = model.n_states
        n_obs = model.n_obs
        n_actions = model.n_actions

        # Resolve matrices with the same fallback logic as render_matrices_module.
        A = model.A if model.A else []
        if not A and n_obs and n_states:
            A = [[1.0 / n_states] * n_states for _ in range(n_obs)]

        B = model.B if model.B else []
        if not B and n_states:
            B = [
                [
                    [1.0 if (r == c) else 0.0 for _ in range(max(n_actions, 1))]
                    for c in range(n_states)
                ]
                for r in range(n_states)
            ]

        C = model.C if model.C else [0.0] * n_obs
        D = model.D if model.D else (
            [1.0 / n_states] * n_states if n_states else []
        )

        self._A = A
        self._B = B
        self._C = C
        self._D = D
        self._n_states = n_states
        self._n_obs = n_obs
        self._n_actions = n_actions

    def likelihood(self, state_dist: List[float]) -> List[float]:
        """Return P(observation) given a hidden-state distribution.

        Implements ``P(o) = A . state_dist`` — identical to the generated
        ``likelihood()`` function in ``render_matrices_module``.
        """
        A = self._A
        if not A or not state_dist:
            return []
        n_obs = len(A)
        n_states = len(state_dist)
        result = [0.0] * n_obs
        for i in range(n_obs):
            row = A[i] if i < len(A) else []
            for j in range(min(len(row), n_states)):
                result[i] += row[j] * state_dist[j]
        return result

    def transition(self, state_dist: List[float], action: int = 0) -> List[float]:
        """Return P(next hidden_state) given current distribution and action.

        Implements ``P(s') = B[:,:,action] . state_dist``, normalized —
        identical to the generated ``transition()`` function.
        """
        B = self._B
        if not B or not state_dist:
            return list(state_dist)
        n_states = len(state_dist)
        n_actions = len(B[0][0]) if (B and B[0]) else 1
        k = max(0, min(action, n_actions - 1))
        result = [0.0] * n_states
        for i in range(n_states):
            row = B[i] if i < len(B) else []
            for j in range(min(len(row), n_states)):
                slice_k = row[j][k] if k < len(row[j]) else 0.0
                result[i] += slice_k * state_dist[j]
        # Normalize to keep result a proper distribution.
        total = sum(result)
        if total > 0.0:
            result = [v / total for v in result]
        return result

    def preference_score(self, obs_dist: List[float]) -> float:
        """Return log-preference score <C, obs_dist> for policy selection."""
        C = self._C
        if not C or not obs_dist:
            return 0.0
        score = 0.0
        for i in range(min(len(C), len(obs_dist))):
            score += C[i] * obs_dist[i]
        return score

    def prior(self) -> List[float]:
        """Return D vector (initial state prior)."""
        return list(self._D)

    def expected_free_energy(
        self, state_dist: List[float], action: int
    ) -> float:
        """Simplified EFE: -preference_score(likelihood(transition(s, a))).

        Returns ``float("inf")`` for invalid or empty distributions.
        """
        if not state_dist:
            return float("inf")
        next_state = self.transition(state_dist, action)
        obs = self.likelihood(next_state)
        if not obs:
            return float("inf")
        return -self.preference_score(obs)

    def best_action(self, state_dist: List[float]) -> int:
        """Return argmin EFE over all actions (0 if n_actions == 0)."""
        if self._n_actions == 0:
            return 0
        best_a = 0
        best_efe = float("inf")
        for a in range(self._n_actions):
            efe = self.expected_free_energy(state_dist, a)
            if efe < best_efe:
                best_efe = efe
                best_a = a
        return best_a

    @classmethod
    def from_gnn_text(cls, gnn_text: str) -> "MatrixFunctions":
        """Convenience: parse GNN markdown and return MatrixFunctions."""
        model = parse_gnn(gnn_text)
        return cls(model)


def make_matrix_functions(model: ReverseGNNModel) -> MatrixFunctions:
    """Convenience wrapper -- equivalent to MatrixFunctions(model)."""
    return MatrixFunctions(model)


__all__ = ["MatrixFunctions", "make_matrix_functions"]
