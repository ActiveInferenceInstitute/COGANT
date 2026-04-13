"""Detect the schema version of a GNN markdown text.

The detector never raises -- it falls back to V1_0 when the version
cannot be determined.
"""

import re

from cogant.schema.versions import SchemaVersion

_VERSION_AND_FLAGS_RE = re.compile(
    r"^##\s+GNNVersionAndFlags\b", re.MULTILINE
)
_GNN_V1_MARKER_RE = re.compile(
    r"GNN\s+v1\b", re.MULTILINE
)


def detect_version(gnn_text: str) -> str:
    """Return the schema version string for *gnn_text*.

    Detection logic:
    - If a ``## GNNVersionAndFlags`` section exists **and** contains
      the marker ``GNN v1``, the text is classified as v1.1.
    - Otherwise, falls back to v1.0.

    Parameters
    ----------
    gnn_text:
        Raw GNN markdown content.

    Returns
    -------
    str
        One of :attr:`SchemaVersion.V1_0` or :attr:`SchemaVersion.V1_1`.
    """
    try:
        if _VERSION_AND_FLAGS_RE.search(gnn_text) and _GNN_V1_MARKER_RE.search(gnn_text):
            return SchemaVersion.V1_1
    except Exception:  # noqa: BLE001 — never raise
        pass
    return SchemaVersion.V1_0
