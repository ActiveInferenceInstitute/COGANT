"""Two observation modalities (visual + tactile) fused into one belief.

Triggers:
    - ObservationRule: `observe_visual()` (read-only, no WRITES)
    - ObservationRule: `observe_tactile()` (read-only, no WRITES)
    - ObservationRule: `read_combined()` (keyword "read", read-only)
    - ActionRule: `update_beliefs()` (keyword "update", WRITES edge)
    - ActionRule: `set_visual_noise()` and `set_tactile_noise()` (keyword "set")
"""

from __future__ import annotations

import random


class VisualSensor:
    """Visual observation modality."""

    def __init__(self, noise: float = 0.15) -> None:
        self.noise = noise

    def observe_visual(self, true_position: float) -> float:
        """Return a noisy visual observation. Read-only."""
        return true_position + random.gauss(0.0, self.noise)

    def set_visual_noise(self, noise: float) -> None:
        """Update the noise level."""
        self.noise = noise


class TactileSensor:
    """Tactile observation modality."""

    def __init__(self, noise: float = 0.3) -> None:
        self.noise = noise

    def observe_tactile(self, true_position: float) -> float:
        """Return a noisy tactile observation. Read-only."""
        return true_position + random.gauss(0.0, self.noise)

    def set_tactile_noise(self, noise: float) -> None:
        """Update the noise level."""
        self.noise = noise


class SensorFusionAgent:
    """Fuses visual and tactile observations into a unified belief."""

    def __init__(self) -> None:
        self.visual = VisualSensor(noise=0.15)
        self.tactile = TactileSensor(noise=0.30)
        self.state: float = 0.0
        self.confidence: float = 0.5

    def update_beliefs(self, true_position: float) -> None:
        """Fuse both sensor modalities to update position belief.

        Uses inverse-variance weighting for optimal Gaussian fusion.
        """
        obs_v = self.visual.observe_visual(true_position)
        obs_t = self.tactile.observe_tactile(true_position)

        # Inverse-variance weighting
        w_v = 1.0 / (self.visual.noise ** 2)
        w_t = 1.0 / (self.tactile.noise ** 2)
        total_w = w_v + w_t

        self.state = (w_v * obs_v + w_t * obs_t) / total_w
        self.confidence = total_w / (total_w + 1.0)

    def read_combined(self) -> dict[str, float]:
        """Read-only access to fused state estimate."""
        return {"position": self.state, "confidence": self.confidence}


if __name__ == "__main__":
    agent = SensorFusionAgent()
    true_pos = 5.0
    for _ in range(5):
        agent.update_beliefs(true_pos)
        result = agent.read_combined()
        print(f"fused: {result['position']:.3f} (conf: {result['confidence']:.3f})")
