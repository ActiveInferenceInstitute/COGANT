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

#: Payload fields stamped with the wall clock of a pipeline run. They
#: differ between two runs over identical source, so drift comparison
#: ignores them at every nesting level.
VOLATILE_PAYLOAD_KEYS: frozenset[str] = frozenset({"created_at", "updated_at", "timestamp"})


def stable_payload(value: Any) -> Any:
    """Return ``value`` with :data:`VOLATILE_PAYLOAD_KEYS` removed recursively.

    Dicts lose the volatile keys, lists and tuples are rebuilt
    element-wise, and every other value is returned unchanged. Used to
    compare two serialized payloads for real (non-timestamp) change.
    """
    if isinstance(value, dict):
        return {
            key: stable_payload(item)
            for key, item in value.items()
            if key not in VOLATILE_PAYLOAD_KEYS
        }
    if isinstance(value, list | tuple):
        return [stable_payload(item) for item in value]
    return value


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


#: Accepted section names per logical state-space collection, in lookup
#: order: the pydantic schema uses ``states``; ``model.gnn.json`` and
#: ``state_space.json`` use ``variables``.
STATE_SPACE_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "states": ("states", "variables"),
    "observations": ("observations",),
    "actions": ("actions",),
}

#: Primary-key fields per state-space collection, in lookup order.
STATE_SPACE_ID_KEYS: dict[str, tuple[str, ...]] = {
    "states": ("var_id", "id"),
    "observations": ("modality_id", "id"),
    "actions": ("action_id", "id"),
}


def state_space_index(state_space: Any, section: str) -> dict[str, dict[str, Any]]:
    """Index one state-space collection by its primary key.

    Accepts the pydantic schema shape (``states`` / ``observations`` /
    ``actions`` lists keyed by ``var_id`` / ``modality_id`` /
    ``action_id``) and the ``model.gnn.json`` shape (``variables`` /
    ``observations`` / ``actions`` dicts keyed by id).

    Args:
        state_space: The state-space dict (anything else yields ``{}``).
        section: ``"states"``, ``"observations"``, or ``"actions"``.

    Returns:
        ``{primary_key: payload}`` for the first section alias present.
        Payloads without a recognizable primary key are skipped.
    """
    if not isinstance(state_space, dict):
        return {}
    id_keys = STATE_SPACE_ID_KEYS[section]
    for alias in STATE_SPACE_SECTION_ALIASES[section]:
        if alias not in state_space:
            continue
        index: dict[str, dict[str, Any]] = {}
        for record in iter_records(state_space.get(alias), id_key=id_keys[0]):
            record_id = next((record[k] for k in id_keys if record.get(k)), None)
            if record_id is not None:
                index[str(record_id)] = record
        return index
    return {}


def edge_key(edge: dict[str, Any]) -> tuple[str | None, str | None, str]:
    """Return the identity of an edge payload as ``(source, target, kind)``.

    Endpoints plus kind identify a relationship in every bundle shape;
    edge ids are not used because hand-built bundles often omit them.
    """
    source, target = edge_endpoints(edge)
    return (source, target, str(edge.get("kind") or ""))
