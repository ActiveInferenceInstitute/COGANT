"""Detect whether a GNN markdown text declares the current 2.0.0 contract."""

import re

from cogant.schema.versions import CURRENT_GNN_VERSION, UNSUPPORTED_GNN_VERSION

_VERSION_AND_FLAGS_RE = re.compile(r"^##\s+GNNVersionAndFlags\b", re.MULTILINE)
_GNN_V2_MARKER_RE = re.compile(r"\bGNN\s+v2\.0\.0\b", re.MULTILINE)


def detect_version(gnn_text: str) -> str:
    """Return ``2.0.0`` for current GNN markdown, otherwise ``unsupported``.

    Parameters
    ----------
    gnn_text:
        Raw GNN markdown content.

    Returns
    -------
    str
        The current GNN version string or ``unsupported``.
    """
    try:
        if _VERSION_AND_FLAGS_RE.search(gnn_text) and _GNN_V2_MARKER_RE.search(gnn_text):
            return CURRENT_GNN_VERSION
    except Exception:  # noqa: BLE001 — never raise
        pass
    return UNSUPPORTED_GNN_VERSION
