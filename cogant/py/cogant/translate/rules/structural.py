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

from cogant.schemas.core import Node, NodeKind, EdgeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import (
    SemanticMapping,
    MappingKind,
    ConfidenceTier,
    ProvenanceRecord,
)
from cogant.graph.queries import GraphQuery
from cogant.translate.engine import RuleExplanation, TranslationRule


class ReadOnlyInputRule(TranslationRule):
    """Maps modules with many read-only external inputs to observation modality.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.7)`` via the flat-``priority=0`` design
        documented in :class:`TranslationRule.priority`, so conflict
        resolution falls through to ``confidence_score = 0.7``. This
        places the rule in the **bottom band** (0.70) alongside
        ``InheritanceRule``, ``RetryPatternRule``, ``ErrorBoundaryRule``
        and the ``ObservationRule`` lexical-fallback branch. Rationale:
        module-level "all reads, no writes" is a weak structural signal
        (modules nearly always expose some read API), so it should
        cleanly lose to any function/method-level rule that also fires
        on the same fragment. TODO(calibration): measure the
        ReadOnlyInputRule→ObservationRule conflict-loss rate on the
        20-repo corpus and promote to a dedicated priority tier only
        if the loss rate exceeds ~20%.
    """

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

        # Confidence 0.70 — principled default (bottom band). Module-level
        # "reads only" is a weak structural cue (modules almost always
        # export some read API), so this rule is intentionally beaten by
        # any higher-confidence function/method-level rule that fires on
        # the same fragment. 0.70 lands at STATIC_ONLY_THRESHOLD+0.20 in
        # ConfidenceModel, keeping the mapping acceptable on its own.
        # Parser certainty 0.80 = tree-sitter Python-fallback band.
        # TODO(calibration): retune against per-module precision on the
        # 20-repo fixture set.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Read-Only Input",
            description=f"Module '{node.name}' acts as observation source (read-only external input)",
            confidence_score=0.7,  # principled default (bottom band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.7,
                    metadata={"read_count": match["read_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.8,  # tree-sitter Python-fallback band
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
    """Maps objects with frequent internal mutations to hidden-state modality.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.75)``. **Mid band** (0.75) alongside
        ``ContainmentRule``, ``DataPipelineRule`` and ``EventBusRule``.
        Rationale: a class touched by any ``WRITES``/``MUTATES`` edge is
        a mild structural cue for hidden state, stronger than a pure
        read-only module (0.70) but weaker than a lexical action match
        (0.80) or a configuration hit (0.85+). The mutation-count
        threshold is deliberately ``>=1`` — any mutation edge counts —
        because classes with internal state typically exhibit bursty
        mutation patterns and a higher threshold would miss lazy
        singletons. TODO(calibration): sweep the threshold in {1, 2, 3}
        on the 20-repo corpus; a higher floor would likely raise
        precision at the cost of recall on under-instrumented fixtures.
    """

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

            # Mutation-count threshold >=1. Principled default: any
            # mutation edge counts, because classes with internal state
            # are typically bursty (rare mutations between long read
            # phases) and a higher floor (e.g. >=3) would miss lazy
            # singletons and state machines with a single setter. The
            # downstream confidence gate (0.75 band) prevents false
            # positives on incidental ``__init__`` assignments.
            # TODO(calibration): sweep {1, 2, 3} on the 20-repo corpus.
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

        # Confidence 0.75 — principled default (mid band). Any
        # ``WRITES``/``MUTATES`` edge on a class is a mild structural
        # cue for hidden state: stronger than a pure read-only module
        # (0.70) but weaker than a lexical action match (0.80) or a
        # config hit (0.85+). Parser certainty 0.80 = tree-sitter
        # Python-fallback band (edge extraction is less precise than
        # name extraction, hence below the 0.85–0.90 AST-native band).
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.HIDDEN_STATE,
            graph_fragment_node_ids=[node_id],
            graph_fragment_edge_ids=match.get("mutation_edges", []),
            semantic_label=f"{node.name} - Hidden State",
            description=f"Class '{node.name}' maintains internal state (frequent mutations)",
            confidence_score=0.75,  # principled default (mid band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.75,
                    metadata={"mutation_count": match["mutation_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.8,  # tree-sitter Python-fallback band
        )

    def explain(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> RuleExplanation:
        """Explain whether this class is a hidden-state / mutating subsystem.

        The rule only applies to ``CLASS`` nodes and fires when the class
        has at least one edge of kind ``WRITES`` or ``MUTATES`` touching
        it (either as source or as target). This mirrors the match logic
        in :meth:`matches` so the explain report stays honest.
        """
        if node.kind != NodeKind.CLASS:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=(
                    f"mutating_subsystem rule only applies to classes; "
                    f"node kind is {node.kind.value}"
                ),
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        mutation_edges = []
        for edge in graph.edges.values():
            if (
                (edge.target_id == node.id or edge.source_id == node.id)
                and edge.kind in (EdgeKind.WRITES, EdgeKind.MUTATES)
            ):
                mutation_edges.append(edge)

        evidence: List[str] = [
            f"mutation edges (WRITES|MUTATES) touching class: {len(mutation_edges)}",
        ]
        if mutation_edges:
            sample = [
                f"{e.kind.value}:{e.source_id}->{e.target_id}"
                for e in mutation_edges[:5]
            ]
            evidence.append(f"sample: {sample}")

        if len(mutation_edges) >= 1:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=True,
                reason=(
                    f"class '{node.name}' has {len(mutation_edges)} "
                    f"WRITES/MUTATES edge(s), indicating internal state"
                ),
                evidence=evidence,
                mapping_kind=self.mapping_kind.value,
            )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"class '{node.name}' has no WRITES/MUTATES edges"
            ),
            evidence=evidence,
            mapping_kind=self.mapping_kind.value,
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
    """Maps class inheritance to inform semantic roles via base class hierarchy.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.7)``. **Bottom band** (0.70)
        alongside ``ReadOnlyInputRule`` and the resilience rules.
        Rationale: inheritance is a structural hint, not evidence —
        a subclass of ``AbstractHandler`` might be a controller or a
        test double or a stub. We use the lexical shortcut "name
        starts with ``Abstract``/``Base`` => POLICY" because Python
        convention strongly correlates those prefixes with abstract
        base classes (PEP 3119). Parser certainty 0.75 is slightly
        below the 0.80 edge-precision band because tree-sitter has
        known gaps on multi-base metaclass hierarchies.
        TODO(calibration): measure tier-disagreement rate vs.
        behavioral rules on the 20-repo corpus; if inheritance
        routinely gets overruled, demote to an "explanation only"
        rule that never writes a mapping.
    """

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

        # Confidence 0.70 — principled default (bottom band).
        # Inheritance is a structural hint rather than direct evidence:
        # a subclass of ``AbstractHandler`` might be a real policy, a
        # test double, or a stub. Parser certainty 0.75 (below the
        # 0.80 tree-sitter norm) reflects known gaps on multi-base
        # metaclass hierarchies. TODO(calibration): log agreement with
        # behavioral/semantic rules; if inheritance loses >50% of
        # conflicts it should be demoted to an explanation-only rule.
        return SemanticMapping(
            id=mapping_id,
            kind=inferred_kind,
            graph_fragment_node_ids=[node_id] + base_ids,
            semantic_label=f"{node.name} - Inheritance Role",
            description=f"Class '{node.name}' inherits from {match['base_count']} base(s), mapped to {inferred_kind.value}",
            confidence_score=0.7,  # principled default (bottom band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.7,
                    metadata={"base_count": match["base_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.75,  # below norm: metaclass gaps
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
    """Analyzes methods within classes to extract observation vs action vs policy roles.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.75)``. **Mid band** (0.75).
        Stronger than pure-structural ``InheritanceRule`` (0.70)
        because it aggregates *lexical* evidence across 5+ methods
        (majority-vote classification), but weaker than per-function
        ``ObservationRule``/``ActionRule`` keyword hits (0.80+)
        because the class-level aggregate can mask mixed-role classes.
        Method-count threshold = 5 (see ``matches``). TODO(calibration):
        sweep {3, 5, 8} method thresholds and the
        ``max(actions, observations)`` tie-breaking rule.
    """

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

            # Method-count threshold = 5. Principled default: below
            # 5 methods a class is too small for a majority-vote
            # classification to be stable (a single method's lexical
            # signal dominates), and the per-function ObservationRule/
            # ActionRule will already fire on each method anyway. The
            # choice of 5 (rather than 3 or 10) is guided by the
            # "5 ± 2 chunking limit" (Miller 1956) as a convenient
            # small-class/large-class boundary. TODO(calibration):
            # sweep {3, 5, 8} on the 20-repo corpus.
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

        # Confidence 0.75 — principled default (mid band). Aggregated
        # lexical evidence over 5+ methods is stronger than a pure
        # structural hint (0.70) but weaker than per-function lexical
        # hits (0.80+) because class-level majority voting can mask
        # mixed-role classes. Parser certainty 0.80 = tree-sitter
        # Python-fallback band.
        return SemanticMapping(
            id=mapping_id,
            kind=primary_role,
            graph_fragment_node_ids=[node_id] + method_ids,
            semantic_label=f"{node.name} - Containment Analysis",
            description=f"Class '{node.name}' contains {len(observation_methods)} observations, {len(action_methods)} actions, {len(policy_methods)} policies → primary role: {primary_role.value}",
            confidence_score=0.75,  # principled default (mid band)
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
            parser_certainty=0.8,  # tree-sitter Python-fallback band
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

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.75)``. **Mid band** (0.75). The
        "reads-from-A, writes-to-B (A≠B)" pattern is a strong
        structural cue for data flow, but we keep it at 0.75 rather
        than 0.80+ because edge-level precision is lower than
        name-level precision (tree-sitter occasionally over-reports
        ``READS`` on attribute-chain accesses). TODO(calibration):
        measure false-positive rate on the 20-repo corpus; if <5%,
        promote to 0.80.
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

        # Confidence 0.75 — principled default (mid band). Read-from-A
        # / write-to-B (A≠B) is a strong structural cue, but edge-level
        # precision is lower than name-level (tree-sitter sometimes
        # over-reports READS on attribute chains).
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.DATA_FLOW,
            graph_fragment_node_ids=fragment_node_ids,
            semantic_label=f"{node.name} - Data Pipeline",
            description=f"Function '{node.name}' transforms data (reads from {match['read_count']} source(s), writes to {match['write_count']} target(s))",
            confidence_score=0.75,  # principled default (mid band)
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
            parser_certainty=0.8,  # tree-sitter Python-fallback band
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "data_pipeline"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.DATA_FLOW
