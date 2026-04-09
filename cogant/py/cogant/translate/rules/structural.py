"""Structural translation rules.

This module is part of the :mod:`cogant.translate.rules` package and
contains rules that recognise structural patterns in the program graph (reads, writes, containment, inheritance, pipelines). Every class in this file inherits from
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


class ReadOnlyInputRule(TranslationRule):
    """Maps modules with many read-only external inputs to observation modality."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find modules with predominance of read operations.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched module nodes.
        """
        matches = []

        # Find all modules
        modules = graph.get_nodes_by_kind(NodeKind.MODULE)

        for module in modules:
            # Get all edges from module
            outgoing_edges = graph.get_edges_from(module.id)
            incoming_edges = graph.get_edges_to(module.id)

            # Count read vs write operations
            reads = sum(1 for e in outgoing_edges if e.kind == EdgeKind.READS)
            writes = sum(1 for e in outgoing_edges if e.kind == EdgeKind.WRITES)

            # Check if predominantly read-only
            if reads > 0 and writes == 0:
                matches.append({
                    "node_id": module.id,
                    "read_count": reads,
                    "write_count": writes,
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create observation mapping for read-only module.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for observation modality.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"obs_{node_id}_{hashlib.sha256(b'read_only_input').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Read-Only Input",
            description=f"Module '{node.name}' acts as observation source (read-only external input)",
            confidence_score=0.7,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.7,
                    metadata={"read_count": match["read_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.8,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "read_only_input"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.OBSERVATION


class MutatingSubsystemRule(TranslationRule):
    """Maps objects with frequent internal mutations to hidden-state modality."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find objects/classes with high mutation frequency.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched class/object nodes.
        """
        matches = []

        # Find all classes
        classes = graph.get_nodes_by_kind(NodeKind.CLASS)

        for cls in classes:
            # Count mutations (WRITES and MUTATES edges targeting this class)
            mutation_edges = []
            for edge in graph.edges.values():
                if (edge.target_id == cls.id or edge.source_id == cls.id) and edge.kind in (EdgeKind.WRITES, EdgeKind.MUTATES):
                    mutation_edges.append(edge)

            # Check if has mutation activity (threshold: 1+)
            if len(mutation_edges) >= 1:
                matches.append({
                    "node_id": cls.id,
                    "mutation_count": len(mutation_edges),
                    "mutation_edges": [e.id for e in mutation_edges],
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create hidden-state mapping for mutating subsystem.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for hidden-state.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"hs_{node_id}_{hashlib.sha256(b'mutating_subsystem').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=[node_id],
            graph_fragment_edge_ids=match.get("mutation_edges", []),
            semantic_label=f"{node.name} - Hidden State",
            description=f"Class '{node.name}' maintains internal state (frequent mutations)",
            confidence_score=0.75,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.75,
                    metadata={"mutation_count": match["mutation_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.8,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "mutating_subsystem"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.HIDDEN_STATE


class InheritanceRule(TranslationRule):
    """Maps class inheritance to inform semantic roles via base class hierarchy."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find classes with inheritance relationships.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched inheritance patterns.
        """
        matches = []

        classes = graph.get_nodes_by_kind(NodeKind.CLASS)
        for cls in classes:
            # Find INHERITS edges from this class
            out_edges = graph.get_edges_from(cls.id)
            inherit_edges = [e for e in out_edges if e.kind == EdgeKind.INHERITS]

            if inherit_edges:
                base_ids = [e.target_id for e in inherit_edges]
                matches.append({
                    "node_id": cls.id,
                    "base_ids": base_ids,
                    "base_count": len(base_ids),
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create semantic mapping based on inheritance pattern.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for inheritance-informed role.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        # Infer semantic kind from base class names
        base_ids = match.get("base_ids", [])
        inferred_kind = MappingKind.HIDDEN_STATE  # default

        # Check if abstract or interface-like
        if node.name.startswith("Abstract") or node.name.startswith("Base"):
            inferred_kind = MappingKind.POLICY

        # Otherwise check bases
        for base_id in base_ids:
            base = graph.get_node(base_id)
            if base:
                base_name_lower = base.name.lower()
                if "handler" in base_name_lower or "controller" in base_name_lower:
                    inferred_kind = MappingKind.POLICY
                    break

        mapping_id = f"inh_{node_id}_{hashlib.sha256(b'inheritance').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=inferred_kind,
            graph_fragment_node_ids=[node_id] + base_ids,
            semantic_label=f"{node.name} - Inheritance Role",
            description=f"Class '{node.name}' inherits from {match['base_count']} base(s), mapped to {inferred_kind.value}",
            confidence_score=0.7,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.7,
                    metadata={"base_count": match["base_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.75,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "inheritance"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.POLICY


class ContainmentRule(TranslationRule):
    """Analyzes methods within classes to extract observation vs action vs policy roles."""

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find classes with multiple methods for detailed analysis.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched containment patterns.
        """
        matches = []

        classes = graph.get_nodes_by_kind(NodeKind.CLASS)
        for cls in classes:
            # Find CONTAINS edges to methods
            out_edges = graph.get_edges_from(cls.id)
            method_edges = [e for e in out_edges if e.kind == EdgeKind.CONTAINS]
            method_ids = [e.target_id for e in method_edges]

            # Only match classes with 5+ methods for significant analysis
            if len(method_ids) >= 5:
                matches.append({
                    "node_id": cls.id,
                    "method_ids": method_ids,
                    "method_count": len(method_ids),
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create containment analysis mapping.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping summarizing method roles.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        method_ids = match.get("method_ids", [])

        # Analyze method roles
        observation_methods = []
        action_methods = []
        policy_methods = []

        observation_keywords = ["get", "read", "fetch", "query", "display", "show", "status", "info", "list"]
        action_keywords = ["set", "update", "create", "delete", "send", "push", "execute", "run", "process", "handle", "dispatch"]
        policy_keywords = ["route", "dispatch", "handle"]

        for method_id in method_ids:
            method = graph.get_node(method_id)
            if not method:
                continue

            name_lower = method.name.lower()

            # Classify by keyword
            if any(kw in name_lower for kw in observation_keywords):
                observation_methods.append(method_id)
            elif any(kw in name_lower for kw in action_keywords):
                action_methods.append(method_id)
            elif any(kw in name_lower for kw in policy_keywords):
                policy_methods.append(method_id)

        # Infer primary role from method distribution
        primary_role = MappingKind.HIDDEN_STATE
        if len(action_methods) > len(observation_methods):
            primary_role = MappingKind.ACTION
        elif len(observation_methods) > len(action_methods):
            primary_role = MappingKind.OBSERVATION
        elif len(policy_methods) > 0:
            primary_role = MappingKind.POLICY

        mapping_id = f"cont_{node_id}_{hashlib.sha256(b'containment').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=primary_role,
            graph_fragment_node_ids=[node_id] + method_ids,
            semantic_label=f"{node.name} - Containment Analysis",
            description=f"Class '{node.name}' contains {len(observation_methods)} observations, {len(action_methods)} actions, {len(policy_methods)} policies → primary role: {primary_role.value}",
            confidence_score=0.75,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.75,
                    metadata={
                        "observation_methods": len(observation_methods),
                        "action_methods": len(action_methods),
                        "policy_methods": len(policy_methods),
                    },
                )
            ],
            evidence_count=1,
            parser_certainty=0.8,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "containment"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.HIDDEN_STATE


