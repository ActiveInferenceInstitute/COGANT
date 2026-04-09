"""Behavioral translation rules.

This module is part of the :mod:`cogant.translate.rules` package and
contains rules that recognise behavioural patterns (orchestration, event buses, test assertions). Every class in this file inherits from
:class:`cogant.translate.engine.TranslationRule` and produces
:class:`cogant.schemas.semantic.SemanticMapping` records with full
provenance and confidence.

See :mod:`cogant.translate.rules` for the umbrella re-export and
:doc:`../../../specs/mappings/code-to-gnn` for the family taxonomy.
"""

import hashlib
from typing import Any, Dict, List, Optional

from cogant.schemas.core import NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import (
    SemanticMapping,
    MappingKind,
    ConfidenceTier,
    ProvenanceRecord,
)
from cogant.graph.queries import GraphQuery
from cogant.translate.engine import TranslationRule


class OrchestratorRule(TranslationRule):
    """Maps schedulers and controllers to policy/action structure."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find orchestrator patterns (high out-degree controllers).

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched orchestrator nodes.
        """
        matches = []

        # Look for functions/classes with high out-degree (calling many others)
        for node in graph.nodes.values():
            if node.kind not in (NodeKind.CLASS, NodeKind.FUNCTION, NodeKind.METHOD):
                continue

            out_edges = graph.get_edges_from(node.id)
            call_edges = [e for e in out_edges if e.kind == EdgeKind.CALLS]

            # Threshold: 3+ function calls indicates orchestration
            if len(call_edges) >= 3:
                matches.append({
                    "node_id": node.id,
                    "call_count": len(call_edges),
                    "called_node_ids": [e.target_id for e in call_edges],
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create orchestration mapping.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for orchestration.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"orch_{node_id}_{hashlib.sha256(b'orchestrator').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.ORCHESTRATION,
            graph_fragment_node_ids=[node_id] + match.get("called_node_ids", []),
            semantic_label=f"{node.name} - Orchestrator",
            description=f"{'Class' if node.kind == NodeKind.CLASS else 'Function'} '{node.name}' acts as orchestrator (high fan-out)",
            confidence_score=0.8,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.8,
                    metadata={"call_count": match["call_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.9,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "orchestrator"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.ORCHESTRATION


class TestAssertionRule(TranslationRule):
    """Maps test assertions to preference/constraint modality."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find test nodes and assertion calls.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched test nodes.
        """
        matches = []

        # Find test functions
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        for func in functions:
            # Check if test function (name contains "test")
            if "test" not in func.name.lower():
                continue

            # Find assertion calls
            out_edges = graph.get_edges_from(func.id)
            assertion_edges = [e for e in out_edges if e.kind == EdgeKind.CALLS]

            if assertion_edges:
                matches.append({
                    "node_id": func.id,
                    "assertion_count": len(assertion_edges),
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create constraint mapping from test assertions.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for constraint.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"const_{node_id}_{hashlib.sha256(b'test_assertion').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONSTRAINT,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Test Constraint",
            description=f"Test function '{node.name}' defines system constraints",
            confidence_score=0.85,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.85,
                    metadata={"assertion_count": match["assertion_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.95,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "test_assertion"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.CONSTRAINT


class EventBusRule(TranslationRule):
    """Maps event/subscription systems to observation-action coupling."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find event bus and subscription patterns.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched event bus patterns.
        """
        matches = []

        # Look for event nodes and their subscriptions
        events = graph.get_nodes_by_kind(NodeKind.EVENT)

        for event in events:
            # Find subscribing nodes
            incoming = graph.get_edges_to(event.id)
            outgoing = graph.get_edges_from(event.id)

            if incoming or outgoing:
                matches.append({
                    "node_id": event.id,
                    "subscriber_count": len([e for e in outgoing if e.kind == EdgeKind.TRIGGERS]),
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create observation-action coupling mapping.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for event bus.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"event_{node_id}_{hashlib.sha256(b'event_bus').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Event Bus",
            description=f"Event '{node.name}' couples observations to actions",
            confidence_score=0.75,
            confidence_tier=ConfidenceTier.STATIC_PLUS_RUNTIME,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.75,
                )
            ],
            evidence_count=1,
            parser_certainty=0.8,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "event_bus"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.OBSERVATION
