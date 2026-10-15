"""Agent configuration for the Active Inference runtime.

Uses a plain dataclass rather than pydantic to maintain the zero-dependency
constraint of the categorical execution core.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for the Active Inference agent loop.

    Attributes:
        max_steps: Maximum number of inference steps before forced halt.
            Must be non-negative.
        convergence_threshold: KL divergence threshold below which the
            agent considers its belief to have converged. Must be in (0, 1).
    """

    max_steps: int = 100
    convergence_threshold: float = 1e-4

    def __post_init__(self) -> None:
        """Validate configuration after initialization.

        Raises:
            ValueError: If any configuration value is invalid.
        """
        if type(self.max_steps) is not int or self.max_steps < 0:
            raise ValueError(f"max_steps must be a non-negative integer; got {self.max_steps}")

        if (
            isinstance(self.convergence_threshold, bool)
            or not isinstance(self.convergence_threshold, (int, float))
            or not math.isfinite(self.convergence_threshold)
            or not (0 < self.convergence_threshold < 1)
        ):
            raise ValueError(
                f"convergence_threshold must be in (0, 1); got {self.convergence_threshold}"
            )

    @classmethod
    def from_yaml(cls, path: str) -> AgentConfig:
        """Load configuration from a YAML file.

        Args:
            path: Path to YAML file with keys matching AgentConfig fields.

        Returns:
            Loaded AgentConfig instance.

        Raises:
            ImportError: If pyyaml is not installed.
            FileNotFoundError: If the file does not exist.
            ValueError: If YAML contains invalid values.

        Example:
            >>> cfg = AgentConfig.from_yaml("config.yaml")
        """
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                "pyyaml is required for from_yaml(); install it with: pip install pyyaml"
            ) from exc

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError("runtime configuration must be a YAML mapping")
        unknown = set(data) - {"max_steps", "convergence_threshold"}
        if unknown:
            raise ValueError(f"unknown runtime configuration fields: {sorted(map(str, unknown))}")
        return cls(**data)

    def to_yaml(self, path: str) -> None:
        """Save configuration to a YAML file.

        Args:
            path: Path where YAML file will be written.

        Raises:
            ImportError: If pyyaml is not installed.

        Example:
            >>> cfg = AgentConfig(max_steps=200)
            >>> cfg.to_yaml("config.yaml")
        """
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                "pyyaml is required for to_yaml(); install it with: pip install pyyaml"
            ) from exc

        data = {
            "max_steps": self.max_steps,
            "convergence_threshold": self.convergence_threshold,
        }

        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False)

        logger.info(f"Saved AgentConfig to {path}")

    @classmethod
    def with_defaults(cls) -> AgentConfig:
        """Create a new AgentConfig with sensible defaults.

        Returns:
            A new AgentConfig instance with default values.

        Example:
            >>> cfg = AgentConfig.with_defaults()
            >>> print(cfg.max_steps)
            100
        """
        return cls()


__all__ = ["AgentConfig"]
