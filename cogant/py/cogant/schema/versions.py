"""Current GNN 2.0.0 schema declarations.

``CURRENT_GNN_VERSION`` is COGANT's own schema identifier, not an upstream
``generalized-notation-notation`` language version.  Upstream's
``GNNVersionAndFlags`` version pattern accepts at most two numeric components,
so ``"2.0.0"`` cannot be represented as an upstream version at all.  COGANT
markdown documents therefore declare it as a dialect: ``GNN v2.0.0`` under
``## GNNVersionAndFlags`` plus an explanatory comment, and are validated
against the upstream *section* contract rather than its version pattern.
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
