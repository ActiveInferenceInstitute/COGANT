"""Active Inference agent loop: step, run_n_steps, run_until_convergence.

The loop wraps a synthesized matrices module (or any object exposing
``A``, ``B``, ``C``, ``D``, ``likelihood``, ``transition``, and
``preference_score`` attributes) and executes the perception-action
cycle:

1. **Observe**: compute predicted observations via ``likelihood(state_dist)``.
2. **Infer**: update the state belief using Bayesian-ish update (likelihood
   weighting).
3. **Act**: select an action by evaluating ``preference_score`` for each
   candidate action's predicted observation distribution.
4. **Transition**: advance the state belief via ``transition(state_dist, action)``.

Each step records an :class:`AgentStep` capturing the belief state,
observation, chosen action, and variational free energy at that timestep.
"""

from __future__ import annotations

import math
import types
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from cogant.runtime.config import AgentConfig
from cogant.runtime.metrics import free_energy as compute_free_energy
from cogant.runtime.metrics import kl_divergence

_EPS = 1e-10


@dataclass
class AgentStep:
    """Record of a single inference step.

    Attributes:
        t: Timestep index (0-based).
        state_dist: Belief distribution over hidden states after this step.
        obs: Index of the observed modality (argmax of predicted obs).
        action: Index of the selected action.
        free_energy: Variational free energy at this step.
    """

    t: int
    state_dist: List[float]
    obs: int
    action: int
    free_energy: float


def _normalize(dist: List[float]) -> List[float]:
    """Normalize a distribution to sum to 1, with epsilon safety."""
    total = sum(dist)
    if total > _EPS:
        return [v / total for v in dist]
    n = len(dist)
    return [1.0 / n] * n if n > 0 else []


def _argmax(values: List[float]) -> int:
    """Return the index of the maximum value."""
    if not values:
        return 0
    best_idx = 0
    best_val = values[0]
    for i in range(1, len(values)):
        if values[i] > best_val:
            best_val = values[i]
            best_idx = i
    return best_idx


def _mat_vec(mat: List[List[float]], vec: List[float]) -> List[float]:
    """Multiply a 2D matrix by a vector: result[i] = sum_j mat[i][j] * vec[j]."""
    result = []
    for row in mat:
        s = 0.0
        for a, b in zip(row, vec):
            s += a * b
        result.append(s)
    return result


def _default_likelihood(A: List[List[float]], state_dist: List[float]) -> List[float]:
    """Fallback likelihood when the matrices module has no likelihood function."""
    return _mat_vec(A, state_dist)


def _default_transition(
    B: List[List[List[float]]], state_dist: List[float], action: int = 0
) -> List[float]:
    """Fallback transition when the matrices module has no transition function."""
    n_states = len(state_dist)
    result = [0.0] * n_states
    for i in range(n_states):
        for j in range(min(len(B[i]) if i < len(B) else 0, n_states)):
            row = B[i][j] if i < len(B) and j < len(B[i]) else []
            k = min(action, len(row) - 1) if row else 0
            val = row[k] if row and k < len(row) else 0.0
            result[i] += val * state_dist[j]
    return _normalize(result)


def _default_preference_score(C: List[float], obs_dist: List[float]) -> float:
    """Fallback preference score when the matrices module has none."""
    return sum(c * o for c, o in zip(C, obs_dist))


