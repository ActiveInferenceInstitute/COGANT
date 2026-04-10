"""Parent/child state hierarchy: planner governs executor.

Triggers:
    - HiddenStateRule: `self.state` in both HighLevelPlanner and LowLevelExecutor
    - ActionRule: `update_plan()` and `update_motor()` (keyword "update")
    - ObservationRule: `get_plan()` and `get_motor_state()` (keyword "get", read-only)
"""

from __future__ import annotations


class HighLevelPlanner:
    """Top-level state: which sub-goal is active."""

    def __init__(self, num_goals: int = 3) -> None:
        self.num_goals = num_goals
        self.state: list[float] = [1.0 / num_goals] * num_goals

    def update_plan(self, goal_evidence: int) -> None:
        """Shift belief toward a particular goal."""
        rate = 0.4
        for i in range(self.num_goals):
            if i == goal_evidence:
                self.state[i] += rate * (1.0 - self.state[i])
            else:
                self.state[i] *= 1.0 - rate
        total = sum(self.state)
        if total > 0:
            self.state = [s / total for s in self.state]

    def get_plan(self) -> int:
        """Return the most likely active goal (read-only query)."""
        return self.state.index(max(self.state))


class LowLevelExecutor:
    """Child state: motor commands conditioned on the active plan."""

    def __init__(self, planner: HighLevelPlanner, num_motor_states: int = 4) -> None:
        self.planner = planner
        self.num_motor_states = num_motor_states
        self.state: list[float] = [1.0 / num_motor_states] * num_motor_states

    def update_motor(self, sensory_feedback: int) -> None:
        """Update motor state given sensory feedback and the current plan."""
        active_goal = self.planner.get_plan()
        rate = 0.3
        target = (sensory_feedback + active_goal) % self.num_motor_states
        for i in range(self.num_motor_states):
            if i == target:
                self.state[i] += rate * (1.0 - self.state[i])
            else:
                self.state[i] *= 1.0 - rate
        total = sum(self.state)
        if total > 0:
            self.state = [s / total for s in self.state]

    def get_motor_state(self) -> list[float]:
        """Read-only access to motor state beliefs."""
        return list(self.state)


if __name__ == "__main__":
    planner = HighLevelPlanner(num_goals=3)
    executor = LowLevelExecutor(planner, num_motor_states=4)
    planner.update_plan(1)
    executor.update_motor(2)
    print(f"active goal: {planner.get_plan()}")
    print(f"motor state: {[round(s, 3) for s in executor.get_motor_state()]}")
