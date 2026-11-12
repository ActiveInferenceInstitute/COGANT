"""Current GNN 2.0.0 schema declarations.

``CURRENT_GNN_VERSION`` (``"2.0.0"``) is COGANT's own schema identifier for the
section layout declared below. It is not an upstream GNN language version:
upstream's ``GNNVersionAndFlags`` schema patterns (``src/gnn/schemas/json.json``,
``xsd.xsd``, ``yaml.yaml`` at ``v5.1.0``) accept at most two numeric components,
e.g. ``GNN v1.1``, so a three-component ``2.0.0`` is not an upstream version.
"""

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
