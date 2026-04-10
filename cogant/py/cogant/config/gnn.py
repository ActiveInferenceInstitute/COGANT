"""GNN export configuration.

Controls how an Active Inference state-space model is serialized into
a GNN (Generalized Notation Notation) specification.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GNNConfig(BaseModel):
    """Configuration for the GNN export stage.

    Attributes:
        include_metadata: Emit the ``ModelMetadata`` section.
        include_connections: Emit the ``Connections`` section.
        include_matrices: Emit the matrix parameter blocks (A, B, C, D).
        matrix_format: How matrices are serialized — ``"dense"`` writes
            out every entry; ``"sparse"`` writes only non-zero entries.
    """

    include_metadata: bool = Field(
        default=True, description="Emit ModelMetadata section"
    )
    include_connections: bool = Field(
        default=True, description="Emit Connections section"
    )
    include_matrices: bool = Field(
        default=True, description="Emit A/B/C/D matrix blocks"
    )
    matrix_format: Literal["dense", "sparse"] = Field(
        default="dense", description="Matrix serialization format"
    )

    model_config = ConfigDict(frozen=True)
