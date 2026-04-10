"""Reverse (GNN -> code) stage configuration.

Controls the reverse-direction pipeline that synthesizes code from a
GNN specification.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReverseConfig(BaseModel):
    """Configuration for the reverse synthesis stage.

    Attributes:
        synthesis_strategy: ``"minimal"`` emits only the scaffolding
            needed to satisfy role bindings; ``"full"`` emits a complete
            executable module.
        include_tests: Whether to synthesize a companion test suite.
        role_threshold: Minimum per-role confidence required before a
            variable is bound during synthesis.
    """

    synthesis_strategy: Literal["minimal", "full"] = Field(
        default="minimal", description="Synthesis strategy"
    )
    include_tests: bool = Field(
        default=False, description="Synthesize a companion test suite"
    )
    role_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum role-binding confidence",
    )

    model_config = ConfigDict(frozen=True)
