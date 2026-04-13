"""
Simple calculator with state machine.

Exercises: state machine patterns, operations as actions, display as observation,
history as hidden state, assertions as preferences.
"""

from typing import List, Optional


class Calculator:
    """A calculator with state machine semantics."""

    def __init__(self):
        # Hidden state
        self.display = "0"
        self.accumulator = 0
        self.operation = None
        self.history: List[str] = []
        self.new_input = True

    def input_digit(self, digit: int) -> str:
        """Action: input a digit (0-9)."""
        if digit < 0 or digit > 9:
            return self.display

        if self.new_input:
            self.display = str(digit)
            self.new_input = False
        else:
            self.display = self.display + str(digit)

        self.history.append(f"input_digit({digit})")
        return self.display

    def input_operation(self, op: str) -> str:
        """Action: input operation (+, -, *, /)."""
        current_value = int(self.display)

        if self.operation is not None:
            # Execute pending operation
            self.accumulator = self._execute_operation(
                self.accumulator, current_value, self.operation
            )
            self.display = str(self.accumulator)
        else:
            self.accumulator = current_value

        self.operation = op
        self.new_input = True
        self.history.append(f"input_operation({op})")
        return self.display

    def equals(self) -> str:
        """Action: execute equals."""
        if self.operation is None:
            return self.display

        current_value = int(self.display)
        result = self._execute_operation(self.accumulator, current_value, self.operation)

        self.display = str(result)
        self.operation = None
        self.accumulator = 0
        self.new_input = True
        self.history.append("equals()")
        return self.display

    def clear(self) -> str:
        """Action: clear the calculator."""
        self.display = "0"
        self.accumulator = 0
        self.operation = None
        self.new_input = True
        self.history.append("clear()")
        return self.display

    def _execute_operation(self, left: int, right: int, op: str) -> int:
        """Hidden state operation."""
        if op == "+":
            return left + right
        elif op == "-":
            return left - right
        elif op == "*":
            return left * right
        elif op == "/" and right != 0:
            return left // right
        return left

    def get_display(self) -> str:
        """Observation: current display value."""
        return self.display

    def get_history(self) -> List[str]:
        """Observation: operation history."""
        return self.history.copy()

    def assert_display(self, expected: str) -> bool:
        """Preference: assertion on display."""
        return self.display == expected

    def assert_history_length(self, max_length: int) -> bool:
        """Preference: constraint on history size."""
        return len(self.history) <= max_length


# Example usage
if __name__ == "__main__":
    calc = Calculator()

    # 5 + 3 = 8
    calc.input_digit(5)
    calc.input_operation("+")
    calc.input_digit(3)
    result = calc.equals()

    print(f"Result: {result}")
    print(f"History: {calc.get_history()}")

    # Assertions
    assert calc.assert_display("8"), "Display should be 8"
    assert calc.assert_history_length(10), "History should be short"
