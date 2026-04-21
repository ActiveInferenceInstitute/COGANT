"""Statespace stage configuration.

Controls how the state-space compiler builds, normalizes, and bounds
matrices for the Active Inference state-space model.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StatespaceConfig(BaseModel):
    """Configuration for the state-space compilation stage.

    Attributes:
        normalize_matrices: Whether to row-normalize transition /
            observation matrices after construction.
        matrix_tolerance: Numerical tolerance used when checking matrix
            properties (stochasticity, symmetry, etc.).
        max_hidden_states: Upper bound on hidden-state dimension.
        max_observations: Upper bound on observation dimension.
    """

    normalize_matrices: bool = Field(
        default=True,
        description="Row-normalize transition/observation matrices",
    )
    matrix_tolerance: float = Field(
        default=1e-6,
        gt=0.0,
        description="Numerical tolerance for matrix checks",
    )
    max_hidden_states: int = Field(default=512, ge=1, description="Maximum hidden-state dimension")
    max_observations: int = Field(default=2048, ge=1, description="Maximum observation dimension")

    model_config = ConfigDict(frozen=True)
