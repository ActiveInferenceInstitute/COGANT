"""Current GNN 2.0.0 schema declarations."""

CURRENT_GNN_VERSION = "2.0.0"
UNSUPPORTED_GNN_VERSION = "unsupported"

GNN_V2_REQUIRED_SECTIONS: list[str] = [
    "GNNSection",
    "GNNVersionAndFlags",
    "ModelName",
    "StateSpaceBlock",
    "Connections",
    "InitialParameterization",
    "Equations",
    "Time",
    "ActInfOntologyAnnotation",
    "ModelParameters",
    "Footer",
    "Signature",
]

__all__ = ["CURRENT_GNN_VERSION", "UNSUPPORTED_GNN_VERSION", "GNN_V2_REQUIRED_SECTIONS"]
