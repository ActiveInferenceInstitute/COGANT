"""Policy selection: select_action and select_policy functions.

Triggers:
    - PolicyRule: `PolicyRouter` class (keyword "router") -> POLICY
    - PolicyRule: `route()` method (keyword "route") -> POLICY
    - PolicyRule: `dispatch_action()` method (keyword "dispatch") -> POLICY
    - ActionRule: `execute_policy()` method (keyword "execute") -> ACTION
    - ObservationRule: `get_available_actions()` (keyword "get", read-only)
"""

from __future__ import annotations

import random


class PolicyRouter:
    """Routes beliefs to actions through a policy lookup table."""

    def __init__(self, num_states: int = 4, num_actions: int = 3) -> None:
        self.num_states = num_states
        self.num_actions = num_actions
        # Simple policy table: state -> preferred action
        self.policy_table: list[int] = [
            i % num_actions for i in range(num_states)
        ]
        self.last_action: int | None = None

    def route(self, beliefs: list[float]) -> int:
        """Select the best action given belief distribution.

        Uses MAP estimate over beliefs to index the policy table.
        """
        best_state = beliefs.index(max(beliefs))
        return self.policy_table[best_state]

    def dispatch_action(self, beliefs: list[float], temperature: float = 0.1) -> int:
        """Softmax action selection with exploration temperature."""
        import math
        weights = []
        for i in range(self.num_actions):
            # Sum belief mass that maps to this action
            mass = sum(
                beliefs[s] for s in range(self.num_states)
                if self.policy_table[s] == i
            )
            weights.append(math.exp(mass / max(temperature, 1e-8)))

        total = sum(weights)
        probs = [w / total for w in weights]

        # Weighted random selection
        r = random.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                return i
        return self.num_actions - 1

    def execute_policy(self, beliefs: list[float]) -> int:
        """Execute the policy and store the selected action."""
        action = self.route(beliefs)
        self.last_action = action
        return action

    def get_available_actions(self) -> list[int]:
        """Return the set of available actions (read-only)."""
        return list(range(self.num_actions))


if __name__ == "__main__":
    router = PolicyRouter(num_states=4, num_actions=3)
    beliefs = [0.1, 0.6, 0.2, 0.1]
    print("route:", router.route(beliefs))
    print("dispatch:", router.dispatch_action(beliefs))
    print("execute:", router.execute_policy(beliefs))
    print("available:", router.get_available_actions())
