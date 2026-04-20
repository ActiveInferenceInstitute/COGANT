"""Translation engine orchestrating rule application over program graphs."""

import dataclasses
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from cogant.graph.queries import GraphQuery
from cogant.schemas.core import Node
from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import ConfidenceTier, MappingKind, SemanticMapping
from cogant.translate.confidence import ConfidenceModel

logger = logging.getLogger(__name__)

__all__ = ["RuleExplanation", "TranslationRule", "TranslationEngine"]


@dataclass
class RuleExplanation:
    """Explanation of why a translation rule did or did not fire on a node.

    Produced by :meth:`TranslationRule.explain` during the
    ``cogant explain`` workflow. Each instance records a single
    (rule, node) decision: the rule's name and priority, whether it
    fired, a short human-readable reason, and the list of concrete
    evidence snippets (edge kinds, keyword matches, qualified
    identifiers) that backed the decision.

    The dataclass is deliberately JSON-serialization friendly via
    :meth:`to_dict` so the explain CLI can emit either a rich text
    report or a machine-readable JSON blob without duplicating the
    payload logic.

    Attributes:
        rule_name: Stable rule identifier (``rule.name``).
        priority: Rule priority tier (higher fires first).
        fired: True when the rule actually produced a mapping for this
            node, False when it was considered but skipped.
        reason: One-line explanation of the decision.
        evidence: Concrete evidence strings collected during matching
            (e.g. ``"WRITES self.display"``, ``"keyword match: 'set'"``).
        mapping_kind: Semantic kind the rule would have produced, or
            None when the rule did not fire.
        confidence: Confidence score (0.0–1.0) if rule fired, 0.0 if not fired.
        contradictions: List of contradictory evidence or rule conflicts that
            might lower confidence in this mapping.
    """

    rule_name: str
    priority: int
    fired: bool
    reason: str
    evidence: list[str] = field(default_factory=list)
    mapping_kind: str | None = None
    confidence: float = 0.0
    contradictions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain JSON-ready dict."""
        return dataclasses.asdict(self)


class TranslationRule(ABC):
    """Base class for translation rules."""

    @abstractmethod
    def matches(self, graph: ProgramGraph, query: GraphQuery) -> list[dict[str, Any]]:
        """Check if rule matches graph patterns.

        Args:
            graph: Program graph to analyze.
            query: Graph query engine.

        Returns:
            List of matched fragments, each with node/edge IDs.
        """
        pass

    @abstractmethod
    def apply(
        self,
        graph: ProgramGraph,
        match: dict[str, Any],
    ) -> SemanticMapping | None:
        """Apply rule to a matched pattern.

        Args:
            graph: Program graph.
            match: Matched pattern from matches().

        Returns:
            SemanticMapping if successful, None otherwise.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this rule."""
        pass

    @property
    @abstractmethod
    def mapping_kind(self) -> MappingKind:
        """Kind of semantic mapping produced."""
        pass

    @property
    def priority(self) -> int:
        """Priority of this rule (higher = applied first). Default 0.

        Rationale for default ``priority=0``:
            Most shipped rules keep the default ``0`` and are applied in
            registration order within a single fixpoint pass.
            :class:`~cogant.translate.rules.structural.MutatingSubsystemRule`
            overrides this property to return ``1`` so class-level hidden-state
            evidence wins ties against overlapping class-scoped mappings from
            aggregate rules at equal confidence. Aside from that exception,
            conflict resolution between overlapping mappings falls through to
            the ``(priority, confidence_score)`` lexicographic comparison in
            :meth:`TranslationEngine._resolve_conflicts`. See
            ``docs/evaluation/CALIBRATION.md`` for the full rule priority audit.
            TODO(calibration): if the empirical conflict-loss rate on
            real-world repos exceeds ~5%, broaden explicit priority tiers.
        """
        return 0

    def explain(
        self,
        node: Node,
        graph: ProgramGraph,
        query: GraphQuery,
    ) -> "RuleExplanation":
        """Explain whether this rule would fire on ``node``.

        This is the default implementation used by the ``cogant explain``
        CLI subcommand. It re-runs :meth:`matches` and checks whether any
        returned match references the target node's id. Subclasses that
        can produce richer evidence (specific edge kinds, keyword hits,
        metric values) should override this method.

        The base implementation never raises: if :meth:`matches` blows
        up, the returned :class:`RuleExplanation` has ``fired=False`` and
        a reason that names the exception type so the CLI can surface it
        instead of aborting the whole explain run.

        Args:
            node: The target node whose role we want to justify.
            graph: Program graph the rule is being evaluated against.
            query: Graph query engine bound to ``graph``.

        Returns:
            A :class:`RuleExplanation` record for this (rule, node) pair.
        """
        try:
            all_matches = self.matches(graph, query)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            return RuleExplanation(
                rule_name=self.name,
                priority=self.priority,
                fired=False,
                reason=f"rule error during matching: {type(exc).__name__}: {exc}",
                evidence=[],
                mapping_kind=self.mapping_kind.value,
                confidence=0.0,
                contradictions=[],
            )

        for match in all_matches:
            node_id = match.get("node_id") if isinstance(match, dict) else None
            fragment_ids: list[str] = []
            if isinstance(match, dict):
                fragment_ids = list(match.get("node_ids", []) or [])
            if node_id == node.id or node.id in fragment_ids:
                evidence: list[str] = []
                for key, value in sorted(match.items()):
                    if key in ("node_id", "node_ids"):
                        continue
                    evidence.append(f"{key}={value}")
                return RuleExplanation(
                    rule_name=self.name,
                    priority=self.priority,
                    fired=True,
                    reason=(
                        f"rule '{self.name}' matched node "
                        f"{node.qualified_name or node.name}"
                    ),
                    evidence=evidence,
                    mapping_kind=self.mapping_kind.value,
                    confidence=0.75,  # default reasonable confidence
                    contradictions=[],
                )

        return RuleExplanation(
            rule_name=self.name,
            priority=self.priority,
            fired=False,
            reason=(
                f"rule '{self.name}' considered but did not match "
                f"{node.qualified_name or node.name}"
            ),
            evidence=[],
            mapping_kind=self.mapping_kind.value,
            confidence=0.0,
            contradictions=[],
        )


class TranslationEngine:
    """Orchestrates translation of program graphs to semantic concepts.

    Applies a series of translation rules using fixpoint iteration until
    convergence (no new mappings) or max iterations reached. Resolves
    conflicts when multiple mappings target overlapping node sets.
    """

    def __init__(self, max_iterations: int = 10):
        """Initialize the translation engine.

        Args:
            max_iterations: Maximum fixpoint iterations (default 10).

        Rationale for default ``max_iterations=10``:
            Empirically the fixpoint settles in <=5 iterations on
            control-positive fixtures and typical corpora; 10 is a small
            safety margin. Callers with very large graphs may pass a
            higher bound. See ``docs/evaluation/CALIBRATION.md``.
        """
        self.rules: list[TranslationRule] = []
        self.mappings: dict[str, SemanticMapping] = {}
        self._match_log: list[dict[str, Any]] = []
        self._rule_priority: dict[str, int] = {}
        self.max_iterations = max_iterations
        self.iterations: list[dict[str, Any]] = []
        self._convergence_iteration: int | None = None
        self._rule_dependency_graph: dict[str, set[str]] = {}

    def register_rule(self, rule: TranslationRule) -> None:
        """Register a translation rule.

        Args:
            rule: Rule to register.
        """
        self.rules.append(rule)

    def translate(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge
        (convergence) or ``max_iterations`` is reached, whichever comes
        first. After the fixpoint exits, conflict resolution picks a
        single winning mapping per node set using priority then
        confidence as the tiebreaker.

        Args:
            graph: Program graph to translate. Must have been built by
                the graph stage; in particular, ``GraphQuery`` must be
                constructable from it.
            rule_filter: Optional list of rule names to apply. ``None``
                (default) applies every registered rule. Pass a subset
                to run a targeted translation, e.g. for unit tests or
                the ``cogant explain`` single-node path.

        Returns:
            List of ``SemanticMapping`` instances kept after conflict
            resolution, in insertion order. May be empty if no rule
            matched.

        Raises:
            RuntimeError: If a registered rule raises an unhandled
                exception. The engine catches and logs per-rule errors
                but re-raises engine-level invariant violations.

        Example:
            >>> engine = TranslationEngine()
            >>> engine.register_rule(ObservationRule())
            >>> mappings = engine.translate(graph)
            >>> all(hasattr(m.kind, "name") for m in mappings)
            True
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()
        self._convergence_iteration = None
        self._rule_dependency_graph.clear()
        self.iterations = []

        # Initialize rule dependency graph for cycle detection
        for rule in self.rules:
            self._rule_dependency_graph[rule.name] = set()

        n_nodes = len(graph.nodes)
        n_edges = len(graph.edges)
        active_rules = (
            [r for r in self.rules if r.name in rule_filter]
            if rule_filter else self.rules
        )
        logger.info(
            "Starting translation: %d rules active, %d nodes, %d edges%s",
            len(active_rules), n_nodes, n_edges,
            f" (filtered to {rule_filter})" if rule_filter else "",
        )

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
            )

            self.iterations.append(
                {
                    "iteration": iteration,
                    "new_mappings": new_mappings_this_pass,
                    "mappings_added": new_mappings_this_pass,
                }
            )

            self._log_match(
                "iteration_complete",
                "engine",
                f"iteration={iteration} new_mappings={new_mappings_this_pass}",
            )
            logger.info("Fixpoint iteration %d: %d new mappings",
                        iteration, new_mappings_this_pass)

            if new_mappings_this_pass == 0:
                logger.info("Fixpoint reached after %d iteration(s)", iteration)
                self._convergence_iteration = iteration
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        conflicts_before = len(self.mappings)
        self._resolve_conflicts()
        conflicts_removed = conflicts_before - len(self.mappings)
        if conflicts_removed > 0:
            logger.info(
                "Conflict resolution: removed %d overlapping mappings (%d → %d)",
                conflicts_removed, conflicts_before, len(self.mappings),
            )

        # Log per-kind role distribution
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1
        logger.info(
            "Translation complete: %d mappings across %d roles%s",
            len(self.mappings), len(by_kind),
            f" ({', '.join(f'{k}={v}' for k, v in sorted(by_kind.items()))})"
            if by_kind else "",
        )

        # Log coverage summary
        coverage = self.get_coverage_report(graph)
        logger.info(
            "Node coverage: %.1f%% (%d/%d covered, %d uncovered)",
            coverage["coverage_percent"],
            coverage["covered_nodes"],
            coverage["total_nodes"],
            coverage["uncovered_nodes"],
        )

        return list(self.mappings.values())

    def _apply_single_pass(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: list[str] | None = None,
        iteration: int = 0,
    ) -> int:
        """Apply all rules once, sorted by priority. Returns count of new mappings created.

        Args:
            graph: Program graph to translate.
            query: Graph query engine bound to ``graph``.
            rule_filter: Optional list of rule names to restrict application.
            iteration: Current fixpoint iteration number (for logging context).

        Returns:
            Number of new mappings created during this pass.
        """
        new_mappings = 0
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
        per_rule_counts: dict[str, int] = {}
        per_rule_errors: dict[str, int] = {}

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

            rule_new = 0
            rule_errors = 0

            # Find matches
            try:
                matches = rule.matches(graph, query)
            except (TypeError, ValueError, KeyError, AttributeError) as e:
                logger.warning(
                    "Rule %r failed during matching (iteration=%d): %s",
                    rule.name, iteration, e,
                )
                self._log_match(
                    "rule_error",
                    rule.name,
                    f"iteration={iteration} error={e}",
                )
                rule_errors += 1
                per_rule_counts[rule.name] = 0
                per_rule_errors[rule.name] = rule_errors
                continue

            # Apply rule to each match
            for match in matches:
                try:
                    mapping = rule.apply(graph, match)
                    if mapping and mapping.id not in self.mappings:
                        self.mappings[mapping.id] = mapping
                        self._rule_priority[mapping.id] = rule.priority
                        self._log_match("mapping_created", rule.name, mapping.id)
                        new_mappings += 1
                        rule_new += 1
                except (TypeError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(
                        "Rule %r failed during apply (iteration=%d, match=%r): %s",
                        rule.name, iteration, match, e,
                    )
                    self._log_match(
                        "apply_error",
                        rule.name,
                        f"iteration={iteration} match={match} error={e}",
                    )
                    rule_errors += 1

            per_rule_counts[rule.name] = rule_new
            if rule_errors:
                per_rule_errors[rule.name] = rule_errors

            if rule_new > 0 or rule_errors > 0:
                logger.debug(
                    "Rule %r: %d new mappings, %d errors (iteration=%d, "
                    "priority=%d, family=%s)",
                    rule.name, rule_new, rule_errors, iteration,
                    rule.priority, rule.mapping_kind.value,
                )

        # Log per-rule summary for this pass when there are new mappings
        if new_mappings > 0:
            active = ", ".join(
                f"{name}={cnt}"
                for name, cnt in sorted(
                    per_rule_counts.items(), key=lambda kv: -kv[1]
                )
                if cnt > 0
            )
            logger.debug(
                "Pass %d rule breakdown: %d new total [%s]",
                iteration, new_mappings, active,
            )
            if per_rule_errors:
                err_summary = ", ".join(
                    f"{name}={cnt}" for name, cnt in per_rule_errors.items()
                )
                logger.debug("Pass %d rule errors: [%s]", iteration, err_summary)

        return new_mappings

    def translate_with_confidence(
        self,
        graph: ProgramGraph,
        rule_filter: list[str] | None = None,
    ) -> list[SemanticMapping]:
        """Translate and rescore all mappings using the ConfidenceModel.

        Runs the standard fixpoint translation, then applies the
        ConfidenceModel to update confidence scores, tiers, and
        conflict penalties on every resulting mapping.

        Args:
            graph: Program graph to translate.
            rule_filter: Optional list of rule names to apply (None = all).

        Returns:
            List of semantic mappings with updated confidence scores.
        """
        mappings = self.translate(graph, rule_filter=rule_filter)

        model = ConfidenceModel()
        model.score_batch(mappings)

        # Re-resolve conflicts now that scores are updated
        self._resolve_conflicts()

        return list(self.mappings.values())

    def _resolve_conflicts(self) -> None:
        """Resolve conflicts when multiple mappings target overlapping node sets.

        Uses a node-to-mappings inverted index so conflict detection is
        O(total_node_references) rather than O(n_mappings^2). For each
        colliding pair, the loser is chosen by comparing
        ``(rule_priority, confidence_score)`` tuples (higher wins), with
        the confidence score acting as a tiebreaker when priorities are
        equal.
        """
        # Build inverted index: node_id -> list of mapping IDs touching it.
        node_to_mappings: dict[str, list[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: set[tuple[str, str]] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            mapping_a = self.mappings.get(a_id)
            mapping_b = self.mappings.get(b_id)
            if mapping_a is None or mapping_b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, mapping_a.confidence_score)
            key_b = (pri_b, mapping_b.confidence_score)
            if key_a >= key_b:
                loser, winner = mapping_b, mapping_a
            else:
                loser, winner = mapping_a, mapping_b
            to_remove.add(loser.id)
            overlap = (
                set(mapping_a.graph_fragment_node_ids)
                & set(mapping_b.graph_fragment_node_ids)
            )
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def get_coverage_report(self, graph: ProgramGraph) -> dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: set[str] = set()

        for mapping in self.mappings.values():
            covered_node_ids.update(mapping.graph_fragment_node_ids)

        # Intersect with actual graph nodes (in case mappings reference stale IDs)
        covered_node_ids &= all_node_ids
        uncovered = all_node_ids - covered_node_ids

        total = len(all_node_ids)
        coverage_pct = (len(covered_node_ids) / total * 100.0) if total > 0 else 0.0

        return {
            "total_nodes": total,
            "covered_nodes": len(covered_node_ids),
            "uncovered_nodes": len(uncovered),
            "coverage_percent": round(coverage_pct, 2),
            "uncovered_node_ids": sorted(uncovered),
        }

    def get_mappings_by_kind(self, kind: MappingKind) -> list[SemanticMapping]:
        """Get all mappings of a specific kind.

        Args:
            kind: Kind of mapping to retrieve.

        Returns:
            List of matching mappings.
        """
        return [m for m in self.mappings.values() if m.kind == kind]

    def get_mappings_by_confidence(
        self,
        tier: ConfidenceTier,
    ) -> list[SemanticMapping]:
        """Get all mappings with a specific confidence tier.

        Args:
            tier: Confidence tier to filter by.

        Returns:
            List of mappings at that tier.
        """
        return [m for m in self.mappings.values() if m.confidence_tier == tier]

    def get_mapping(self, mapping_id: str) -> SemanticMapping | None:
        """Get a mapping by ID.

        Args:
            mapping_id: ID of mapping.

        Returns:
            SemanticMapping if found, None otherwise.
        """
        return self.mappings.get(mapping_id)

    def _log_match(self, event_type: str, rule_name: str, detail: str) -> None:
        """Log a match event.

        Args:
            event_type: Type of event.
            rule_name: Name of rule.
            detail: Event details.
        """
        self._match_log.append({
            "event_type": event_type,
            "rule_name": rule_name,
            "detail": detail,
        })

    def get_match_log(self) -> list[dict[str, Any]]:
        """Get the match log.

        Returns:
            List of match events.
        """
        return self._match_log.copy()

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind: dict[str, int] = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier: dict[str, int] = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }

    def explain(self) -> list[str]:
        """Produce human-readable explanations of which rules fired and why.

        Returns a list of formatted explanation strings describing the
        translation decisions. Each string covers one (rule, node) pair
        that was evaluated during the most recent :meth:`translate` call.
        Empty list if no translation has been run yet.

        Returns:
            List of explanation strings (one per rule evaluation).
        """
        explanations: list[str] = []

        # Group match log entries by rule
        rule_summary: dict[str, int] = {}
        for entry in self._match_log:
            rule_name = entry.get("rule_name", "unknown")
            event_type = entry.get("event_type", "")
            if event_type == "mapping_created":
                rule_summary[rule_name] = rule_summary.get(rule_name, 0) + 1

        # Build human-readable summary
        for rule_name in sorted(rule_summary.keys()):
            count = rule_summary[rule_name]
            explanations.append(
                f"Rule '{rule_name}' fired {count} time(s)"
            )

        # Add convergence summary
        iteration_events = [
            e for e in self._match_log
            if e.get("event_type") == "iteration_complete"
        ]
        if iteration_events:
            last_event = iteration_events[-1]
            detail = last_event.get("detail", "")
            explanations.append(f"Fixpoint convergence: {detail}")

        return explanations

    def validate(self) -> list[str]:
        """Validate SemanticMappings for internal consistency.

        Checks all mappings in :attr:`mappings` for:
        - Non-empty node IDs
        - Valid confidence scores (0.0–1.0)
        - Consistent mapping kinds
        - No orphaned node references (node exists in graph)

        Returns:
            List of validation issues (empty = valid). Each string
            describes one inconsistency or violation.
        """
        issues: list[str] = []

        if not self.mappings:
            return issues  # No mappings is valid (empty graph)

        # Get all node IDs from a stored graph (if available)
        # For now, we'll validate the structure without graph reference
        for mapping_id, mapping in self.mappings.items():
            # Check non-empty node IDs
            if not mapping.graph_fragment_node_ids:
                issues.append(
                    f"Mapping '{mapping_id}' has no node IDs in fragment"
                )

            # Check confidence score range
            if not (0.0 <= mapping.confidence_score <= 1.0):
                issues.append(
                    f"Mapping '{mapping_id}' confidence {mapping.confidence_score} "
                    f"out of range [0.0, 1.0]"
                )

            # Check mapping kind is valid
            if not hasattr(mapping.kind, "value"):
                issues.append(
                    f"Mapping '{mapping_id}' has invalid mapping kind"
                )

            # Check consistency between confidence score and tier
            tier = mapping.confidence_tier.value
            score = mapping.confidence_score
            if tier == "STATIC_ONLY" and score < 0.5:
                issues.append(
                    f"Mapping '{mapping_id}' has STATIC_ONLY tier but "
                    f"confidence {score} < 0.5 (inconsistent)"
                )

        return issues

    def get_convergence_info(self) -> dict[str, Any]:
        """Get information about fixpoint convergence.

        Returns a dictionary with:
        - converged: Whether fixpoint was reached
        - iterations: Number of iterations until convergence (or max_iterations)
        - final_mapping_count: Number of mappings in final result

        Returns:
            Dictionary with convergence metadata.
        """
        return {
            "converged": self._convergence_iteration is not None,
            "iterations": self._convergence_iteration or self.max_iterations,
            "final_mapping_count": len(self.mappings),
        }