class DataPipelineRule(TranslationRule):
    """Maps data transformation chains to data-flow modality.

    Detects functions that read from one source, transform, and write to another.
    Pattern: node with both READS and WRITES edges where read sources differ
    from write targets.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find functions with both read and write edges to different targets.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched data pipeline nodes.
        """
        matches = []

        # Find functions and methods
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        methods = graph.get_nodes_by_kind(NodeKind.METHOD)

        for node in functions + methods:
            out_edges = graph.get_edges_from(node.id)

            read_edges = [e for e in out_edges if e.kind == EdgeKind.READS]
            write_edges = [e for e in out_edges if e.kind == EdgeKind.WRITES]

            # Must have both reads and writes
            if not read_edges or not write_edges:
                continue

            read_targets = {e.target_id for e in read_edges}
            write_targets = {e.target_id for e in write_edges}

            # Read sources must differ from write targets (transformation, not echo)
            if read_targets != write_targets:
                matches.append({
                    "node_id": node.id,
                    "read_targets": list(read_targets),
                    "write_targets": list(write_targets),
                    "read_count": len(read_edges),
                    "write_count": len(write_edges),
                })

        return matches

    def apply(self, graph: ProgramGraph, match: Dict[str, Any]) -> Optional[SemanticMapping]:
        """Create data-flow mapping for data pipeline node.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for data flow.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        fragment_node_ids = (
            [node_id]
            + match.get("read_targets", [])
            + match.get("write_targets", [])
        )

        mapping_id = f"dpipe_{node_id}_{hashlib.sha256(b'data_pipeline').hexdigest()[:8]}"

        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.DATA_FLOW,
            graph_fragment_node_ids=fragment_node_ids,
            semantic_label=f"{node.name} - Data Pipeline",
            description=f"Function '{node.name}' transforms data (reads from {match['read_count']} source(s), writes to {match['write_count']} target(s))",
            confidence_score=0.75,
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.75,
                    metadata={
                        "read_count": match["read_count"],
                        "write_count": match["write_count"],
                    },
                )
            ],
            evidence_count=1,
            parser_certainty=0.8,
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "data_pipeline"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.DATA_FLOW
