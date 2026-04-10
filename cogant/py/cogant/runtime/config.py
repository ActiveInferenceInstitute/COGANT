"""Agent configuration for the Active Inference runtime.

Uses a plain dataclass rather than pydantic to maintain the zero-dependency
constraint of the runtime package.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Configuration for the Active Inference agent loop.

    Attributes:
        max_steps: Maximum number of inference steps before forced halt.
        convergence_threshold: KL divergence threshold below which the
            agent considers its belief to have converged.
        action_selection: Strategy for selecting actions. Currently
            only ``"preference"`` (argmax of preference_score) is
            supported.
        seed: Random seed for reproducibility (reserved for future
            stochastic action selection).
    """

    max_steps: int = 100
    convergence_threshold: float = 1e-4
    action_selection: str = "preference"
    seed: int = 42


__all__ = ["AgentConfig"]
