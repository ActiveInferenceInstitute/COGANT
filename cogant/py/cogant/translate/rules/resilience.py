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
    "RetryPatternRule",
    "ErrorBoundaryRule",
    "SingletonAccessRule",
    "CircuitBreakerRule",
    "RateLimiterRule",
]


class RetryPatternRule(TranslationRule):
    """Maps retry/backoff/circuit breaker patterns to policy under uncertainty.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.70)``. **Bottom band** (0.70),
        tied with ``ReadOnlyInputRule``, ``InheritanceRule``,
        ``ErrorBoundaryRule``, and the lexical fallback of
        ``ObservationRule``. Rationale: keyword matching alone is
        a weak signal for retry logic — a function named
        ``retry_count`` might be a counter, not a retry executor.
        This rule intentionally loses to the stronger
        ``CircuitBreakerRule`` (0.80) when both fire. Parser
        certainty 0.70 is the lowest in the family because tree-
        sitter pattern detection for retry decorators is
        incomplete. TODO(calibration): promote to 0.80 if GUARDS
        edge coverage improves in the parser.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
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

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
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

        # Confidence 0.70 — principled default (bottom band).
        # Keyword-only matching is noisy (``retry_count`` might be
        # just a counter). Parser certainty 0.70 is the lowest in
        # the family because decorator-based retry patterns have
        # incomplete tree-sitter coverage. Intentionally loses to
        # CircuitBreakerRule (0.80) on the same fragment.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.POLICY,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Retry Policy",
            description=f"Function '{node.name}' implements retry/circuit breaker policy",
            confidence_score=0.7,  # principled default (bottom band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.7,
                )
            ],
            evidence_count=1,
            parser_certainty=0.7,  # lowest in family (decorator gap)
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

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.70)``. **Bottom band** (0.70).
        Rationale: CATCHES/THROWS edges are directly extracted from
        ``try/except`` / ``raise`` Python constructs (high structural
        precision) but the *semantic* meaning — "this is an error
        boundary worth modeling" — is weak because most non-trivial
        functions have at least one try/except for cleanup. Parser
        certainty 0.75 (below the 0.80 norm) reflects the fact that
        tree-sitter does not resolve exception-type hierarchies.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
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

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
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

        # Confidence 0.70 — principled default (bottom band).
        # CATCHES/THROWS edges are structurally precise but
        # semantically overloaded: most non-trivial functions have
        # some error handling. Parser certainty 0.75 reflects the
        # lack of exception-hierarchy resolution in tree-sitter.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.ERROR_HANDLING,
            graph_fragment_node_ids=fragment_node_ids,
            semantic_label=f"{node.name} - Error Boundary",
            description=f"Function '{node.name}' handles errors (catches {match['catches_count']}, throws {match['throws_count']})",
            confidence_score=0.70,  # principled default (bottom band)
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
            parser_certainty=0.75,  # no exception-hierarchy resolution
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

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.65)``. **Lowest band** (0.65) —
        the lowest confidence score in the entire rule family.
        Rationale: "accessed by many modules" is a very weak signal
        (logging facilities, common types, and enum constants all
        trigger it), so this rule is explicitly the last to win in
        any conflict. Thresholds: ``read_edges >= 3`` and
        ``len(reader_modules) >= 3``. The module-diversity check
        prevents the rule from firing on intra-module utilities.
        TODO(calibration): if the false-positive rate on the
        20-repo corpus exceeds 30%, raise the module-diversity
        threshold to 5 or combine with a "not in typing/stdlib
        whitelist" filter.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
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

            # Read-count threshold = 3. Principled default: below 3
            # readers is indistinguishable from ordinary 2-caller
            # helper code. TODO(calibration): sweep {3, 5, 8} on
            # 20-repo corpus; consider combining with a "stdlib/
            # typing whitelist" filter to cut false positives.
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

            # Module-diversity threshold = 3. Principled default:
            # fewer than 3 distinct module paths in the reader set
            # typically indicates an intra-package helper rather
            # than a true singleton/global. Matches the read-count
            # threshold for symmetry. TODO(calibration): sweep {3,
            # 5, 8} in tandem with the read-count sweep.
            if len(reader_modules) >= 3:
                matches.append({
                    "node_id": node.id,
                    "reader_ids": reader_ids,
                    "reader_count": len(read_edges),
                    "module_count": len(reader_modules),
                })

        return matches

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
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

        # Confidence 0.65 — principled default (LOWEST band in the
        # entire rule family). "Accessed by many modules" is a very
        # weak semantic signal; this rule is explicitly the last to
        # win in any conflict. 0.65 = STATIC_PLUS_RUNTIME_THRESHOLD
        # exactly, so this rule's mapping is *only* promoted past
        # the "trust without review" bar if runtime evidence
        # corroborates it.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CONTEXT,
            graph_fragment_node_ids=[node_id] + match.get("reader_ids", []),
            semantic_label=f"{node.name} - Singleton/Global State",
            description=f"{'Variable' if node.kind == NodeKind.VARIABLE else 'Class'} '{node.name}' is accessed by {match['reader_count']} readers across {match['module_count']} modules",
            confidence_score=0.65,  # principled default (LOWEST in family)
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
            parser_certainty=0.7,  # cross-module READS noise
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

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.80)``. **Upper-mid band** (0.80),
        tied with ``ActionRule``/``PolicyRule``/``ContextRule``/
        ``OrchestratorRule``. Rationale: the combined signal of
        GUARDS edge + retry keyword (or metadata hit) is much
        stronger than the keyword-only ``RetryPatternRule`` (0.70),
        so CircuitBreakerRule correctly wins on overlapping
        fragments. The composite requirement keeps false positives
        low — a function named ``retry_helper`` alone won't fire
        without a GUARDS edge.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
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

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
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

        # Confidence 0.80 — principled default (upper-mid band).
        # The composite (GUARDS edge + retry keyword/metadata)
        # requirement is a much stronger signal than
        # RetryPatternRule's keyword-only matching (0.70), so this
        # rule correctly wins overlapping conflicts.
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.CIRCUIT_BREAKER,
            graph_fragment_node_ids=[node_id] + match.get("guarded_ids", []),
            semantic_label=f"{node.name} - Circuit Breaker",
            description=f"{'Function' if node.kind in (NodeKind.FUNCTION, NodeKind.METHOD) else 'Class'} '{node.name}' implements circuit breaker pattern (guards {match['guards_count']} target(s))",
            confidence_score=0.80,  # principled default (upper-mid band)
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
            parser_certainty=0.85,  # AST-native on GUARDS edges
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "circuit_breaker"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.CIRCUIT_BREAKER


class RateLimiterRule(TranslationRule):
    """Maps rate-limiting patterns to throttling modality.

    Rule priority (audit 2026-04-09):
        Effective priority = ``(0, 0.75)``. **Mid band** (0.75), tied
        with ``MutatingSubsystemRule``/``ContainmentRule``/
        ``DataPipelineRule``/``EventBusRule``. Rationale: rate-limiting
        detection depends on keyword matching (``rate_limit``,
        ``throttle_``) or structural patterns (sleep/backoff loops with
        rate checks). Patterns: decorator-based rate limiters (``@rate_limit``),
        token-bucket implementations, leaky-bucket algorithms, sleep-based
        backoff with rate calculations. TODO(calibration): measure
        rate-limiter coverage on the 20-repo corpus; if <30%, promote to 0.80
        as the pattern is becoming more common in microservices.
    """

    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
        """Find rate-limiting patterns.

        Args:
            graph: Program graph.
            query: Graph query engine.

        Returns:
            List of matched rate limiter nodes.
        """
        matches = []

        rate_keywords = [
            "rate_limit", "throttle_", "token_bucket", "leaky_bucket",
            "ratelimit", "rate_limit", "quota", "throttle", "backoff"
        ]

        # Find functions and methods with rate-limiting keywords
        functions = graph.get_nodes_by_kind(NodeKind.FUNCTION)
        methods = graph.get_nodes_by_kind(NodeKind.METHOD)

        for node in functions + methods:
            name_lower = node.name.lower()
            has_rate_keyword = any(kw in name_lower for kw in rate_keywords)

            # Check for sleep/backoff pattern with rate logic
            out_edges = graph.get_edges_from(node.id)
            calls = [e for e in out_edges if e.kind == EdgeKind.CALLS]
            has_sleep_or_backoff = any(
                "sleep" in e.target_id.lower() or "backoff" in e.target_id.lower()
                for e in calls
            )

            if has_rate_keyword or has_sleep_or_backoff:
                matches.append({
                    "node_id": node.id,
                    "rate_keyword": has_rate_keyword,
                    "has_backoff": has_sleep_or_backoff,
                })

        # Find classes that implement rate limiting
        classes = graph.get_nodes_by_kind(NodeKind.CLASS)
        for cls in classes:
            name_lower = cls.name.lower()
            if any(kw in name_lower for kw in rate_keywords):
                matches.append({
                    "node_id": cls.id,
                    "rate_keyword": True,
                    "has_backoff": False,
                })

        return matches

    def apply(self, graph: ProgramGraph, match: dict[str, Any]) -> SemanticMapping | None:
        """Create rate-limiter mapping.

        Args:
            graph: Program graph.
            match: Matched pattern.

        Returns:
            SemanticMapping for rate limiter.
        """
        node_id = match["node_id"]
        node = graph.get_node(node_id)

        if not node:
            return None

        mapping_id = f"ratelim_{node_id}_{hashlib.sha256(b'rate_limiter').hexdigest()[:8]}"

        # Confidence 0.75 — principled default (mid band). Rate-limiting
        # patterns are identifiable but depend on keyword matching or
        # structural patterns that can have false positives (e.g., any
        # sleep call isn't necessarily rate-limiting). Parser certainty
        # 0.80 for keyword-based detection (AST-native).
        return SemanticMapping(
            id=mapping_id,
            kind=MappingKind.POLICY,
            graph_fragment_node_ids=[node_id],
            semantic_label=f"{node.name} - Rate Limiter",
            description=f"Function/class '{node.name}' implements rate limiting or throttling",
            confidence_score=0.75,  # principled default (mid band)
            confidence_tier=ConfidenceTier.STATIC_ONLY,
            provenance=[
                ProvenanceRecord(
                    source="static_analysis",
                    confidence=0.75,
                    metadata={
                        "rate_keyword": match.get("rate_keyword", False),
                        "has_backoff": match.get("has_backoff", False),
                    },
                )
            ],
            evidence_count=1,
            parser_certainty=0.8,  # keyword detection + call graph
        )

    @property
    def name(self) -> str:
        """Stable identifier for this rule."""
        return "rate_limiter"

    @property
    def mapping_kind(self) -> MappingKind:
        """GNN mapping kind produced by this rule."""
        return MappingKind.POLICY
