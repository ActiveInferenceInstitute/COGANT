"""Single observation modality: a temperature sensor.

Triggers:
    - ObservationRule: `observe()` and `read_temperature()` methods (read-only)
    - ContextRule: `get_status()` reads and returns (read-only + returns)
"""

from __future__ import annotations

import random


class TemperatureSensor:
    """Reads temperature from a simulated environment."""

    def __init__(self, noise_std: float = 0.1) -> None:
        self.noise_std = noise_std
        self._true_temp = 20.0  # ground truth, not directly accessible

    def observe(self) -> float:
        """Return a noisy observation of the true temperature.

        This is a pure read operation --- no state mutation occurs.
        """
        noise = random.gauss(0.0, self.noise_std)
        return self._true_temp + noise

    def read_temperature(self) -> float:
        """Alias for observe(), using the 'read_' prefix convention."""
        return self.observe()

    def get_status(self) -> dict[str, float]:
        """Return sensor metadata (read-only)."""
        return {
            "noise_std": self.noise_std,
            "last_reading": self.observe(),
        }


if __name__ == "__main__":
    sensor = TemperatureSensor(noise_std=0.5)
    readings = [sensor.observe() for _ in range(5)]
    print("readings:", [round(r, 2) for r in readings])
    print("status:", sensor.get_status())
