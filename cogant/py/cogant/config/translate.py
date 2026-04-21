"""Translate stage configuration.

Controls the rule-driven translation from a normalized program graph
into an Active Inference / GNN representation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TranslateConfig(BaseModel):
    """Configuration for the translate stage.

    Attributes:
        max_iterations: Maximum passes the translator will make over the
            graph before stopping.
        confidence_threshold: Minimum per-rule confidence required for
            a translation to be accepted.
        enable_rules: Explicit allow-list of rule names. An empty list
            means "enable every rule".
        disable_rules: Explicit deny-list of rule names, evaluated after
            ``enable_rules``.
    """

    max_iterations: int = Field(default=10, ge=1, description="Maximum translation iterations")
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum per-rule confidence",
    )
    enable_rules: list[str] = Field(
        default_factory=list,
        description="Rule allow-list (empty = all rules)",
    )
    disable_rules: list[str] = Field(
        default_factory=list,
        description="Rule deny-list, applied after enable_rules",
    )

    model_config = ConfigDict(frozen=True)
