"""Semantic translation rules.

This module is part of the :mod:`cogant.translate.rules` package and
contains rules that produce direct semantic-role mappings (observation, action, policy, preference, context). Every class in this file inherits from
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


class ObservationRule(TranslationRule):
    """Maps getter/query functions and read-only methods to observation modality."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find functions/methods that observe state without mutation.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched observation functions/methods.
        """
        matches = []
        observation_keywords = ["get", "read", "fetch", "query", "display", "show", "status", "info", "list"]

        # Find functions and methods
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        methods = graph.get_nodes_by_kind(NodeKind.METHOD)

        for node in functions + methods:
            name_lower = node.name.lower()

            # Check for keyword match
            keyword_match = any(kw in name_lower for kw in observation_keywords)

            # Check for read-only pattern: READS but no WRITES
            out_edges = graph.get_edges_from(node.id)
            reads = sum(1 for e in out_edges if e.kind == EdgeKind.READS)
            writes = sum(1 for e in out_edges if e.kind == EdgeKind.WRITES)

            # Match if keyword match OR (has reads and no writes)
            if keyword_match or (reads > 0 and writes == 0):
                matches.append({
                    "node_id": node.id,
                    "read_count": reads,
                    "write_count": writes,
                    "keyword_match": keyword_match,
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create observation mapping.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for observation.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"obs_{node_id}_{hashlib.sha256(b'observation').hexdigest()[:8]}"
        confidence = 0.85 if match["keyword_match"] else 0.7

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Observation",
            description=f"Function/method '{node.name}' observes state (read-only access)",
            confidence_score=confidence,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=confidence,
                    metadata={"read_count": match["read_count"], "write_count": match["write_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.8,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "observation"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.OBSERVATION


class ActionRule(TranslationRule):
    """Maps setter/mutator functions to action modality."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find functions/methods that mutate state.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched action functions/methods.
        """
        matches = []
        action_keywords = ["set", "update", "create", "delete", "send", "push", "execute", "run", "process", "handle", "dispatch", "encode", "decode", "dump", "load"]

        # Find functions and methods
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        methods = graph.get_nodes_by_kind(NodeKind.METHOD)

        for node in functions + methods:
            name_lower = node.name.lower()

            # Check for keyword match
            keyword_match = any(kw in name_lower for kw in action_keywords)

            # Count mutations (also used as edge-based fallback trigger)
            out_edges = graph.get_edges_from(node.id)
            writes = sum(1 for e in out_edges if e.kind in (EdgeKind.WRITES, EdgeKind.MUTATES))
            calls = sum(1 for e in out_edges if e.kind == EdgeKind.CALLS)
            writes_only = sum(1 for e in out_edges if e.kind == EdgeKind.WRITES)

            # Match on keyword OR on >=2 outgoing WRITES edges (functional-codebase recall)
            if keyword_match or writes_only >= 2:
                matches.append({
                    "node_id": node.id,
                    "write_count": writes,
                    "call_count": calls,
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create action mapping.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for action.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"act_{node_id}_{hashlib.sha256(b'action').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Action",
            description=f"Function/method '{node.name}' performs action (mutates state)",
            confidence_score=0.8,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.8,
                    metadata={"write_count": match["write_count"], "call_count": match["call_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.85,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "action"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.ACTION


class PolicyRule(TranslationRule):
    """Maps controllers, handlers, and routers to policy modality."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find classes and functions that implement policy/control logic.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched policy nodes.
        """
        matches = []
        policy_keywords = ["middleware", "handler", "controller", "manager", "router", "dispatcher", "scheduler", "route", "dispatch", "handle"]

        # Find classes
        classes = graph.get_nodes_by_kind(NodeKind.CLASS)
        for cls in classes:
            name_lower = cls.name.lower()
            if any(kw in name_lower for kw in policy_keywords):
                out_edges = graph.get_edges_from(cls.id)
                call_count = sum(1 for e in out_edges if e.kind == EdgeKind.CALLS)

                matches.append({
                    "node_id": cls.id,
                    "call_count": call_count,
                    "node_type": "class",
                })

        # Find functions with policy keywords
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        methods = graph.get_nodes_by_kind(NodeKind.METHOD)

        for node in functions + methods:
            name_lower = node.name.lower()
            if any(kw in name_lower for kw in ["route", "dispatch", "handle"]):
                out_edges = graph.get_edges_from(node.id)
                call_count = sum(1 for e in out_edges if e.kind == EdgeKind.CALLS)

                matches.append({
                    "node_id": node.id,
                    "call_count": call_count,
                    "node_type": "function",
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create policy mapping.

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

        mapping_id = f"pol_{node_id}_{hashlib.sha256(b'policy').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.POLICY,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Policy",
            description=f"{'Class' if match['node_type'] == 'class' else 'Function'} '{node.name}' implements control policy",
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
            parser_certainty=0.85,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "policy"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.POLICY


class PreferenceRule(TranslationRule):
    """Maps validators and test functions to preference/constraint modality."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find validation and test functions.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched preference/constraint nodes.
        """
        matches = []

        # Find classes with Validator/Checker in name
        classes = graph.get_nodes_by_kind(NodeKind.CLASS)
        for cls in classes:
            name_lower = cls.name.lower()
            if "validator" in name_lower or "checker" in name_lower:
                matches.append({
                    "node_id": cls.id,
                    "constraint_type": "class",
                })

        # Find functions/methods with test_, assert_, validate, check
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        methods = graph.get_nodes_by_kind(NodeKind.METHOD)

        for node in functions + methods:
            name_lower = node.name.lower()
            if (name_lower.startswith("test_") or
                name_lower.startswith("assert_") or
                "validate" in name_lower or
                "check" in name_lower):

                matches.append({
                    "node_id": node.id,
                    "constraint_type": "function",
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create preference/constraint mapping.

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

        mapping_id = f"pref_{node_id}_{hashlib.sha256(b'preference').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONSTRAINT,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Preference/Constraint",
            description=f"{'Class' if match['constraint_type'] == 'class' else 'Function'} '{node.name}' defines system constraints",
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
        return "preference"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.CONSTRAINT


class ContextRule(TranslationRule):
    """Maps configuration and parameter classes to context modality."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find context/configuration classes and functions.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched context nodes.
        """
        matches = []
        context_keywords = ["config", "settings", "env", "options", "params"]

        # Find classes and functions with context keywords
        classes = graph.get_nodes_by_kind(NodeKind.CLASS)
        for cls in classes:
            name_lower = cls.name.lower()
            if any(kw in name_lower for kw in context_keywords):
                matches.append({
                    "node_id": cls.id,
                    "context_type": "class",
                })

        # Find functions that only read and return values (read-only + returns)
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        for func in functions:
            out_edges = graph.get_edges_from(func.id)
            reads = sum(1 for e in out_edges if e.kind == EdgeKind.READS)
            writes = sum(1 for e in out_edges if e.kind == EdgeKind.WRITES)
            returns = sum(1 for e in out_edges if e.kind == EdgeKind.RETURNS)

            # Context function: reads config/state and returns it
            if reads > 0 and writes == 0 and returns > 0:
                matches.append({
                    "node_id": func.id,
                    "context_type": "function",
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create context mapping.

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

        mapping_id = f"ctx_{node_id}_{hashlib.sha256(b'context').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONTEXT,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Context",
            description=f"{'Class' if match['context_type'] == 'class' else 'Function'} '{node.name}' provides system context",
            confidence_score=0.8,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.8,
                )
            ],
            evidence_count=1,
            parser_certainty=0.85,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "context"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.CONTEXT
