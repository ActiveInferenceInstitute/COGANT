"""Single hidden state factor with update dynamics.

Triggers:
    - HiddenStateRule: class with `state` attribute set in __init__
    - ActionRule: `update_state` method (keyword "update", WRITES edge)
"""

from __future__ import annotations


class BeliefState:
    """A single hidden state factor representing beliefs about position."""

    def __init__(self, num_states: int = 4) -> None:
        self.state: list[float] = [1.0 / num_states] * num_states
        self.num_states = num_states

    def update_state(self, observation_index: int) -> None:
        """Bayesian-style belief update given an observation.

        Shifts probability mass toward the observed state.
        """
        learning_rate = 0.3
        for i in range(self.num_states):
            if i == observation_index:
                self.state[i] += learning_rate * (1.0 - self.state[i])
            else:
                self.state[i] *= 1.0 - learning_rate

        # Normalise
        total = sum(self.state)
        if total > 0:
            self.state = [s / total for s in self.state]

    def get_state(self) -> list[float]:
        """Return current belief distribution (read-only)."""
        return list(self.state)


if __name__ == "__main__":
    belief = BeliefState(num_states=4)
    print("initial:", belief.get_state())
    belief.update_state(2)
    print("after obs 2:", belief.get_state())
    belief.update_state(2)
    print("after obs 2 again:", belief.get_state())
