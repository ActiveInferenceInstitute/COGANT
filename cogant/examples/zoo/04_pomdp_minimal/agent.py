"""Minimal POMDP agent: state + observation + action in one loop.

Triggers:
    - HiddenStateRule: `self.state` attribute in __init__
    - ObservationRule: `observe()` method (read-only, keyword match)
    - ActionRule: `update_beliefs()` (keyword "update", WRITES edge)
    - ActionRule: `act()` (mutates self.state)
"""

from __future__ import annotations

import random


class MinimalPOMDPAgent:
    """A stripped-down POMDP agent with discrete states and actions."""

    def __init__(self, num_states: int = 3, num_actions: int = 2) -> None:
        self.num_states = num_states
        self.num_actions = num_actions
        self.state: list[float] = [1.0 / num_states] * num_states
        self.last_observation: int | None = None

    def observe(self, environment_state: int) -> int:
        """Generate a noisy observation of the true environment state.

        Read-only: does not mutate agent beliefs.
        """
        if random.random() < 0.8:
            return environment_state
        return random.randint(0, self.num_states - 1)

    def update_beliefs(self, observation: int) -> None:
        """Bayesian belief update given a new observation."""
        self.last_observation = observation
        likelihood = 0.8
        for i in range(self.num_states):
            if i == observation:
                self.state[i] *= likelihood
            else:
                self.state[i] *= (1.0 - likelihood) / max(1, self.num_states - 1)

        total = sum(self.state)
        if total > 0:
            self.state = [s / total for s in self.state]

    def act(self) -> int:
        """Select and execute an action based on current beliefs.

        Picks the action that would move toward the most likely state.
        """
        best_state = self.state.index(max(self.state))
        action = best_state % self.num_actions
        return action

    def step(self, environment_state: int) -> int:
        """Run one perception-action cycle."""
        obs = self.observe(environment_state)
        self.update_beliefs(obs)
        return self.act()


if __name__ == "__main__":
    agent = MinimalPOMDPAgent(num_states=3, num_actions=2)
    for t in range(5):
        true_state = t % 3
        action = agent.step(true_state)
        print(
            f"t={t} true={true_state} action={action} beliefs={[round(s, 2) for s in agent.state]}"
        )
