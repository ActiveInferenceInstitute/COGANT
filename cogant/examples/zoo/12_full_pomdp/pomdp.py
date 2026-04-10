"""Complete POMDP: states + observations + actions + policy + constraints.

Triggers:
    - HiddenStateRule: `self.state` attribute in __init__
    - ObservationRule: `observe()` method (read-only)
    - ObservationRule: `get_beliefs()` (keyword "get", read-only)
    - ActionRule: `update_beliefs()` (keyword "update", WRITES edge)
    - ActionRule: `execute_action()` (keyword "execute", WRITES edge)
    - PolicyRule: `PolicyHandler` class (keyword "handler")
    - PolicyRule: `handle_decision()` (keyword "handle")
    - PreferenceRule: `ConstraintChecker` class (keyword "checker")
    - PreferenceRule: `validate_action()` (keyword "validate")
    - PreferenceRule: `check_safety()` (keyword "check")
"""

from __future__ import annotations

import math
import random


# --- Hidden State ---

class HiddenStateModel:
    """Discrete hidden state with Bayesian belief updates."""

    def __init__(self, num_states: int = 5) -> None:
        self.num_states = num_states
        self.state: list[float] = [1.0 / num_states] * num_states

    def update_beliefs(self, observation: int, likelihood: float = 0.8) -> None:
        """Update beliefs given a new observation (Bayes rule)."""
        for i in range(self.num_states):
            if i == observation:
                self.state[i] *= likelihood
            else:
                self.state[i] *= (1.0 - likelihood) / max(1, self.num_states - 1)
        total = sum(self.state)
        if total > 0:
            self.state = [s / total for s in self.state]

    def get_beliefs(self) -> list[float]:
        """Read-only access to belief distribution."""
        return list(self.state)


# --- Observation ---

class ObservationModel:
    """Generates noisy observations of hidden state."""

    def __init__(self, accuracy: float = 0.8) -> None:
        self.accuracy = accuracy

    def observe(self, true_state: int, num_states: int) -> int:
        """Generate a noisy observation. Read-only (no mutation)."""
        if random.random() < self.accuracy:
            return true_state
        return random.randint(0, num_states - 1)

    def get_likelihood_matrix(self, num_states: int) -> list[list[float]]:
        """Return the likelihood matrix A (read-only)."""
        matrix = []
        for i in range(num_states):
            row = []
            for j in range(num_states):
                if i == j:
                    row.append(self.accuracy)
                else:
                    row.append((1.0 - self.accuracy) / max(1, num_states - 1))
            matrix.append(row)
        return matrix


# --- Policy ---

class PolicyHandler:
    """Selects actions based on expected free energy minimisation."""

    def __init__(self, num_actions: int = 3) -> None:
        self.num_actions = num_actions
        self.last_efe: list[float] = []

    def handle_decision(
        self,
        beliefs: list[float],
        preferences: list[float],
    ) -> int:
        """Select the action that minimises expected free energy."""
        self.last_efe = []
        for a in range(self.num_actions):
            # Simplified EFE: pragmatic value only
            shifted = beliefs[a:] + beliefs[:a]
            pragmatic = -sum(s * p for s, p in zip(shifted, preferences))
            epistemic = sum(s * math.log(s + 1e-12) for s in shifted)
            self.last_efe.append(pragmatic + epistemic)

        return self.last_efe.index(min(self.last_efe))


# --- Constraint ---

class ConstraintChecker:
    """Validates that actions and states satisfy safety constraints."""

    def __init__(self, forbidden_states: list[int] | None = None) -> None:
        self.forbidden_states = forbidden_states or []

    def validate_action(self, action: int, num_actions: int) -> bool:
        """Check that the action index is in valid range."""
        return 0 <= action < num_actions

    def check_safety(self, beliefs: list[float]) -> bool:
        """Ensure the agent does not concentrate belief on forbidden states."""
        for s in self.forbidden_states:
            if s < len(beliefs) and beliefs[s] > 0.8:
                return False
        return True


# --- Full Agent ---

class FullPOMDPAgent:
    """Complete POMDP agent wiring all components together."""

    def __init__(
        self,
        num_states: int = 5,
        num_actions: int = 3,
        forbidden_states: list[int] | None = None,
    ) -> None:
        self.hidden = HiddenStateModel(num_states)
        self.obs_model = ObservationModel(accuracy=0.8)
        self.policy = PolicyHandler(num_actions)
        self.checker = ConstraintChecker(forbidden_states or [0])
        self.preferences = [0.05, 0.05, 0.8, 0.05, 0.05]
        self.num_states = num_states
        self.num_actions = num_actions

    def step(self, true_state: int) -> dict:
        """Execute one full perception-action cycle."""
        obs = self.obs_model.observe(true_state, self.num_states)
        self.hidden.update_beliefs(obs)
        action = self.policy.handle_decision(
            self.hidden.get_beliefs(),
            self.preferences,
        )
        safe = self.checker.check_safety(self.hidden.get_beliefs())
        valid = self.checker.validate_action(action, self.num_actions)

        if not safe or not valid:
            action = 0  # fallback to safe default

        self.execute_action(action)
        return {
            "observation": obs,
            "beliefs": self.hidden.get_beliefs(),
            "action": action,
            "safe": safe,
        }

    def execute_action(self, action: int) -> None:
        """Apply the selected action to the environment (stub)."""
        pass  # In a real system this would mutate environment state


if __name__ == "__main__":
    agent = FullPOMDPAgent(num_states=5, num_actions=3, forbidden_states=[0])
    for t in range(8):
        true_state = (t + 1) % 5
        result = agent.step(true_state)
        beliefs_str = [round(b, 3) for b in result["beliefs"]]
        print(f"t={t} obs={result['observation']} act={result['action']} safe={result['safe']} beliefs={beliefs_str}")
