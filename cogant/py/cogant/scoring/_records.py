"""Shape normalization shared by the scoring analyzers.

COGANT persists the same logical collections in more than one JSON
shape, and the scorers must read all of them:

* ``program_graph.json`` (written by
  :func:`cogant.api.orchestration.program_graph_to_dict`) stores
  ``nodes`` and ``edges`` as dicts keyed by id, and each edge payload
  names its endpoints ``source_id`` / ``target_id``.
* Hand-built and legacy fixture bundles use lists of payloads and name
  edge endpoints ``source`` / ``target``.

The helpers here reduce every shape to a list of payload dicts, so the
analyzers never iterate dict keys by accident.
"""

from __future__ import annotations

from typing import Any


def iter_records(collection: Any, id_key: str = "id") -> list[dict[str, Any]]:
    """Normalize a list- or dict-shaped collection to a list of payload dicts.

    Args:
        collection: A list of payload dicts, a dict mapping ids to
            payload dicts, or anything else (``None``, scalars).
        id_key: Field that receives the dict key when a dict-shaped
            payload omits it, so id-based diffs keep working.

    Returns:
        The payload dicts in collection order. Non-dict entries are
        dropped so callers can use ``.get`` safely.
    """
    if isinstance(collection, dict):
        normalized: list[dict[str, Any]] = []
        for key, value in collection.items():
            if isinstance(value, dict):
                if id_key not in value:
                    value = {**value, id_key: key}
                normalized.append(value)
        return normalized
    if isinstance(collection, list):
        return [item for item in collection if isinstance(item, dict)]
    return []


def edge_endpoints(edge: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return ``(source, target)`` ids for a serialized edge payload.

    Reads the canonical ``source_id`` / ``target_id`` fields and falls
    back to the legacy ``source`` / ``target`` names. Empty values are
    returned as ``None``.
    """
    source = edge.get("source_id") or edge.get("source")
    target = edge.get("target_id") or edge.get("target")
    return (str(source) if source else None, str(target) if target else None)


def edge_key(edge: dict[str, Any]) -> tuple[str | None, str | None, str]:
    """Return the identity of an edge payload as ``(source, target, kind)``.

    Endpoints plus kind identify a relationship in every bundle shape;
    edge ids are not used because hand-built bundles often omit them.
    """
    source, target = edge_endpoints(edge)
    return (source, target, str(edge.get("kind") or ""))
