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

import types
from dataclasses import dataclass
from typing import Any

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
    state_dist: list[float]
    obs: int
    action: int
    free_energy: float


@dataclass
class EpisodeResult:
    """Result of running one learning episode.

    Attributes:
        steps: Ordered list of :class:`AgentStep` records for the episode.
        final_posterior: Belief distribution over hidden states at the
            end of the episode (the last step's ``state_dist``).
        obs_counts: Histogram of observation indices seen during the
            episode (length ``n_obs``; entries sum to ``len(steps)``).
        obs_state_counts: Joint soft counts ``[n_obs x n_states]`` —
            ``obs_state_counts[o][s]`` accumulates ``state_dist[s]`` over
            every step where observation ``o`` was seen. Used for the
            frequency-based A update.
        mean_free_energy: Arithmetic mean of ``step.free_energy`` over
            the episode (``nan`` if the episode is empty).
        final_free_energy: VFE at the last step (``nan`` if empty).
    """

    steps: list[AgentStep]
    final_posterior: list[float]
    obs_counts: list[float]
    obs_state_counts: list[list[float]]
    mean_free_energy: float
    final_free_energy: float


@dataclass
class MultiEpisodeResult:
    """Result of a multi-episode learning run.

    Attributes:
        episodes: Per-episode :class:`EpisodeResult` records.
        vfe_trajectory: Mean VFE per episode (parallel to ``episodes``).
        final_vfe_trajectory: Final-step VFE per episode.
        D_trajectory: Snapshot of the D prior after each episode update.
        learning_rate: Learning rate used for the A likelihood update.
    """

    episodes: list[EpisodeResult]
    vfe_trajectory: list[float]
    final_vfe_trajectory: list[float]
    D_trajectory: list[list[float]]
    learning_rate: float


def _normalize(dist: list[float]) -> list[float]:
    """Normalize a distribution to sum to 1, with epsilon safety."""
    total = sum(dist)
    if total > _EPS:
        return [v / total for v in dist]
    n = len(dist)
    return [1.0 / n] * n if n > 0 else []


def _argmax(values: list[float]) -> int:
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


def _mat_vec(mat: list[list[float]], vec: list[float]) -> list[float]:
    """Multiply a 2D matrix by a vector: result[i] = sum_j mat[i][j] * vec[j]."""
    result = []
    for row in mat:
        s = 0.0
        for a, b in zip(row, vec, strict=False):
            s += a * b
        result.append(s)
    return result


def _default_likelihood(A: list[list[float]], state_dist: list[float]) -> list[float]:
    """Fallback likelihood when the matrices module has no likelihood function."""
    return _mat_vec(A, state_dist)


def _default_transition(
    B: list[list[list[float]]], state_dist: list[float], action: int = 0
) -> list[float]:
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


def _default_preference_score(C: list[float], obs_dist: list[float]) -> float:
    """Fallback preference score when the matrices module has none."""
    return sum(c * o for c, o in zip(C, obs_dist, strict=False))


