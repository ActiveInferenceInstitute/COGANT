"""Two independent hidden state factors: temperature and pressure.

Triggers:
    - HiddenStateRule: `self.state_temperature` attribute
    - HiddenStateRule: `self.state_pressure` attribute
    - ActionRule: `update_temperature()` and `update_pressure()` (keyword "update")
    - ObservationRule: `get_temperature()` and `get_pressure()` (keyword "get", read-only)
"""

from __future__ import annotations


class DualFactorBelief:
    """Maintains beliefs over two independent hidden state factors."""

    def __init__(self, temp_states: int = 5, pressure_states: int = 3) -> None:
        self.temp_states = temp_states
        self.pressure_states = pressure_states
        self.state_temperature: list[float] = [1.0 / temp_states] * temp_states
        self.state_pressure: list[float] = [1.0 / pressure_states] * pressure_states

    def update_temperature(self, observation: int) -> None:
        """Update temperature belief given a temperature observation."""
        rate = 0.25
        for i in range(self.temp_states):
            if i == observation:
                self.state_temperature[i] += rate * (1.0 - self.state_temperature[i])
            else:
                self.state_temperature[i] *= 1.0 - rate
        total = sum(self.state_temperature)
        if total > 0:
            self.state_temperature = [s / total for s in self.state_temperature]

    def update_pressure(self, observation: int) -> None:
        """Update pressure belief given a pressure observation."""
        rate = 0.25
        for i in range(self.pressure_states):
            if i == observation:
                self.state_pressure[i] += rate * (1.0 - self.state_pressure[i])
            else:
                self.state_pressure[i] *= 1.0 - rate
        total = sum(self.state_pressure)
        if total > 0:
            self.state_pressure = [s / total for s in self.state_pressure]

    def get_temperature(self) -> list[float]:
        """Read-only access to temperature beliefs."""
        return list(self.state_temperature)

    def get_pressure(self) -> list[float]:
        """Read-only access to pressure beliefs."""
        return list(self.state_pressure)


if __name__ == "__main__":
    belief = DualFactorBelief(temp_states=5, pressure_states=3)
    belief.update_temperature(2)
    belief.update_pressure(1)
    print("temp:", [round(t, 3) for t in belief.get_temperature()])
    print("pressure:", [round(p, 3) for p in belief.get_pressure()])
