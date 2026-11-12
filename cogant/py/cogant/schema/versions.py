"""Current GNN 2.0.0 schema declarations.

``CURRENT_GNN_VERSION`` (``"2.0.0"``) is COGANT's own schema identifier for the
section layout declared below; it is not the pinned upstream release version
(``v5.1.0``). The anchored ``GNNVersionAndFlags`` patterns upstream publishes at
that pin (``src/gnn/schemas/json.json`` and ``yaml.yaml``) tie the value to at
most two numeric components, e.g. ``GNN v1.1``, so neither accepts
``GNN v2.0.0``. That anchor is a property of those two schema files, not of GNN
versioning as a whole: upstream's ``src/gnn/grammars/bnf.bnf`` lists a
three-component ``<version_number>``, its syntax parser stores the
``GNNVersionAndFlags`` text verbatim, and its own
``docs/other/meta_livestream_consciousness.md`` example declares ``GNN v1.4.1``.
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
