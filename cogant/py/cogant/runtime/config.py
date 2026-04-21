"""Agent configuration for the Active Inference runtime.

Uses a plain dataclass rather than pydantic to maintain the zero-dependency
constraint of the runtime package.
"""

from __future__ import annotations

import logging
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

    def __post_init__(self) -> None:
        """Validate configuration after initialization.

        Raises:
            ValueError: If any configuration value is invalid.
        """
        if self.max_steps < 0:
            raise ValueError(f"max_steps must be non-negative; got {self.max_steps}")

        if not (0 < self.convergence_threshold < 1):
            raise ValueError(
                f"convergence_threshold must be in (0, 1); got {self.convergence_threshold}"
            )

        if self.action_selection not in ("preference", "entropy"):
            logger.warning(
                f"Unknown action_selection strategy: {self.action_selection}; "
                f"will fall back to 'preference'"
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
            data = yaml.safe_load(f) or {}

        return cls(
            max_steps=data.get("max_steps", 100),
            convergence_threshold=data.get("convergence_threshold", 1e-4),
            action_selection=data.get("action_selection", "preference"),
            seed=data.get("seed", 42),
        )

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
            "action_selection": self.action_selection,
            "seed": self.seed,
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
