"""Markov blanket data model and partitioning primitive.

This module defines the :class:`MarkovBlanket` dataclass and a pure-function
partitioning primitive, :func:`partition_by_seeds`, that assigns every node
of a :class:`~cogant.schemas.graph.ProgramGraph` to exactly one Active
Inference role: ``INTERNAL``, ``SENSORY``, ``ACTIVE``, or ``EXTERNAL``.

The implementation is deliberately graph-theoretic rather than heuristic:
given a seed set ``S`` (the "system of interest"), every non-seed node
is labelled by looking at its bidirectional adjacency with ``S``.
No language- or domain-specific knowledge is required, so the primitive
can be re-used for any repo translated by COGANT.

Partitioning rules (applied to the undirected projection of the graph):

* A node ``n ∈ S`` with no edge leaving ``S`` is **internal** (``μ``).
  Its only neighbours are other internal or boundary nodes in ``S``.
* A node ``n ∈ S`` with at least one neighbour outside ``S`` is a
  **boundary** node. We further split boundary nodes into **sensory**
  and **active** based on directed edge flow:
    * ``sensory``  — there exists a directed edge from an external
      node into ``n`` (information flowing IN).
    * ``active``   — there exists a directed edge from ``n`` to an
      external node (information flowing OUT).
    * A node that both reads and writes across the boundary is tagged
      as ``active`` by default (because it has causal influence
      outward) and reported as ``bidirectional`` in metadata.
* A node ``n ∉ S`` with at least one neighbour in ``S`` is part of the
  immediate external neighbourhood (``external`` with ``neighbour``
  metadata flag).
* All other nodes are **external** with no special flag.

The result is a complete, mutually-exclusive partition of the graph,
which is exactly what is required to populate the Markov blanket section
of the GNN export bundle. The function is deterministic: given the same
graph and seed set, it always produces the same partition.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from cogant.schemas.core import Node, NodeKind
from cogant.schemas.graph import ProgramGraph


class BlanketRole(StrEnum):
    """Active Inference role of a node within a Markov blanket."""

    INTERNAL = "internal"
    """μ — inside the system of interest with no external adjacency."""

    SENSORY = "sensory"
    """s — boundary node with incoming edges from external states."""

    ACTIVE = "active"
    """a — boundary node with outgoing edges to external states."""

    EXTERNAL = "external"
    """η — outside the system of interest."""


@dataclass
class MarkovBlanket:
    """Active-Inference Markov blanket partition of a program graph.

    Instances are usually produced by
    :meth:`MarkovBlanketExtractor.extract` or by the low-level
    :func:`partition_by_seeds` helper. The dataclass is intentionally
    serialization-friendly: ``serialize_blanket`` returns a dictionary
    suitable for JSON, parquet, or YAML output.

    Example:
        >>> from cogant.schemas.graph import ProgramGraph, GraphMetadata
        >>> from cogant.markov.blanket import partition_by_seeds
        >>> graph = ProgramGraph(metadata=GraphMetadata(repo_uri="demo"))
        >>> blanket = partition_by_seeds(graph, seeds=set())
        >>> isinstance(blanket, MarkovBlanket)
        True
        >>> blanket.boundary_ids
        set()

    Attributes:
        roles: Mapping of node id → :class:`BlanketRole`.
        seeds: The seed set supplied to the partitioner.
        internal_ids: Convenience accessor for μ nodes.
        sensory_ids: Convenience accessor for s nodes.
        active_ids: Convenience accessor for a nodes.
        external_ids: Convenience accessor for η nodes.
        boundary_ids: Union of sensory and active (the blanket B).
        rationale: Per-node short string explaining *why* the role was
            assigned (e.g. ``"internal; neighbours all in seed set"``).
            Populated by :func:`partition_by_seeds`.
        stats: Counts and coverage ratios, convenient for reports.
        metadata: Free-form extra information (strategy used, seed
            heuristic, graph hash, etc.).
    """

    roles: dict[str, BlanketRole]
    seeds: set[str]
    internal_ids: set[str] = field(default_factory=set)
    sensory_ids: set[str] = field(default_factory=set)
    active_ids: set[str] = field(default_factory=set)
    external_ids: set[str] = field(default_factory=set)
    rationale: dict[str, str] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def boundary_ids(self) -> set[str]:
        """Union of sensory and active nodes — the Markov blanket B."""
        return self.sensory_ids | self.active_ids

    def role_of(self, node_id: str) -> BlanketRole:
        """Return the role of ``node_id``, defaulting to EXTERNAL."""
        return self.roles.get(node_id, BlanketRole.EXTERNAL)

    def ids_by_role(self, role: BlanketRole) -> set[str]:
        """Return the set of node ids that carry a given role."""
        if role is BlanketRole.INTERNAL:
            return self.internal_ids
        if role is BlanketRole.SENSORY:
            return self.sensory_ids
        if role is BlanketRole.ACTIVE:
            return self.active_ids
        return self.external_ids


def _bidirectional_adjacency(
    graph: ProgramGraph,
) -> dict[str, tuple[set[str], set[str]]]:
    """Build in/out neighbour sets for every node.

    Returns a mapping ``node_id → (in_neighbours, out_neighbours)``
    where ``in_neighbours`` are all sources of edges pointing AT the node
    and ``out_neighbours`` are the targets of edges leaving the node.
    Self-loops are excluded from both sets.

    We precompute this once so the partitioner is O(V + E) rather than
    O(V²) through repeated calls to :meth:`ProgramGraph.get_edges_from`.
    """
    in_adj: dict[str, set[str]] = {n: set() for n in graph.nodes}
    out_adj: dict[str, set[str]] = {n: set() for n in graph.nodes}

    for edge in graph.edges.values():
        s, t = edge.source_id, edge.target_id
        if s == t:
            continue
        if s in out_adj:
            out_adj[s].add(t)
        if t in in_adj:
            in_adj[t].add(s)

    return {node_id: (in_adj[node_id], out_adj[node_id]) for node_id in graph.nodes}


def partition_by_seeds(
    graph: ProgramGraph,
    seeds: Iterable[str],
    *,
    adjacency: Mapping[str, tuple[set[str], set[str]]] | None = None,
) -> MarkovBlanket:
    """Assign every node in ``graph`` a Markov blanket role.

    Args:
        graph: The program graph to partition.
        seeds: Iterable of node ids that define the "system of interest".
            Nodes NOT in this set are considered environmental.
        adjacency: Optional precomputed ``{id: (in_set, out_set)}`` map
            to avoid rebuilding if the caller already has one.

    Returns:
        A fully populated :class:`MarkovBlanket`. Every node id in the
        graph will appear exactly once across ``internal_ids``,
        ``sensory_ids``, ``active_ids``, and ``external_ids``.

    The partitioning rule is purely topological:

    .. code-block:: text

        node ∈ seeds  and  all neighbours ∈ seeds         → INTERNAL
        node ∈ seeds  and  ∃ external neighbour           → SENSORY/ACTIVE
        node ∉ seeds                                       → EXTERNAL

    Example:
        >>> from cogant.schemas.graph import ProgramGraph, GraphMetadata
        >>> graph = ProgramGraph(metadata=GraphMetadata(repo_uri="demo"))
        >>> blanket = partition_by_seeds(graph, seeds=[])
        >>> blanket.stats["total_nodes"]
        0
    """
    seed_set: set[str] = {s for s in seeds if s in graph.nodes}

    if adjacency is None:
        adjacency = _bidirectional_adjacency(graph)

    roles: dict[str, BlanketRole] = {}
    rationale: dict[str, str] = {}
    internal: set[str] = set()
    sensory: set[str] = set()
    active: set[str] = set()
    external: set[str] = set()
    bidirectional: set[str] = set()
    external_neighbours: set[str] = set()

    for node_id in graph.nodes:
        in_neigh, out_neigh = adjacency[node_id]
        neigh = in_neigh | out_neigh

        if node_id in seed_set:
            ext_in = {n for n in in_neigh if n not in seed_set}
            ext_out = {n for n in out_neigh if n not in seed_set}

            if not (ext_in or ext_out):
                roles[node_id] = BlanketRole.INTERNAL
                rationale[node_id] = "internal: all neighbours inside seed set"
                internal.add(node_id)
                continue

            if ext_out and ext_in:
                roles[node_id] = BlanketRole.ACTIVE
                rationale[node_id] = (
                    "active (bidirectional): edges flow in and out of the system"
                )
                active.add(node_id)
                bidirectional.add(node_id)
            elif ext_out:
                roles[node_id] = BlanketRole.ACTIVE
                rationale[node_id] = "active: writes/calls reach external states"
                active.add(node_id)
            else:
                roles[node_id] = BlanketRole.SENSORY
                rationale[node_id] = "sensory: reads/observes external states"
                sensory.add(node_id)
        else:
            roles[node_id] = BlanketRole.EXTERNAL
            if neigh & seed_set:
                rationale[node_id] = "external: immediate neighbour of the system"
                external_neighbours.add(node_id)
            else:
                rationale[node_id] = "external: no adjacency with the system"
            external.add(node_id)

    total = len(graph.nodes) or 1
    stats = {
        "total_nodes": len(graph.nodes),
        "seed_count": len(seed_set),
        "internal_count": len(internal),
        "sensory_count": len(sensory),
        "active_count": len(active),
        "external_count": len(external),
        "external_neighbour_count": len(external_neighbours),
        "bidirectional_count": len(bidirectional),
        "internal_ratio": round(len(internal) / total, 4),
        "boundary_ratio": round((len(sensory) + len(active)) / total, 4),
        "external_ratio": round(len(external) / total, 4),
    }

    blanket = MarkovBlanket(
        roles=roles,
        seeds=seed_set,
        internal_ids=internal,
        sensory_ids=sensory,
        active_ids=active,
        external_ids=external,
        rationale=rationale,
        stats=stats,
        metadata={
            "bidirectional_ids": sorted(bidirectional),
            "external_neighbour_ids": sorted(external_neighbours),
        },
    )
    return blanket


def _node_kind_value(node: Node) -> str:
    kind = node.kind
    return kind.value if isinstance(kind, NodeKind) else str(kind)


def serialize_blanket(
    blanket: MarkovBlanket,
    graph: ProgramGraph,
    *,
    include_rationale: bool = True,
    max_nodes_per_role: int | None = None,
) -> dict[str, Any]:
    """Convert a :class:`MarkovBlanket` into a JSON-friendly dictionary.

    Args:
        blanket: The partition to serialize.
        graph: The graph used to produce the partition. Needed so that
            each node id can be enriched with its human-readable
            ``kind``, ``name``, and ``path`` for downstream reports.
        include_rationale: Whether to include the per-node rationale
            string. Defaults to ``True``; set ``False`` if the caller
            wants a more compact file.
        max_nodes_per_role: Optional cap on how many nodes to emit per
            role (useful for very large graphs). Capping is applied
            deterministically by sorting node ids first.

    Returns:
        A dict with the schema::

            {
              "schema_version": "1.0.0",
              "seeds": [...],
              "stats": {...},
              "roles": {
                  "internal": [{id, kind, name, path, rationale?}, ...],
                  "sensory":  [...],
                  "active":   [...],
                  "external": [...],
              },
              "metadata": {...}
            }

    Example:
        >>> from cogant.schemas.graph import ProgramGraph, GraphMetadata
        >>> graph = ProgramGraph(metadata=GraphMetadata(repo_uri="demo"))
        >>> blanket = partition_by_seeds(graph, seeds=[])
        >>> doc = serialize_blanket(blanket, graph)
        >>> doc["schema_version"]
        '1.0.0'
        >>> sorted(doc["roles"].keys())
        ['active', 'external', 'internal', 'sensory']
    """

    def _format(node_ids: Iterable[str]) -> list[dict[str, Any]]:
        ids = sorted(node_ids)
        if max_nodes_per_role is not None:
            ids = ids[:max_nodes_per_role]
        out: list[dict[str, Any]] = []
        for nid in ids:
            node = graph.get_node(nid)
            record: dict[str, Any] = {
                "id": nid,
                "kind": _node_kind_value(node) if node else None,
                "name": node.name if node else None,
                "path": node.path if node else None,
            }
            if include_rationale and nid in blanket.rationale:
                record["rationale"] = blanket.rationale[nid]
            out.append(record)
        return out

    return {
        "schema_version": "1.0.0",
        "seeds": sorted(blanket.seeds),
        "stats": dict(blanket.stats),
        "roles": {
            BlanketRole.INTERNAL.value: _format(blanket.internal_ids),
            BlanketRole.SENSORY.value: _format(blanket.sensory_ids),
            BlanketRole.ACTIVE.value: _format(blanket.active_ids),
            BlanketRole.EXTERNAL.value: _format(blanket.external_ids),
        },
        "metadata": dict(blanket.metadata),
    }
