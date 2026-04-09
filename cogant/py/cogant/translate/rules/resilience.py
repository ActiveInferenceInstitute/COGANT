"""Resilience translation rules.

This module is part of the :mod:`cogant.translate.rules` package and
contains rules that recognise resilience and uncertainty patterns (retry, error boundary, singleton, circuit breaker). Every class in this file inherits from
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


class RetryPatternRule(TranslationRule):
    """Maps retry/backoff/circuit breaker patterns to policy under uncertainty."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find retry and circuit breaker patterns.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched pattern nodes.
        """
        matches = []

        # Look for functions/methods with retry/circuit breaker keywords
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        functions.extend(graph.get_nodes_by_kind(NodeKind.METHOD))

        retry_keywords = ["retry", "backoff", "circuit", "breaker", "timeout", "fallback"]

        for func in functions:
            name_lower = func.name.lower()
            if any(keyword in name_lower for keyword in retry_keywords):
                matches.append({
                    "node_id": func.id,
                    "pattern_type": "retry_or_circuit_breaker",
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create policy mapping for retry pattern.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for policy.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"policy_{node_id}_{hashlib.sha256(b'retry_pattern').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.POLICY,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Retry Policy",
            description=f"Function '{node.name}' implements retry/circuit breaker policy",
            confidence_score=0.7,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.7,
                )
            ],
            evidence_count=1,
            parser_certainty=0.7,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "retry_pattern"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.POLICY


class ErrorBoundaryRule(TranslationRule):
    """Maps error handling boundaries to error-handling modality.

    Detects functions/methods with CATCHES or THROWS edges, representing
    error boundaries in the system.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find nodes with CATCHES or THROWS edges.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched error boundary nodes.
        """
        matches = []

        # Find functions and methods
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        methods = graph.get_nodes_by_kind(NodeKind.METHOD)

        for node in functions + methods:
            out_edges = graph.get_edges_from(node.id)

            catches_edges = [e for e in out_edges if e.kind == EdgeKind.CATCHES]
            throws_edges = [e for e in out_edges if e.kind == EdgeKind.THROWS]

            if not catches_edges and not throws_edges:
                continue

            # Caught exception node IDs form the graph fragment
            caught_node_ids = [e.target_id for e in catches_edges]
            thrown_node_ids = [e.target_id for e in throws_edges]

            matches.append({
                "node_id": node.id,
                "caught_node_ids": caught_node_ids,
                "thrown_node_ids": thrown_node_ids,
                "catches_count": len(catches_edges),
                "throws_count": len(throws_edges),
            })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create error-handling mapping for error boundary node.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for error handling.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        fragment_node_ids = (
            [node_id]
            + match.get("caught_node_ids", [])
            + match.get("thrown_node_ids", [])
        )

        mapping_id = f"errbnd_{node_id}_{hashlib.sha256(b'error_boundary').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.ERROR_HANDLING,
            graph_fragment_node_ids=fragment_node_ids,
            semantic_label=f"{node.name} - Error Boundary",
            description=f"Function '{node.name}' handles errors (catches {match['catches_count']}, throws {match['throws_count']})",
            confidence_score=0.70,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.70,
                    metadata={
                        "catches_count": match["catches_count"],
                        "throws_count": match["throws_count"],
                    },
                )
            ],
            evidence_count=1,
            parser_certainty=0.75,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "error_boundary"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.ERROR_HANDLING


class SingletonAccessRule(TranslationRule):
    """Maps singleton/global state access to context modality.

    Detects variables or classes that are read by many different modules
    (high in-degree of READS edges from diverse paths). Threshold: 3+ readers
    from different modules.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find nodes with high in-degree READS from diverse modules.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched singleton/global state nodes.
        """
        matches = []

        # Check variables and classes as potential singletons
        variables = graph.get_nodes_by_kind(NodeKind.VARIABLE)
        classes = graph.get_nodes_by_kind(NodeKind.CLASS)

        for node in variables + classes:
            # Find incoming READS edges
            incoming = graph.get_edges_to(node.id)
            read_edges = [e for e in incoming if e.kind == EdgeKind.READS]

            if len(read_edges) < 3:
                continue

            # Check diversity: count unique module paths among readers
            reader_modules = set()
            reader_ids = []
            for edge in read_edges:
                reader = graph.get_node(edge.source_id)
                if reader and reader.path:
                    # Extract module path (directory portion)
                    parts = reader.path.rsplit("/", 1)
                    module_path = parts[0] if len(parts) > 1 else reader.path
                    reader_modules.add(module_path)
                reader_ids.append(edge.source_id)

            # Threshold: 3+ readers from different modules
            if len(reader_modules) >= 3:
                matches.append({
                    "node_id": node.id,
                    "reader_ids": reader_ids,
                    "reader_count": len(read_edges),
                    "module_count": len(reader_modules),
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create context mapping for singleton/global state node.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for context.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"single_{node_id}_{hashlib.sha256(b'singleton_access').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONTEXT,
            graph_fragment_node_ids=[node_id] + match.get("reader_ids", []),
            semantic_label=f"{node.name} - Singleton/Global State",
            description=f"{'Variable' if node.kind == NodeKind.VARIABLE else 'Class'} '{node.name}' is accessed by {match['reader_count']} readers across {match['module_count']} modules",
            confidence_score=0.65,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.65,
                    metadata={
                        "reader_count": match["reader_count"],
                        "module_count": match["module_count"],
                    },
                )
            ],
            evidence_count=1,
            parser_certainty=0.7,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "singleton_access"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.CONTEXT


class CircuitBreakerRule(TranslationRule):
    """Maps circuit breaker patterns to circuit-breaker modality.

    Detects functions/classes that contain both a GUARDS edge and a
    retry/fallback pattern (name contains retry/fallback/circuit/breaker
    keywords or has metadata indicating retry logic).
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find nodes with GUARDS edges and retry/fallback indicators.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched circuit breaker nodes.
        """
        matches = []

        circuit_keywords = ["retry", "fallback", "circuit", "breaker"]

        # Find functions, methods, and classes
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        methods = graph.get_nodes_by_kind(NodeKind.METHOD)
        classes = graph.get_nodes_by_kind(NodeKind.CLASS)

        for node in functions + methods + classes:
            out_edges = graph.get_edges_from(node.id)

            # Must have at least one GUARDS edge
            guards_edges = [e for e in out_edges if e.kind == EdgeKind.GUARDS]
            if not guards_edges:
                continue

            # Check for retry/fallback pattern via name or metadata
            name_lower = node.name.lower()
            has_keyword = any(kw in name_lower for kw in circuit_keywords)

            has_retry_metadata = False
            if node.metadata:
                meta_str = str(node.metadata).lower()
                has_retry_metadata = any(kw in meta_str for kw in circuit_keywords)

            if has_keyword or has_retry_metadata:
                guarded_ids = [e.target_id for e in guards_edges]
                matches.append({
                    "node_id": node.id,
                    "guarded_ids": guarded_ids,
                    "guards_count": len(guards_edges),
                    "keyword_match": has_keyword,
                    "metadata_match": has_retry_metadata,
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create circuit-breaker mapping.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for circuit breaker.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"cb_{node_id}_{hashlib.sha256(b'circuit_breaker').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CIRCUIT_BREAKER,
            graph_fragment_node_ids=[node_id] + match.get("guarded_ids", []),
            semantic_label=f"{node.name} - Circuit Breaker",
            description=f"{'Function' if node.kind in (NodeKind.FUNCTION, NodeKind.METHOD) else 'Class'} '{node.name}' implements circuit breaker pattern (guards {match['guards_count']} target(s))",
            confidence_score=0.80,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.80,
                    metadata={
                        "guards_count": match["guards_count"],
                        "keyword_match": match["keyword_match"],
                        "metadata_match": match["metadata_match"],
                    },
                )
            ],
            evidence_count=1,
            parser_certainty=0.85,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "circuit_breaker"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.CIRCUIT_BREAKER