class AgentRuntime:
    """Active Inference agent runtime wrapping a matrices module.

    The matrices module (or namespace) must expose at minimum:
    ``A``, ``B``, ``C``, ``D`` as nested lists. It may optionally expose
    ``likelihood(state_dist)``, ``transition(state_dist, action)``, and
    ``preference_score(obs_dist)`` as callable helpers.

    Args:
        matrices: A module or namespace with A, B, C, D attributes.
    """

    def __init__(self, matrices: Any) -> None:
        self.A: List[List[float]] = getattr(matrices, "A", [])
        self.B: List[List[List[float]]] = getattr(matrices, "B", [])
        self.C: List[float] = getattr(matrices, "C", [])
        self.D: List[float] = getattr(matrices, "D", [])

        # Bind helper functions (use module's if available, else fallback)
        if hasattr(matrices, "likelihood") and callable(matrices.likelihood):
            self._likelihood = matrices.likelihood
        else:
            self._likelihood = lambda sd: _default_likelihood(self.A, sd)

        if hasattr(matrices, "transition") and callable(matrices.transition):
            self._transition = matrices.transition
        else:
            self._transition = lambda sd, a=0: _default_transition(self.B, sd, a)

        if hasattr(matrices, "preference_score") and callable(matrices.preference_score):
            self._preference_score = matrices.preference_score
        else:
            self._preference_score = lambda od: _default_preference_score(self.C, od)

        self._n_states = len(self.D) if self.D else (len(self.A[0]) if self.A and self.A[0] else 1)
        self._n_obs = len(self.A) if self.A else 1
        self._n_actions = (
            len(self.B[0][0]) if self.B and self.B[0] and self.B[0][0] else 1
        )

    @classmethod
    def from_matrices_dict(cls, d: Dict[str, Any]) -> "AgentRuntime":
        """Create an AgentRuntime from a plain dict with keys A, B, C, D.

        Builds lightweight likelihood/transition/preference_score helpers
        from the raw matrices so that no synthesized module is required.

        Args:
            d: Dictionary with at least ``A``, ``B``, ``C``, ``D`` keys.

        Returns:
            An AgentRuntime instance.
        """
        ns = types.SimpleNamespace(
            A=d["A"],
            B=d["B"],
            C=d["C"],
            D=d["D"],
        )
        # Attach default helpers that close over the dict's matrices.
        A, B, C = d["A"], d["B"], d["C"]
        ns.likelihood = lambda sd: _default_likelihood(A, sd)
        ns.transition = lambda sd, a=0: _default_transition(B, sd, a)
        ns.preference_score = lambda od: _default_preference_score(C, od)
        return cls(ns)

    def step(self, state_dist: List[float], obs_idx: int, t: int = 0) -> AgentStep:
        """Execute one inference step.

        1. Compute predicted observations from current belief.
        2. Weight belief by likelihood of the observed modality.
        3. Select best action by evaluating preference over each
           action's predicted next-observation distribution.
        4. Transition state belief using the chosen action.
        5. Compute variational free energy.

        Args:
            state_dist: Current belief over hidden states (sums to ~1).
            obs_idx: Index of the current observation.
            t: Timestep label for the returned AgentStep.

        Returns:
            An AgentStep with the updated belief, action, and VFE.
        """
        # 1. Predicted observations
        pred_obs = self._likelihood(state_dist)

        # 2. Bayesian belief update: weight state by likelihood of obs
        if obs_idx < self._n_obs and self.A:
            weights = [
                self.A[obs_idx][j] if j < len(self.A[obs_idx]) else _EPS
                for j in range(len(state_dist))
            ]
            updated = [s * w for s, w in zip(state_dist, weights)]
            state_dist = _normalize(updated)

        # 3. Action selection: evaluate each action
        best_action = 0
        best_score = float("-inf")
        for a in range(self._n_actions):
            next_state = self._transition(list(state_dist), a)
            next_obs = self._likelihood(next_state)
            score = self._preference_score(next_obs)
            if score > best_score:
                best_score = score
                best_action = a

        # 4. Transition
        new_state = self._transition(list(state_dist), best_action)
        new_state = _normalize(new_state)

        # 5. Free energy
        fe = compute_free_energy(new_state, obs_idx, self.A, self.C, self.D)

        return AgentStep(
            t=t,
            state_dist=new_state,
            obs=obs_idx,
            action=best_action,
            free_energy=fe,
        )

    def run_n_steps(
        self, n: int, initial_state: Optional[List[float]] = None
    ) -> List[AgentStep]:
        """Run ``n`` inference steps from an initial state.

        At each step the observation is chosen as the argmax of the
        predicted observation distribution (a simplification of actual
        sensory sampling).

        Args:
            n: Number of steps to run.
            initial_state: Initial belief distribution. Defaults to D.

        Returns:
            List of ``n`` AgentStep records.
        """
        state = list(initial_state) if initial_state is not None else list(self.D)
        state = _normalize(state)
        steps: List[AgentStep] = []
        for t in range(n):
            pred_obs = self._likelihood(state)
            obs_idx = _argmax(pred_obs)
            agent_step = self.step(state, obs_idx, t=t)
            steps.append(agent_step)
            state = list(agent_step.state_dist)
        return steps

    def run_until_convergence(
        self,
        initial_state: Optional[List[float]] = None,
        cfg: Optional[AgentConfig] = None,
    ) -> List[AgentStep]:
        """Run until KL(state[t] || state[t-1]) < convergence_threshold.

        Args:
            initial_state: Initial belief distribution. Defaults to D.
            cfg: Agent configuration. Defaults to AgentConfig().

        Returns:
            List of AgentStep records up to and including the
            converged step.
        """
        if cfg is None:
            cfg = AgentConfig()
        state = list(initial_state) if initial_state is not None else list(self.D)
        state = _normalize(state)
        steps: List[AgentStep] = []
        prev_state = list(state)

        for t in range(cfg.max_steps):
            pred_obs = self._likelihood(state)
            obs_idx = _argmax(pred_obs)
            agent_step = self.step(state, obs_idx, t=t)
            steps.append(agent_step)

            # Check convergence after at least one step
            if t > 0:
                kl = kl_divergence(agent_step.state_dist, prev_state)
                if kl < cfg.convergence_threshold:
                    break

            prev_state = list(agent_step.state_dist)
            state = list(agent_step.state_dist)

        return steps


def run_n_steps(
    runtime: AgentRuntime, n: int, initial_state: Optional[List[float]] = None
) -> List[AgentStep]:
    """Module-level convenience: run ``n`` steps on a runtime.

    Args:
        runtime: An initialized AgentRuntime.
        n: Number of steps.
        initial_state: Initial belief distribution.

    Returns:
        List of AgentStep records.
    """
    return runtime.run_n_steps(n, initial_state)


def run_until_convergence(
    runtime: AgentRuntime,
    initial_state: Optional[List[float]] = None,
    cfg: Optional[AgentConfig] = None,
) -> List[AgentStep]:
    """Module-level convenience: run until convergence.

    Args:
        runtime: An initialized AgentRuntime.
        initial_state: Initial belief distribution.
        cfg: Agent configuration.

    Returns:
        List of AgentStep records.
    """
    return runtime.run_until_convergence(initial_state, cfg)


__all__ = [
    "AgentStep",
    "AgentRuntime",
    "run_n_steps",
    "run_until_convergence",
]
