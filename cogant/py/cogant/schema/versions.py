"""Canonical schema version declarations for the GNN format.

Each version defines the set of required markdown sections that a
conforming GNN file must contain.
"""


class SchemaVersion:
    """Known GNN schema versions."""

    V1_0 = "1.0"
    V1_1 = "1.1"
    CURRENT = "1.1"


GNN_V1_0_REQUIRED_SECTIONS: list[str] = [
    "GNNSection",
    "ModelName",
    "StateSpaceBlock",
    "ActInfOntologyAnnotation",
]

GNN_V1_1_REQUIRED_SECTIONS: list[str] = [
    # v1.1 adds GNNVersionAndFlags as required
    *GNN_V1_0_REQUIRED_SECTIONS,
    "GNNVersionAndFlags",
]
