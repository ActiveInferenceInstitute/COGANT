"""Single action type: a thermostat actuator.

Triggers:
    - ActionRule: `act()` method (mutates self.current_output)
    - ActionRule: `set_target()` method (keyword "set", WRITES edge)
    - ActionRule: `execute_action()` method (keyword "execute")
"""

from __future__ import annotations


class ThermostatActuator:
    """Controls a heater by setting output power level."""

    def __init__(self, max_power: float = 100.0) -> None:
        self.max_power = max_power
        self.current_output: float = 0.0
        self.target_temperature: float = 20.0

    def act(self, desired_power: float) -> None:
        """Set the heater output power (clamped to valid range).

        This mutates `self.current_output`.
        """
        self.current_output = max(0.0, min(desired_power, self.max_power))

    def set_target(self, temperature: float) -> None:
        """Set the desired target temperature."""
        self.target_temperature = temperature

    def execute_action(self, error_signal: float) -> None:
        """Proportional controller: convert error signal to power output."""
        gain = 2.0
        power = gain * error_signal
        self.act(power)


if __name__ == "__main__":
    actuator = ThermostatActuator(max_power=100.0)
    actuator.set_target(25.0)
    actuator.execute_action(error_signal=5.0)
    print(f"output power: {actuator.current_output}")
