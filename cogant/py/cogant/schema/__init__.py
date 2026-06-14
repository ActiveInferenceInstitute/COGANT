"""Current GNN 2.0.0 schema detection and section declarations."""

from cogant.schema.detector import detect_version
from cogant.schema.versions import (
    CURRENT_GNN_VERSION,
    GNN_V2_REQUIRED_SECTIONS,
    UNSUPPORTED_GNN_VERSION,
)

__all__ = [
    "CURRENT_GNN_VERSION",
    "UNSUPPORTED_GNN_VERSION",
    "GNN_V2_REQUIRED_SECTIONS",
    "detect_version",
]
