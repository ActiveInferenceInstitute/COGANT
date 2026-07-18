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

from cogant.reverse.matrices import _validate_matrix_semantics
from cogant.reverse.parser import ReverseGNNModel, parse_gnn


class MatrixFunctions:
    """Runtime-callable Active Inference matrix functions from a parsed GNN.

    Unlike render_matrices_module (which generates Python source),
    these are Python closures that can be called directly without exec().

    Example:
        Build a MatrixFunctions instance from a parsed GNN and score an
        observation distribution::

            from cogant.reverse.parser import ReverseGNNModel
            from cogant.reverse.callable import MatrixFunctions

            model = ReverseGNNModel()
            model.hidden_states = ["s_f0", "s_f1"]
            model.observations = ["o_m0", "o_m1"]
            model.actions = ["u_c0"]
            model.A = [[0.9, 0.1], [0.1, 0.9]]
            model.C = [1.0, 0.0]
            mf = MatrixFunctions(model)
            obs = mf.likelihood([0.5, 0.5])
            assert len(obs) == 2
    """

    def __init__(self, model: ReverseGNNModel) -> None:
        _validate_matrix_semantics(model)
        n_states = model.n_states
        n_obs = model.n_obs
        n_actions = model.n_actions

        # Runtime execution uses the source matrices exactly. Missing
        # matrices are evidence gaps, not values to invent.
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

        # Public attributes so AgentRuntime can read raw matrices
        self.A = A
        self.B = B
        self.C = C
        self.D = D

    def likelihood(self, state_dist: list[float]) -> list[float]:
        """Return P(observation) given a hidden-state distribution.

        Implements ``P(o) = A . state_dist`` — identical to the generated
        ``likelihood()`` function in ``render_matrices_module``.
        """
        self._validate_state_distribution(state_dist)
        A = self._A
        if not A:
            return []
        n_obs = len(A)
        n_states = len(state_dist)
        result = [0.0] * n_obs
        for i in range(n_obs):
            row = A[i] if i < len(A) else []
            for j in range(n_states):
                result[i] += row[j] * state_dist[j]
        return result

    def transition(self, state_dist: list[float], action: int = 0) -> list[float]:
        """Return P(next hidden_state) given current distribution and action.

        Implements ``P(s') = B[:,:,action] . state_dist``, normalized —
        identical to the generated ``transition()`` function.
        """
        self._validate_state_distribution(state_dist)
        B = self._B
        if not state_dist:
            return []
        if not B:
            raise ValueError("transition matrix B is unavailable for this model")
        n_states = len(state_dist)
        n_actions = len(B[0][0]) if (B and B[0]) else 1
        if action < 0 or action >= n_actions:
            raise ValueError("action index is outside the declared B dimension")
        k = action
        result = [0.0] * n_states
        for i in range(n_states):
            row = B[i] if i < len(B) else []
            for j in range(n_states):
                slice_k = row[j][k]
                result[i] += slice_k * state_dist[j]
        # Normalize to keep result a proper distribution.
        total = sum(result)
        if total <= 0.0:
            raise ValueError("transition matrix produced no probability mass")
        result = [v / total for v in result]
        return result

    def preference_score(self, obs_dist: list[float]) -> float:
        """Return log-preference score <C, obs_dist> for policy selection."""
        C = self._C
        if len(obs_dist) != self._n_obs:
            raise ValueError("observation distribution has incompatible dimensions")
        if any(value < 0.0 for value in obs_dist) or not all(
            value == value and abs(value) != float("inf") for value in obs_dist
        ):
            raise ValueError("observation distribution must be finite and non-negative")
        if not C:
            return 0.0
        score = 0.0
        for i in range(min(len(C), len(obs_dist))):
            score += C[i] * obs_dist[i]
        return score

    def _validate_state_distribution(self, state_dist: list[float]) -> None:
        if len(state_dist) != self._n_states:
            raise ValueError("state distribution has incompatible dimensions")
        if any(value < 0.0 for value in state_dist) or not all(
            value == value and abs(value) != float("inf") for value in state_dist
        ):
            raise ValueError("state distribution must be finite and non-negative")
        if state_dist and abs(sum(state_dist) - 1.0) > 1e-6:
            raise ValueError("state distribution must sum to 1.0")

    def prior(self) -> list[float]:
        """Return D vector (initial state prior)."""
        return list(self._D)

    def expected_free_energy(self, state_dist: list[float], action: int) -> float:
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
        """Convenience: parse GNN markdown and return MatrixFunctions.

        Args:
            gnn_text: The full body of a ``*.gnn.md`` file as a string.

        Returns:
            A :class:`MatrixFunctions` bound to the parsed model.

        Example:
            >>> gnn = '''## ModelName\\nDemo\\n\\n## StateSpaceBlock\\ns[2]\\no[2]\\n'''
            >>> mf = MatrixFunctions.from_gnn_text(gnn)
            >>> isinstance(mf, MatrixFunctions)
            True
        """
        model = parse_gnn(gnn_text)
        return cls(model)


def make_matrix_functions(model: ReverseGNNModel) -> MatrixFunctions:
    """Convenience wrapper -- equivalent to MatrixFunctions(model).

    Args:
        model: A parsed :class:`ReverseGNNModel`.

    Returns:
        A :class:`MatrixFunctions` bound to ``model``.

    Example:
        >>> from cogant.reverse.parser import ReverseGNNModel
        >>> model = ReverseGNNModel()
        >>> model.hidden_states = ["s_f0", "s_f1"]
        >>> model.observations = ["o_m0", "o_m1"]
        >>> mf = make_matrix_functions(model)
        >>> isinstance(mf, MatrixFunctions)
        True
    """
    return MatrixFunctions(model)


__all__ = ["MatrixFunctions", "make_matrix_functions"]
