"""Reduced network representations derived from a Markov blanket.

A :class:`~cogant.markov.blanket.MarkovBlanket` tells us the role of every
node in the graph, but consumers of COGANT (Active Inference modellers,
architecture reviewers, diff tools) usually want a **reduced** network
that collapses the full program graph to the canonical four-node
Active Inference schematic:

.. code-block:: text

        ┌──────┐        ┌──────┐
        │  η   │◀──────▶│  s   │──────┐
        └──────┘        └──────┘      ▼
                                    ┌──────┐
                                    │  μ   │
                                    └──────┘
        ┌──────┐        ┌──────┐      ▲
        │  η   │◀──────│  a   │──────┘
        └──────┘        └──────┘

:func:`build_blanket_network` walks the original program graph and
produces:

* **Aggregate edges** between the four roles (η→s, s→μ, μ→a, a→η)
  with counts and per-:class:`~cogant.schemas.core.EdgeKind` breakdowns.
* **Role bags** listing which concrete nodes are behind each aggregate
  vertex, so the reduced view is always traceable to the full graph.

The result is serializable to JSON, Mermaid, and Cytoscape formats so
that the bundle can render the Markov blanket as a diagram or load it
into a network analysis tool without a second traversal.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from cogant.markov.blanket import BlanketRole, MarkovBlanket
from cogant.schemas.core import EdgeKind
from cogant.schemas.graph import ProgramGraph


@dataclass
class BlanketNetwork:
    """Collapsed four-node Active Inference network view of a blanket.

    Example:
        >>> from cogant.schemas.graph import ProgramGraph, GraphMetadata
        >>> from cogant.markov.blanket import partition_by_seeds
        >>> graph = ProgramGraph(metadata=GraphMetadata(repo_uri="demo"))
        >>> blanket = partition_by_seeds(graph, seeds=[])
        >>> net = build_blanket_network(graph, blanket)
        >>> isinstance(net, BlanketNetwork)
        True
        >>> "graph LR" in net.to_mermaid()
        True
    """

    role_counts: dict[str, int]
    """Number of concrete nodes per role (``internal``, ``sensory``, …)."""

    role_members: dict[str, list[str]]
    """Node ids per role, sorted."""

    aggregate_edges: dict[tuple[str, str], int]
    """Dict of ``(from_role, to_role) → edge count``."""

    edge_kind_breakdown: dict[tuple[str, str], dict[str, int]]
    """Same shape as ``aggregate_edges`` but bucketed by ``EdgeKind``."""

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the network as a JSON-friendly dictionary."""
        return {
            "role_counts": dict(self.role_counts),
            "role_members": {k: list(v) for k, v in self.role_members.items()},
            "aggregate_edges": [
                {"from": a, "to": b, "count": c}
                for (a, b), c in sorted(self.aggregate_edges.items())
            ],
            "edge_kind_breakdown": [
                {"from": a, "to": b, "kinds": dict(sorted(d.items()))}
                for (a, b), d in sorted(self.edge_kind_breakdown.items())
            ],
            "metadata": dict(self.metadata),
        }

    def to_mermaid(self) -> str:
        """Render the collapsed view as a Mermaid ``graph LR`` block.

        The four roles are drawn with bracketed labels summarising the
        node count in that role. Aggregate edges are labelled with the
        number of underlying concrete edges.
        """
        lines = ["graph LR"]
        label = {
            "internal": f"μ internal [{self.role_counts.get('internal', 0)}]",
            "sensory":  f"s sensory [{self.role_counts.get('sensory', 0)}]",
            "active":   f"a active [{self.role_counts.get('active', 0)}]",
            "external": f"η external [{self.role_counts.get('external', 0)}]",
        }
        for key, text in label.items():
            lines.append(f"    {key}[\"{text}\"]")
        for (src, dst), count in sorted(self.aggregate_edges.items()):
            if count > 0:
                lines.append(f"    {src} -->|{count}| {dst}")
        return "\n".join(lines)


def build_blanket_network(
    graph: ProgramGraph, blanket: MarkovBlanket
) -> BlanketNetwork:
    """Collapse ``graph`` into a four-role aggregate network.

    Every concrete edge in ``graph`` is mapped to a pair
    ``(role_of_source, role_of_target)`` and counted. Edges are also
    bucketed by :class:`EdgeKind` so that downstream tooling can see,
    e.g., how many of the s→μ edges are ``READS`` vs ``CALLS``.

    Args:
        graph: The program graph used to build ``blanket``.
        blanket: The Markov blanket partition.

    Returns:
        A :class:`BlanketNetwork` summarising the collapsed view.

    Example:
        >>> from cogant.schemas.graph import ProgramGraph, GraphMetadata
        >>> from cogant.markov.blanket import partition_by_seeds
        >>> graph = ProgramGraph(metadata=GraphMetadata(repo_uri="demo"))
        >>> blanket = partition_by_seeds(graph, seeds=[])
        >>> network = build_blanket_network(graph, blanket)
        >>> sorted(network.role_counts.keys())
        ['active', 'external', 'internal', 'sensory']
    """
    aggregate: dict[tuple[str, str], int] = defaultdict(int)
    kind_break: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def _role_name(node_id: str) -> str:
        return blanket.role_of(node_id).value

    for edge in graph.edges.values():
        src_role = _role_name(edge.source_id)
        dst_role = _role_name(edge.target_id)
        key = (src_role, dst_role)
        aggregate[key] += 1
        kind_value = (
            edge.kind.value if isinstance(edge.kind, EdgeKind) else str(edge.kind)
        )
        kind_break[key][kind_value] += 1

    # Freeze inner defaultdicts so json.dumps doesn't serialize a factory.
    edge_kind_breakdown = {k: dict(v) for k, v in kind_break.items()}

    role_members = {
        BlanketRole.INTERNAL.value: sorted(blanket.internal_ids),
        BlanketRole.SENSORY.value: sorted(blanket.sensory_ids),
        BlanketRole.ACTIVE.value: sorted(blanket.active_ids),
        BlanketRole.EXTERNAL.value: sorted(blanket.external_ids),
    }
    role_counts = {k: len(v) for k, v in role_members.items()}

    network = BlanketNetwork(
        role_counts=role_counts,
        role_members=role_members,
        aggregate_edges=dict(aggregate),
        edge_kind_breakdown=edge_kind_breakdown,
        metadata={
            "edge_count": len(graph.edges),
            "node_count": len(graph.nodes),
            "seed_count": len(blanket.seeds),
        },
    )
    return network
