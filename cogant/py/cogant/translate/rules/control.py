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
from typing import Any

from cogant.graph.queries import GraphQuery
from cogant.schemas.core import NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)
from cogant.translate.engine import TranslationRule

__all__ = ["ConfigRule", "FeatureFlagRule", "ParameterRule"]


class ConfigRule(TranslationRule):
    """Maps configuration files and structures to context priors.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.90)``. **Top band** (0.90) —
        the highest confidence score in the entire translation rule
        family. Rationale: ``ConfigRule`` fires only when the
        upstream parser has already classified a node as
        ``NodeKind.CONFIGURATION`` (yaml/toml/ini/json config files,
        module-level ``CONFIG = {...}`` dicts, ``Settings`` subclasses).
        That classification is itself strongly evidenced, so the
        confidence stacks: parser_certainty 0.95 (highest) plus
        confidence 0.90 makes this rule effectively unbeatable by
        heuristic rules, which is correct — explicit config is
        ground truth for context. TODO(calibration): confirm that
        ``NodeKind.CONFIGURATION`` extraction has <5% false-positive
        rate on the 20-repo corpus.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
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
            matches.append(
                {
                    "node_id": config.id,
                }
            )

        return matches

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
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

        # Confidence 0.90 — principled default (top band, highest in
        # entire rule family). The upstream parser has already
        # classified this node as CONFIGURATION, which is a strongly-
        # evidenced classification in its own right. Parser certainty
        # 0.95 is the highest in the family.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONTEXT,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Context Prior",
            description=f"Configuration '{node.name}' provides system context",
            confidence_score=0.9,  # principled default (top band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.9,
                )
            ],
            evidence_count=1,
            parser_certainty=0.95,  # highest in family (explicit config)
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
    """Maps feature flags to latent context selectors.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.85)``. **High band** (0.85),
        tied with ``PreferenceRule``/``TestAssertionRule`` and the
        keyword branch of ``ObservationRule``. Rationale: feature
        flags are specific but slightly less unambiguous than raw
        configuration (which gets 0.90); some "feature flag"
        patterns are actually dynamic toggles rather than static
        context selectors. The rule relies on upstream
        ``NodeKind.FEATURE_FLAG`` classification.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
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
            matches.append(
                {
                    "node_id": flag.id,
                }
            )

        return matches

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
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

        # Confidence 0.85 — principled default (high band). Relies on
        # upstream NodeKind.FEATURE_FLAG classification which is
        # slightly less precise than explicit CONFIGURATION.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONTEXT,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Feature Flag",
            description=f"Feature flag '{node.name}' selects system context",
            confidence_score=0.85,  # principled default (high band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.85,
                )
            ],
            evidence_count=1,
            parser_certainty=0.9,  # high AST precision on flag nodes
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "feature_flag"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.CONTEXT


class ParameterRule(TranslationRule):
    """Maps learnable parameters and hyperparameters to context priors.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.85)``. **High band** (0.85), tied
        with ``PreferenceRule``/``TestAssertionRule``. Rationale:
        learnable parameters are semantic ground truth for context —
        they control system behavior but are not part of the observation,
        action, or policy logic. Patterns: ``param_``, ``weight_``,
        ``hyperparameter``, ``learning_rate``, typed dataclass fields
        (float/int), module-level configuration assignments.
        TODO(calibration): validate that parameter detection covers
        ML frameworks (PyTorch, TensorFlow, scikit-learn) on the
        20-repo corpus.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
        """Find learnable parameters and hyperparameters.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched parameter nodes.
        """
        matches = []

        parameter_keywords = [
            "param_",
            "weight_",
            "hyperparameter",
            "learning_rate",
            "lr",
            "beta",
            "gamma",
            "alpha",
            "theta",
            "lambda_",
        ]

        # Find variables with parameter keywords
        variables = graph.get_nodes_by_kind(NodeKind.VARIABLE)
        for var in variables:
            name_lower = var.name.lower()
            if any(kw in name_lower for kw in parameter_keywords):
                matches.append(
                    {
                        "node_id": var.id,
                        "parameter_type": "variable",
                    }
                )

        # Find classes that are parameter/config dataclasses or contain float/int fields
        classes = graph.get_nodes_by_kind(NodeKind.CLASS)
        for cls in classes:
            name_lower = cls.name.lower()
            is_param_class = any(
                kw in name_lower for kw in ["param", "config", "settings", "hyperparameter"]
            )

            if is_param_class:
                matches.append(
                    {
                        "node_id": cls.id,
                        "parameter_type": "class",
                    }
                )

        return matches

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
        """Create context mapping for learnable parameter.

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

        mapping_id = f"param_{node_id}_{hashlib.sha256(b'parameter').hexdigest()[:8]}"

        # Confidence 0.85 — principled default (high band). Learnable
        # parameters are semantic ground truth for context — they control
        # system behavior but are not part of observation/action/policy.
        # Parser certainty 0.90 for variables (AST-native), 0.85 for
        # classes (dataclass detection is slightly less precise).
        param_type = match.get("parameter_type", "variable")
        parser_certainty = 0.9 if param_type == "variable" else 0.85

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONTEXT,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Learnable Parameter",
            description=f"{'Variable' if param_type == 'variable' else 'Class'} '{node.name}' defines learnable parameters",
            confidence_score=0.85,  # principled default (high band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.85,
                )
            ],
            evidence_count=1,
            parser_certainty=parser_certainty,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "parameter"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.CONTEXT
