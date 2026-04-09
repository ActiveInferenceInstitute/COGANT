"""Control translation rules.

This module is part of the :mod:`cogant.translate.rules` package and
contains rules that recognise control-flow modifiers (configuration, feature flags). Every class in this file inherits from
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


class ConfigRule(TranslationRule):
    """Maps configuration files and structures to context priors."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find configuration nodes.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched configuration nodes.
        """
        matches = []

        # Find configuration nodes
        configs = graph.get_nodes_by_kind(NodeKind.CONFIGURATION)

        for config in configs:
            matches.append({
                "node_id": config.id,
            })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create context mapping for configuration.

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

        mapping_id = f"ctx_{node_id}_{hashlib.sha256(b'config').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONTEXT,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Context Prior",
            description=f"Configuration '{node.name}' provides system context",
            confidence_score=0.9,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.9,
                )
            ],
            evidence_count=1,
            parser_certainty=0.95,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "config"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.CONTEXT


class FeatureFlagRule(TranslationRule):
    """Maps feature flags to latent context selectors."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find feature flag nodes.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched feature flag nodes.
        """
        matches = []

        # Find feature flag nodes
        flags = graph.get_nodes_by_kind(NodeKind.FEATURE_FLAG)

        for flag in flags:
            matches.append({
                "node_id": flag.id,
            })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create context selector mapping for feature flag.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for feature flag.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"fflag_{node_id}_{hashlib.sha256(b'feature_flag').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONTEXT,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Feature Flag",
            description=f"Feature flag '{node.name}' selects system context",
            confidence_score=0.85,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.85,
                )
            ],
            evidence_count=1,
            parser_certainty=0.9,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "feature_flag"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.CONTEXT