class AgentRuntime:
    """Active Inference agent runtime wrapping a matrices module.

    The matrices module (or namespace) must expose at minimum:
    ``A``, ``B``, ``C``, ``D`` as nested lists. It may optionally expose
    ``likelihood(state_dist)``, ``transition(state_dist, action)``, and
    ``preference_score(obs_dist)`` as callable helpers.

    Args:
        matrices: A module or namespace with A, B, C, D attributes.

    Example:
        Build a runtime from raw POMDP matrices and run three perception
        steps::

            from cogant.runtime.loop import AgentRuntime

            rt = AgentRuntime.from_matrices_dict({
                "A": [[0.9, 0.1], [0.1, 0.9]],
                "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
                "C": [1.0, 0.0],
                "D": [0.5, 0.5],
            })
            steps = rt.run_n_steps(3)
            assert len(steps) == 3
    """

    def __init__(self, matrices: Any) -> None:
        self.A: list[list[float]] = getattr(matrices, "A", [])
        self.B: list[list[list[float]]] = getattr(matrices, "B", [])
        self.C: list[float] = getattr(matrices, "C", [])
        self.D: list[float] = getattr(matrices, "D", [])

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
        # Number of episodes completed — drives the running-average D update.
        self._episode_count = 0

    @classmethod
    def from_matrices_dict(cls, d: dict[str, Any]) -> AgentRuntime:
        """Create an AgentRuntime from a plain dict with keys A, B, C, D.

        Builds lightweight likelihood/transition/preference_score helpers
        from the raw matrices so that no synthesized module is required.

        Args:
            d: Dictionary with at least ``A``, ``B``, ``C``, ``D`` keys.

        Returns:
            An AgentRuntime instance.

        Example:
            >>> rt = AgentRuntime.from_matrices_dict({
            ...     "A": [[1.0, 0.0], [0.0, 1.0]],
            ...     "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
            ...     "C": [0.0, 1.0],
            ...     "D": [0.5, 0.5],
            ... })
            >>> isinstance(rt, AgentRuntime)
            True
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

    def step(self, state_dist: list[float], obs_idx: int, t: int = 0) -> AgentStep:
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

        Example:
            >>> rt = AgentRuntime.from_matrices_dict({
            ...     "A": [[0.9, 0.1], [0.1, 0.9]],
            ...     "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
            ...     "C": [1.0, 0.0],
            ...     "D": [0.5, 0.5],
            ... })
            >>> s = rt.step([0.5, 0.5], obs_idx=0, t=0)
            >>> s.t, len(s.state_dist)
            (0, 2)
        """
        # 1. Predicted observations
        self._likelihood(state_dist)

        # 2. Bayesian belief update: weight state by likelihood of obs
        if obs_idx < self._n_obs and self.A:
            weights = [
                self.A[obs_idx][j] if j < len(self.A[obs_idx]) else _EPS
                for j in range(len(state_dist))
            ]
            updated = [s * w for s, w in zip(state_dist, weights, strict=False)]
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
        self, n: int, initial_state: list[float] | None = None
    ) -> list[AgentStep]:
        """Run ``n`` inference steps from an initial state.

        At each step the observation is chosen as the argmax of the
        predicted observation distribution (a simplification of actual
        sensory sampling).

        Args:
            n: Number of steps to run.
            initial_state: Initial belief distribution. Defaults to D.

        Returns:
            List of ``n`` AgentStep records.

        Example:
            >>> rt = AgentRuntime.from_matrices_dict({
            ...     "A": [[0.9, 0.1], [0.1, 0.9]],
            ...     "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
            ...     "C": [1.0, 0.0],
            ...     "D": [0.5, 0.5],
            ... })
            >>> steps = rt.run_n_steps(5)
            >>> len(steps)
            5
        """
        state = list(initial_state) if initial_state is not None else list(self.D)
        state = _normalize(state)
        steps: list[AgentStep] = []
        for t in range(n):
            pred_obs = self._likelihood(state)
            obs_idx = _argmax(pred_obs)
            agent_step = self.step(state, obs_idx, t=t)
            steps.append(agent_step)
            state = list(agent_step.state_dist)
        return steps

    def run_until_convergence(
        self,
        initial_state: list[float] | None = None,
        cfg: AgentConfig | None = None,
    ) -> list[AgentStep]:
        """Run until KL(state[t] || state[t-1]) < convergence_threshold.

        Args:
            initial_state: Initial belief distribution. Defaults to D.
            cfg: Agent configuration. Defaults to AgentConfig().

        Returns:
            List of AgentStep records up to and including the
            converged step.

        Example:
            >>> from cogant.runtime.config import AgentConfig
            >>> rt = AgentRuntime.from_matrices_dict({
            ...     "A": [[0.99, 0.01], [0.01, 0.99]],
            ...     "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
            ...     "C": [1.0, 0.0],
            ...     "D": [0.5, 0.5],
            ... })
            >>> steps = rt.run_until_convergence(cfg=AgentConfig(max_steps=20))
            >>> 1 <= len(steps) <= 20
            True
        """
        if cfg is None:
            cfg = AgentConfig()
        state = list(initial_state) if initial_state is not None else list(self.D)
        state = _normalize(state)
        steps: list[AgentStep] = []
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

    # ------------------------------------------------------------------
    # Multi-episode learning
    # ------------------------------------------------------------------

    def run_episode(
        self,
        n_steps: int,
        initial_state: list[float] | None = None,
    ) -> EpisodeResult:
        """Run one learning episode of ``n_steps`` inference cycles.

        Re-uses :meth:`run_n_steps` for the perception-action loop and
        additionally accumulates per-modality observation histograms and
        joint ``(obs, state)`` soft counts. The joint counts are the
        statistic required by the frequency-based A update in
        :meth:`update_A_from_counts`.

        Args:
            n_steps: Number of perception-action cycles. ``0`` yields an
                empty result whose posterior falls back to the current
                prior ``D`` (or a uniform distribution if ``D`` is empty).
            initial_state: Optional belief distribution to start from. If
                ``None`` the current ``D`` prior is used.

        Returns:
            An :class:`EpisodeResult` capturing the trajectory and the
            sufficient statistics for learning updates.

        Example:
            >>> rt = AgentRuntime.from_matrices_dict({
            ...     "A": [[0.9, 0.1], [0.1, 0.9]],
            ...     "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
            ...     "C": [1.0, 0.0],
            ...     "D": [0.5, 0.5],
            ... })
            >>> result = rt.run_episode(4)
            >>> len(result.steps), len(result.final_posterior)
            (4, 2)
        """
        n_obs = max(self._n_obs, 1)
        n_states = max(self._n_states, 1)
        obs_counts = [0.0] * n_obs
        obs_state_counts = [[0.0] * n_states for _ in range(n_obs)]

        steps = self.run_n_steps(n_steps, initial_state=initial_state)

        if not steps:
            if initial_state is not None:
                posterior = _normalize(list(initial_state))
            elif self.D:
                posterior = _normalize(list(self.D))
            else:
                posterior = [1.0 / n_states] * n_states
            return EpisodeResult(
                steps=[],
                final_posterior=posterior,
                obs_counts=obs_counts,
                obs_state_counts=obs_state_counts,
                mean_free_energy=float("nan"),
                final_free_energy=float("nan"),
            )

        total_fe = 0.0
        for step in steps:
            o = step.obs
            if 0 <= o < n_obs:
                obs_counts[o] += 1.0
                row = obs_state_counts[o]
                for j in range(min(n_states, len(step.state_dist))):
                    row[j] += step.state_dist[j]
            total_fe += step.free_energy

        return EpisodeResult(
            steps=steps,
            final_posterior=list(steps[-1].state_dist),
            obs_counts=obs_counts,
            obs_state_counts=obs_state_counts,
            mean_free_energy=total_fe / len(steps),
            final_free_energy=steps[-1].free_energy,
        )

    def update_D_from_posterior(self, posterior: list[float]) -> list[float]:
        """Update the D prior as a running average with the new posterior.

        Implements::

            D_new = (D_old * episode_num + posterior) / (episode_num + 1)

        where ``episode_num`` is the number of episodes completed **before**
        the current update (``self._episode_count``). After the update,
        ``_episode_count`` is incremented so that successive calls produce a
        true arithmetic running mean of posteriors.

        The update mutates ``self.D`` in place **and** rebinds the attribute
        so callers that cached a reference still see consistent values.
        ``posterior`` is normalised defensively before mixing.

        Args:
            posterior: The (unnormalised or normalised) posterior belief
                distribution from the most recent episode.

        Returns:
            The updated D prior (same object as ``self.D``).
        """
        if not self.D or not posterior:
            return self.D
        n = min(len(self.D), len(posterior))
        norm_post = _normalize(list(posterior[:n]))
        k = self._episode_count
        new_D: list[float] = []
        for i in range(n):
            d_old = self.D[i]
            p_new = norm_post[i] if i < len(norm_post) else 0.0
            new_D.append((d_old * k + p_new) / (k + 1))
        # Normalise to guard against floating-point drift.
        new_D = _normalize(new_D)
        # Preserve list identity for any cached references.
        for i in range(n):
            self.D[i] = new_D[i]
        self._episode_count = k + 1
        return self.D

    def update_A_from_counts(
        self,
        obs_state_counts: list[list[float]],
        learning_rate: float = 0.1,
    ) -> list[list[float]]:
        """Frequency-based A likelihood update from episode observations.

        For every observation ``o`` the empirical conditional frequency
        over hidden states,

            freq[o, s] = obs_state_counts[o][s] / sum_s obs_state_counts[o][s]

        is blended into the corresponding row of A::

            A[o, :] += learning_rate * (freq[o, :] - A[o, :])

        After the row update each **column** of A is normalised so that
        ``sum_o A[o, s] == 1`` for every state ``s`` — this preserves the
        likelihood-matrix invariant that each column is a proper
        distribution over observations.

        Observations that were never seen during the episode leave their
        corresponding A rows unchanged, which keeps the update conservative
        and avoids collapsing A toward zeros.

        Args:
            obs_state_counts: ``[n_obs x n_states]`` soft counts from an
                :class:`EpisodeResult`.
            learning_rate: Step size in ``[0, 1]``. ``0`` disables the
                update; ``1`` replaces A rows with empirical frequencies
                (still followed by column normalisation).

        Returns:
            The updated A matrix (same object as ``self.A``).
        """
        if not self.A or not obs_state_counts:
            return self.A
        lr = max(0.0, min(1.0, float(learning_rate)))
        n_obs = len(self.A)
        n_states = len(self.A[0]) if self.A[0] else 0
        if n_states == 0:
            return self.A

        # Row update: blend empirical frequencies into each row.
        for o in range(min(n_obs, len(obs_state_counts))):
            row_counts = obs_state_counts[o]
            total = sum(row_counts[:n_states])
            if total <= _EPS:
                # No observations of this modality -> leave row alone.
                continue
            freq = [row_counts[j] / total if j < len(row_counts) else 0.0 for j in range(n_states)]
            for j in range(n_states):
                self.A[o][j] = (1.0 - lr) * self.A[o][j] + lr * freq[j]

        # Column normalisation: enforce sum_o A[o, s] == 1 per state.
        for s in range(n_states):
            col_sum = 0.0
            for o in range(n_obs):
                col_sum += self.A[o][s]
            if col_sum > _EPS:
                for o in range(n_obs):
                    self.A[o][s] = self.A[o][s] / col_sum
            else:
                # Degenerate column -> reset to uniform so A stays a
                # proper likelihood matrix.
                uniform = 1.0 / n_obs
                for o in range(n_obs):
                    self.A[o][s] = uniform

        return self.A

    def run_multi_episode(
        self,
        n_episodes: int,
        steps_per_episode: int,
        learning_rate: float = 0.1,
        initial_state: list[float] | None = None,
    ) -> MultiEpisodeResult:
        """Run multiple episodes, updating D and A between each.

        Between episodes the runtime:

        1. Updates the D prior as a running average of episode posteriors
           (see :meth:`update_D_from_posterior`).
        2. Updates the A likelihood from observation/state soft counts
           (see :meth:`update_A_from_counts`).

        Each episode starts from ``initial_state`` if provided, otherwise
        from the current (already-updated) D prior — so the agent both
        *uses* and *refines* what it has learned.

        Args:
            n_episodes: Number of episodes to run.
            steps_per_episode: Steps within each episode.
            learning_rate: Learning rate for the A update (0 disables A
                learning; D learning is always a running average).
            initial_state: Optional fixed initial belief for every
                episode. Defaults to the current (updated) D prior.

        Returns:
            A :class:`MultiEpisodeResult` with per-episode VFE trajectories
            and snapshots of the D prior after each update.

        Example:
            >>> rt = AgentRuntime.from_matrices_dict({
            ...     "A": [[0.9, 0.1], [0.1, 0.9]],
            ...     "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
            ...     "C": [1.0, 0.0],
            ...     "D": [0.5, 0.5],
            ... })
            >>> result = rt.run_multi_episode(n_episodes=3, steps_per_episode=2, learning_rate=0.1)
            >>> len(result.episodes), len(result.D_trajectory)
            (3, 3)
        """
        episodes: list[EpisodeResult] = []
        vfe_traj: list[float] = []
        final_vfe_traj: list[float] = []
        D_traj: list[list[float]] = []

        for _ep in range(max(0, n_episodes)):
            result = self.run_episode(
                steps_per_episode,
                initial_state=initial_state,
            )
            episodes.append(result)
            vfe_traj.append(result.mean_free_energy)
            final_vfe_traj.append(result.final_free_energy)

            # Learning updates (order: D then A; both operate on episode stats).
            self.update_D_from_posterior(result.final_posterior)
            self.update_A_from_counts(result.obs_state_counts, learning_rate=learning_rate)
            D_traj.append(list(self.D))

        return MultiEpisodeResult(
            episodes=episodes,
            vfe_trajectory=vfe_traj,
            final_vfe_trajectory=final_vfe_traj,
            D_trajectory=D_traj,
            learning_rate=learning_rate,
        )


