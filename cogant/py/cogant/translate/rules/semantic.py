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


OBSERVATION_KEYWORDS = [
    "get", "read", "fetch", "query", "display", "show", "status", "info", "list",
]
"""Lexical keywords that signal an observation-role function or method.

Chosen from PEP 8 naming conventions and the CPython stdlib corpus (audit
2026-04-09): ``get_``/``read_``/``fetch_``/``query_`` are the canonical
accessor prefixes; ``display``/``show``/``status``/``info``/``list`` round
out the set with UI/introspection verbs commonly attached to observers in
Python web frameworks (Flask, Django). TODO(calibration): expand the list
against a frequency analysis of observation methods in the 20-repo corpus
(see ``_rnd/CALIBRATION.md``). Known gaps: ``peek``, ``sample``,
``inspect`` — add if they appear.
"""

ACTION_KEYWORDS = [
    "set", "update", "create", "delete", "send", "push", "execute", "run",
    "process", "handle", "dispatch", "encode", "decode", "dump", "load",
]
"""Lexical keywords that signal an action-role function or method.

Chosen from PEP 8 naming conventions plus the CRUD/IO verb set. Note:
``handle``/``dispatch`` also appear in the POLICY keyword list — this
is intentional (they genuinely straddle action and policy roles) and is
resolved by confidence tie-breaking in ``_resolve_conflicts``. Principled
default. TODO(calibration): measure the action→policy conflict rate on
``handle``/``dispatch`` matches in the 20-repo corpus. Known gaps:
``commit``, ``rollback``, ``flush``, ``emit`` — add if frequent.
"""


