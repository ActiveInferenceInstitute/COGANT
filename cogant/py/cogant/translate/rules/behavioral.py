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
from typing import Any

from cogant.graph.queries import GraphQuery
from cogant.schemas.core import EdgeKind, NodeKind
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)
from cogant.translate.engine import TranslationRule

__all__ = [
    "OrchestratorRule",
    "TestAssertionRule",
    "EventBusRule",
    "StateMachineRule",
]


class OrchestratorRule(TranslationRule):
    """Maps schedulers and controllers to policy/action structure.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.80)``. **Upper-mid band** (0.80),
        tied with ``ActionRule``/``PolicyRule``/``ContextRule``/
        ``CircuitBreakerRule``. Rationale: high call fan-out is a
        reliable structural signal for orchestration but not
        unambiguous — utility modules can also have many calls.
        Call-count threshold = 3 (see ``matches``): below 3, the
        pattern is indistinguishable from simple helpers.
        TODO(calibration): sweep {2, 3, 5, 8} on the 20-repo corpus.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
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

            # Call-count threshold = 3. Principled default: below 3
            # calls, high-fan-out is indistinguishable from simple
            # helper functions (2 calls = typical setup/teardown);
            # at >=3 the pattern starts to look like real
            # orchestration (setup/work/cleanup triad or larger).
            # TODO(calibration): sweep {2, 3, 5, 8} on 20-repo corpus.
            if len(call_edges) >= 3:
                matches.append({
                    "node_id": node.id,
                    "call_count": len(call_edges),
                    "called_node_ids": [e.target_id for e in call_edges],
                })

        return matches

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
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

        # Confidence 0.80 — principled default (upper-mid band). High
        # call fan-out is reliable but not unambiguous. Parser
        # certainty 0.90 because call-edge extraction is one of the
        # highest-precision operations in the Python AST substrate.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.ORCHESTRATION,
            graph_fragment_node_ids=[node_id] + match.get("called_node_ids", []),
            semantic_label=f"{node.name} - Orchestrator",
            description=f"{'Class' if node.kind == NodeKind.CLASS else 'Function'} '{node.name}' acts as orchestrator (high fan-out)",
            confidence_score=0.8,  # principled default (upper-mid band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.8,
                    metadata={"call_count": match["call_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.9,  # high AST precision on CALLS edges
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
    """Maps test assertions to preference/constraint modality.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.85)``. **High band** (0.85), tied
        with ``PreferenceRule`` and the keyword branch of
        ``ObservationRule``. Rationale: a function with "test" in its
        name plus at least one ``CALLS`` edge (proxy for assertion)
        is one of the most reliable static signals in the entire
        rule family — pytest/unittest conventions are nearly
        universal. Parser certainty 0.95 is the *highest* in the
        family because both the name match and the call extraction
        are handled by the native Python AST with minimal ambiguity.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
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

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
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

        # Confidence 0.85 — principled default (high band). Parser
        # certainty 0.95 is the highest in the rule family because
        # "test"-prefix names and call extraction are both native
        # Python AST operations with near-zero ambiguity.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONSTRAINT,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Test Constraint",
            description=f"Test function '{node.name}' defines system constraints",
            confidence_score=0.85,  # principled default (high band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.85,
                    metadata={"assertion_count": match["assertion_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.95,  # highest in family (pytest/unittest conventions)
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
    """Maps event/subscription systems to observation-action coupling.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.75)``. **Mid band** (0.75),
        tied with ``MutatingSubsystemRule``/``ContainmentRule``/
        ``DataPipelineRule``. Rationale: event-bus detection depends
        on the upstream parser recognizing ``EVENT`` node kinds,
        which is only done for patterns the tree-sitter queries
        understand (decorator-driven pub/sub). Confidence tier is
        set to STATIC_PLUS_RUNTIME (not STATIC_ONLY) as a hint that
        dynamic trace corroboration is especially valuable for
        event-driven code. TODO(calibration): measure EVENT-node
        coverage across the 20-repo corpus.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
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

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
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

        # Confidence 0.75 — principled default (mid band). Event-bus
        # detection depends on upstream EVENT-kind nodes, which are
        # only emitted for patterns the tree-sitter queries
        # understand. Tier set to STATIC_PLUS_RUNTIME as a hint that
        # dynamic trace corroboration is particularly valuable for
        # event-driven code paths.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.OBSERVATION,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Event Bus",
            description=f"Event '{node.name}' couples observations to actions",
            confidence_score=0.75,  # principled default (mid band)
            confidence_tier=ConfidenceTier.STATIC_PLUS_RUNTIME,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.75,
                )
            ],
            evidence_count=1,
            parser_certainty=0.8,  # tree-sitter Python-fallback band
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "event_bus"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.OBSERVATION


class StateMachineRule(TranslationRule):
    """Maps finite state machine patterns to policy/hidden-state modality.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.80)``. **Upper-mid band** (0.80),
        tied with ``ActionRule``/``PolicyRule``/``ContextRule``/
        ``OrchestratorRule``/``CircuitBreakerRule``. Rationale: state
        machines with explicit state enums + transition methods are a
        strong structural signal for policy/control logic, but depend
        on the upstream parser recognizing STATE node kinds and
        transition patterns. Patterns: state enums, ``on_enter_*``/
        ``on_exit_*`` methods, ``transitions`` library usage, explicit
        state attributes (self.state, self._state).
        TODO(calibration): measure STATE-node coverage on the 20-repo
        corpus; if <40%, demote to 0.75 or add heuristics for
        transitions-library imports.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
        """Find finite state machine patterns.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched state machine nodes.
        """
        matches = []

        state_keywords = ["state", "fsm", "stateful", "transitions"]

        # Look for classes with state-like structure
        classes = graph.get_nodes_by_kind(NodeKind.CLASS)
        for cls in classes:
            name_lower = cls.name.lower()
            has_state_keyword = any(kw in name_lower for kw in state_keywords)

            # Check for on_enter/on_exit methods (state machine pattern)
            out_edges = graph.get_edges_from(cls.id)
            methods = [graph.get_node(e.target_id) for e in out_edges if e.kind == EdgeKind.CONTAINS]
            transition_methods = sum(
                1 for m in methods
                if m and ("on_enter" in m.name.lower() or "on_exit" in m.name.lower())
            )

            # Also check for explicit state variable
            has_state_var = any(
                "state" in m.name.lower()
                for m in methods
                if m and m.kind == NodeKind.VARIABLE
            )

            if has_state_keyword or transition_methods >= 1 or has_state_var:
                matches.append({
                    "node_id": cls.id,
                    "transition_count": transition_methods,
                    "has_state_var": has_state_var,
                })

        return matches

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
        """Create state machine mapping.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for state machine.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"fsm_{node_id}_{hashlib.sha256(b'state_machine').hexdigest()[:8]}"

        # Confidence 0.80 — principled default (upper-mid band).
        # Explicit state enums + transition methods are a strong
        # structural signal, but depend on upstream STATE-node
        # classification. Parser certainty 0.85 for method detection
        # (tree-sitter handles method names reliably).
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.POLICY,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - State Machine",
            description=f"Class '{node.name}' implements a finite state machine ({match.get('transition_count', 0)} transition method(s))",
            confidence_score=0.80,  # principled default (upper-mid band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.80,
                    metadata={
                        "transition_count": match.get("transition_count", 0),
                        "has_state_var": match.get("has_state_var", False),
                    },
                )
            ],
            evidence_count=1,
            parser_certainty=0.85,  # method name/structure detection
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "state_machine"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.POLICY