def run_n_steps(
    runtime: AgentRuntime, n: int, initial_state: list[float] | None = None
) -> list[AgentStep]:
    """Module-level convenience: run ``n`` steps on a runtime.

    Args:
        runtime: An initialized AgentRuntime.
        n: Number of steps.
        initial_state: Initial belief distribution.

    Returns:
        List of AgentStep records.

    Example:
        >>> from cogant.runtime.loop import AgentRuntime, run_n_steps
        >>> rt = AgentRuntime.from_matrices_dict({
        ...     "A": [[1.0, 0.0], [0.0, 1.0]],
        ...     "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
        ...     "C": [1.0, 0.0],
        ...     "D": [0.5, 0.5],
        ... })
        >>> len(run_n_steps(rt, 2))
        2
    """
    return runtime.run_n_steps(n, initial_state)


def run_until_convergence(
    runtime: AgentRuntime,
    initial_state: list[float] | None = None,
    cfg: AgentConfig | None = None,
) -> list[AgentStep]:
    """Module-level convenience: run until convergence.

    Args:
        runtime: An initialized AgentRuntime.
        initial_state: Initial belief distribution.
        cfg: Agent configuration.

    Returns:
        List of AgentStep records.

    Example:
        >>> from cogant.runtime.loop import AgentRuntime, run_until_convergence
        >>> rt = AgentRuntime.from_matrices_dict({
        ...     "A": [[0.99, 0.01], [0.01, 0.99]],
        ...     "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
        ...     "C": [1.0, 0.0],
        ...     "D": [0.5, 0.5],
        ... })
        >>> steps = run_until_convergence(rt)
        >>> len(steps) > 0
        True
    """
    return runtime.run_until_convergence(initial_state, cfg)


__all__ = [
    "AgentStep",
    "AgentRuntime",
    "EpisodeResult",
    "MultiEpisodeResult",
    "run_n_steps",
    "run_until_convergence",
]