class ObservationRule(TranslationRule):
    """Maps getter/query functions and read-only methods to observation modality.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.85)`` on keyword match, or
        ``(0, 0.70)`` on the edge-based read-only fallback.
        - Keyword band: **high band** (0.85), same as
          ``PreferenceRule`` and ``TestAssertionRule``, tied second
          only to ``ConfigRule`` (0.90). Rationale: lexical matches
          on ``get_``/``read_``/``fetch_`` prefixes carry strong
          prior probability of observation semantics based on PEP 8
          naming convention.
        - Fallback band: **bottom band** (0.70). The structural "reads,
          no writes" signal alone is weaker because pure-read helpers
          are also ubiquitous in private utility code.
        The bimodal confidence lets conflict resolution automatically
        prefer keyword-driven observations over structural ones.
        TODO(calibration): empirically validate the 0.85/0.70 split
        against a hand-labeled observation fixture.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find functions/methods that observe state without mutation.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched observation functions/methods.
        """
        matches = []
        observation_keywords = OBSERVATION_KEYWORDS

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
        # Bimodal confidence — 0.85 on keyword hit (high band, strong
        # PEP 8 naming prior), 0.70 on edge-only fallback (bottom band,
        # weaker because pure-read helpers are ubiquitous in private
        # utility code). The split is principled; the 0.15 gap is
        # chosen to cross the STATIC_ONLY → STATIC_PLUS_RUNTIME boundary
        # (0.65) if dynamic evidence is later added to a keyword-matched
        # mapping.
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

    def explain(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> RuleExplanation:
        """Explain whether this node is an observation.

        Walks the same decision path used by :meth:`matches`, but
        collects concrete evidence snippets (keyword matches and
        READS/WRITES edge counts) into a :class:`RuleExplanation` so the
        ``cogant explain`` CLI can render a justification report.
        """
        if node.kind not in (NodeKind.FUNCTION, NodeKind.METHOD):
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=(
                    f"observation rule only applies to functions/methods; "
                    f"node kind is {node.kind.value}"
                ),
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        name_lower = (node.name or "").lower()
        matched_keywords = [kw for kw in OBSERVATION_KEYWORDS if kw in name_lower]

        out_edges = graph.get_edges_from(node.id)
        read_targets = [e.target_id for e in out_edges if e.kind == EdgeKind.READS]
        write_targets = [e.target_id for e in out_edges if e.kind == EdgeKind.WRITES]

        evidence: List[str] = []
        if matched_keywords:
            evidence.append(f"keyword match: {matched_keywords}")
        evidence.append(f"READS count: {len(read_targets)}")
        evidence.append(f"WRITES count: {len(write_targets)}")
        if read_targets:
            evidence.append(f"READS targets: {sorted(read_targets)[:5]}")

        keyword_match = bool(matched_keywords)
        read_only = len(read_targets) > 0 and len(write_targets) == 0

        if keyword_match or read_only:
            if keyword_match and read_only:
                reason = (
                    f"name contains observation keyword(s) {matched_keywords} "
                    f"AND read-only access pattern (READS={len(read_targets)}, "
                    f"WRITES=0)"
                )
            elif keyword_match:
                reason = (
                    f"name contains observation keyword(s) {matched_keywords}"
                )
            else:
                reason = (
                    f"read-only access pattern (READS={len(read_targets)}, "
                    f"WRITES=0) with no observation keyword"
                )
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=True,
                reason=reason,
                evidence=evidence,
                mapping_kind=self.mapping_kind.value,
            )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"no observation keyword in '{node.name}' and not read-only "
                f"(READS={len(read_targets)}, WRITES={len(write_targets)})"
            ),
            evidence=evidence,
            mapping_kind=self.mapping_kind.value,
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
    """Maps setter/mutator functions to action modality.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.80)``. **Upper-mid band** (0.80)
        alongside ``PolicyRule``, ``ContextRule``, ``OrchestratorRule``
        and ``CircuitBreakerRule``. Rationale: action semantics are
        slightly less specific than ``PreferenceRule``/``TestAssertionRule``
        (0.85) because CRUD verbs are the most overloaded lexical
        category in real codebases. The edge-based fallback
        ``writes_only >= 2`` was added (commit e1eb463) to recover
        recall on functional codebases where writes are named
        ``apply``/``reduce`` rather than ``set``/``update``.
        TODO(calibration): sweep the ``>=2`` writes threshold in
        {1, 2, 3} on the 20-repo corpus.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find functions/methods that mutate state.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched action functions/methods.
        """
        matches = []
        action_keywords = ACTION_KEYWORDS

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

            # Fallback threshold: ``writes >= 1`` outgoing WRITES/MUTATES
            # edge. Principled default aligned with the property invariant
            # in ``tests/property/test_translation_invariants.py`` which
            # accepts a single mutation edge as valid structural grounding
            # for the ACTION role. A ``>=2`` floor would reject legitimate
            # mutators whose static graph collapses multiple ``self.X``
            # writes into a single edge to the parent class node (a known
            # tree-sitter Python behaviour on ``self`` attribute writes).
            # TODO(calibration): sweep {1, 2, 3} on the 20-repo corpus if
            # false-positive rate on functional codebases exceeds ~5%.
            if keyword_match or writes >= 1:
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

        # Confidence 0.80 — principled default (upper-mid band). Action
        # verbs are slightly overloaded in practice (CRUD terms appear
        # in helpers and wrappers), hence 0.05 below the 0.85 band of
        # ``PreferenceRule``/``TestAssertionRule``. Parser certainty
        # 0.85 = full AST-native band (names + edges both parsed by
        # Python AST, not the tree-sitter fallback).
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.ACTION,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Action",
            description=f"Function/method '{node.name}' performs action (mutates state)",
            confidence_score=0.8,  # principled default (upper-mid band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.8,
                    metadata={"write_count": match["write_count"], "call_count": match["call_count"]},
                )
            ],
            evidence_count=1,
            parser_certainty=0.85,  # AST-native band
        )

    def explain(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> RuleExplanation:
        """Explain whether this node performs an action.

        Mirrors the :meth:`matches` decision by checking for action
        keywords in the node name and counting outgoing WRITES/MUTATES
        edges. The rule fires when either (a) the name contains an
        action keyword, or (b) at least 2 outgoing WRITES edges exist
        (the functional-codebase recall threshold).
        """
        if node.kind not in (NodeKind.FUNCTION, NodeKind.METHOD):
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=(
                    f"action rule only applies to functions/methods; "
                    f"node kind is {node.kind.value}"
                ),
                evidence=[],
                mapping_kind=self.mapping_kind.value,
            )

        name_lower = (node.name or "").lower()
        matched_keywords = [kw for kw in ACTION_KEYWORDS if kw in name_lower]

        out_edges = graph.get_edges_from(node.id)
        write_edges = [e for e in out_edges if e.kind == EdgeKind.WRITES]
        mutate_edges = [e for e in out_edges if e.kind == EdgeKind.MUTATES]
        call_edges = [e for e in out_edges if e.kind == EdgeKind.CALLS]

        evidence: List[str] = []
        if matched_keywords:
            evidence.append(f"keyword match: {matched_keywords}")
        evidence.append(f"WRITES count: {len(write_edges)}")
        if mutate_edges:
            evidence.append(f"MUTATES count: {len(mutate_edges)}")
        evidence.append(f"CALLS count: {len(call_edges)}")
        if write_edges:
            write_targets = [e.target_id for e in write_edges]
            evidence.append(f"WRITES targets: {sorted(write_targets)[:5]}")

        keyword_match = bool(matched_keywords)
        mutation_count = len(write_edges) + len(mutate_edges)
        writes_threshold = mutation_count >= 1

        if keyword_match or writes_threshold:
            if keyword_match and writes_threshold:
                reason = (
                    f"name contains action keyword(s) {matched_keywords} "
                    f"AND has {mutation_count} WRITES/MUTATES edge(s) "
                    f"(>=1 threshold)"
                )
            elif keyword_match:
                reason = f"name contains action keyword(s) {matched_keywords}"
            else:
                reason = (
                    f"has {mutation_count} WRITES/MUTATES edge(s) "
                    f"(>=1 mutation threshold) with no action keyword"
                )
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=True,
                reason=reason,
                evidence=evidence,
                mapping_kind=self.mapping_kind.value,
            )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"no action keyword in '{node.name}' and "
                f"{mutation_count} WRITES/MUTATES edges (<1 threshold)"
            ),
            evidence=evidence,
            mapping_kind=self.mapping_kind.value,
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
    """Maps controllers, handlers, and routers to policy modality.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.80)``. **Upper-mid band** (0.80),
        tied with ``ActionRule``, ``ContextRule``, ``OrchestratorRule``,
        ``CircuitBreakerRule``. Rationale: controller/handler/router
        vocabulary is a strong web-framework signal (Flask, Django,
        FastAPI) but carries real ambiguity — "handler" also appears
        in action and retry contexts. Confidence tie-breaking between
        policy and action on ``handle``/``dispatch`` is delegated to
        per-match context. TODO(calibration): measure the
        policy↔action collision rate on ``handle``/``dispatch`` in
        the 20-repo corpus.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
        """Find classes and functions that implement policy/control logic.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched policy nodes.
        """
        matches = []
        # Policy keywords — sourced from web-framework conventions
        # (Flask view, Django middleware, FastAPI router, express
        # handler). Principled default. The overlap with ACTION_KEYWORDS
        # on ``handle``/``dispatch`` is intentional; conflict resolution
        # in ``_resolve_conflicts`` will pick whichever rule produces
        # higher confidence on that specific match.
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

        # Confidence 0.80 — principled default (upper-mid band).
        # Parser certainty 0.85 = AST-native (class/function names
        # are extracted by Python AST, not tree-sitter fallback).
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.POLICY,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Policy",
            description=f"{'Class' if match['node_type'] == 'class' else 'Function'} '{node.name}' implements control policy",
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
            parser_certainty=0.85,  # AST-native band
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
    """Maps validators and test functions to preference/constraint modality.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.85)``. **High band** (0.85), tied
        with ``TestAssertionRule`` and the keyword branch of
        ``ObservationRule``. Rationale: ``validate``/``check``/
        ``Validator``/``test_`` are exceptionally strong lexical
        signals — there is essentially no non-constraint use of
        ``test_`` prefixes in well-formed Python, and PEP 8 +
        pytest/unittest conventions anchor the other patterns.
        Parser certainty 0.90 is the highest in the rule family
        because name-only matching doesn't depend on edge extraction.
    """

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

        # Confidence 0.85 — principled default (high band). The
        # ``test_``/``assert_``/``validate``/``check``/``Validator``
        # vocabulary is exceptionally unambiguous in Python — PEP 8
        # + pytest/unittest conventions anchor these as constraint
        # signals. Parser certainty 0.90 is the highest in the rule
        # family because name-only matching doesn't depend on edge
        # extraction accuracy.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONSTRAINT,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Preference/Constraint",
            description=f"{'Class' if match['constraint_type'] == 'class' else 'Function'} '{node.name}' defines system constraints",
            confidence_score=0.85,  # principled default (high band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.85,
                )
            ],
            evidence_count=1,
            parser_certainty=0.9,  # name-only, highest in family
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
    """Maps configuration and parameter classes to context modality.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.80)``. **Upper-mid band** (0.80),
        tied with ``ActionRule``/``PolicyRule``. Rationale: context
        keywords ``config``/``settings``/``env``/``options``/``params``
        are specific but less strong than a ``validate``/``test_``
        prefix (which get 0.85); they correlate well with
        configuration roles but also occasionally appear in
        orchestrators. Note: the dedicated ``ConfigRule`` (control.py,
        confidence 0.90) supersedes this rule when ``config`` is in
        the name — this rule provides the broader
        ``settings``/``params``/``env`` fallback.
    """

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

        # Confidence 0.80 — principled default (upper-mid band).
        # Parser certainty 0.85 = AST-native band. ``ConfigRule`` in
        # control.py supersedes this rule (confidence 0.90) on exact
        # ``config`` hits.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONTEXT,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Context",
            description=f"{'Class' if match['context_type'] == 'class' else 'Function'} '{node.name}' provides system context",
            confidence_score=0.8,  # principled default (upper-mid band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.8,
                )
            ],
            evidence_count=1,
            parser_certainty=0.85,  # AST-native band
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "context"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.CONTEXT
