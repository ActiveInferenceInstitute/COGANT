"""Translation engine orchestrating rule application over program graphs."""

import logging
from typing import Any, Dict, List, Optional, Set
from abc import ABC, abstractmethod

from cogant.schemas.graph import ProgramGraph
from cogant.schemas.semantic import SemanticMapping, MappingKind, ConfidenceTier
from cogant.graph.queries import GraphQuery
from cogant.translate.confidence import ConfidenceModel

logger = logging.getLogger(__name__)


class TranslationRule(ABC):
    """Base class for translation rules."""

    @abstractmethod
    def matches(self, graph: ProgramGraph, query: GraphQuery) -> List[Dict[str, Any]]:
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
        match: Dict[str, Any],
    ) -> Optional[SemanticMapping]:
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
        """Priority of this rule (higher = applied first). Default 0."""
        return 0


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
        """
        self.rules: List[TranslationRule] = []
        self.mappings: Dict[str, SemanticMapping] = {}
        self._match_log: List[Dict[str, Any]] = []
        self._rule_priority: Dict[str, int] = {}
        self.max_iterations = max_iterations

    def register_rule(self, rule: TranslationRule) -> None:
        """Register a translation rule.

        Args:
            rule: Rule to register.
        """
        self.rules.append(rule)

    def translate(
        self,
        graph: ProgramGraph,
        rule_filter: Optional[List[str]] = None,
    ) -> List[SemanticMapping]:
        """Translate a program graph using registered rules with fixpoint iteration.

        Rules are applied repeatedly until no new mappings emerge (convergence)
        or max_iterations is reached.

        Args:
            graph: Program graph to translate.
            rule_filter: Optional list of rule names to apply (None = all).

        Returns:
            List of semantic mappings discovered.
        """
        self.mappings.clear()
        self._match_log.clear()
        self._rule_priority.clear()

        query = GraphQuery(graph)

        for iteration in range(1, self.max_iterations + 1):
            logger.debug("Fixpoint iteration %d starting (%d existing mappings)",
                         iteration, len(self.mappings))

            new_mappings_this_pass = self._apply_single_pass(
                graph, query, rule_filter=rule_filter, iteration=iteration
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
                break
        else:
            logger.warning(
                "Max iterations (%d) reached without convergence", self.max_iterations
            )

        # Resolve conflicts among overlapping mappings
        self._resolve_conflicts()

        return list(self.mappings.values())

    def _apply_single_pass(
        self,
        graph: ProgramGraph,
        query: GraphQuery,
        rule_filter: Optional[List[str]] = None,
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

        for rule in sorted_rules:
            # Skip if filtered out
            if rule_filter and rule.name not in rule_filter:
                continue

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

        return new_mappings

    def translate_with_confidence(
        self,
        graph: ProgramGraph,
        rule_filter: Optional[List[str]] = None,
    ) -> List[SemanticMapping]:
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
        node_to_mappings: Dict[str, List[str]] = {}
        for mapping in self.mappings.values():
            for node_id in mapping.graph_fragment_node_ids:
                node_to_mappings.setdefault(node_id, []).append(mapping.id)

        # Collect unique colliding pairs via the inverted index.
        conflict_pairs: Set[tuple] = set()
        for mids in node_to_mappings.values():
            if len(mids) < 2:
                continue
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    a, b = mids[i], mids[j]
                    conflict_pairs.add((a, b) if a < b else (b, a))

        to_remove: Set[str] = set()
        for a_id, b_id in conflict_pairs:
            if a_id in to_remove or b_id in to_remove:
                continue
            a = self.mappings.get(a_id)
            b = self.mappings.get(b_id)
            if a is None or b is None:
                continue
            pri_a = self._rule_priority.get(a_id, 0)
            pri_b = self._rule_priority.get(b_id, 0)
            key_a = (pri_a, a.confidence_score)
            key_b = (pri_b, b.confidence_score)
            if key_a >= key_b:
                loser, winner = b, a
            else:
                loser, winner = a, b
            to_remove.add(loser.id)
            overlap = set(a.graph_fragment_node_ids) & set(b.graph_fragment_node_ids)
            self._log_match(
                "conflict_resolved",
                "engine",
                f"removed={loser.id} kept={winner.id} overlap={overlap}",
            )

        for mid in to_remove:
            del self.mappings[mid]

    def get_coverage_report(self, graph: ProgramGraph) -> Dict[str, Any]:
        """Report what percentage of graph nodes received at least one mapping.

        Args:
            graph: The program graph that was translated.

        Returns:
            Dictionary with coverage statistics including total nodes,
            covered nodes, uncovered node IDs, and coverage percentage.
        """
        all_node_ids = set(graph.nodes.keys())
        covered_node_ids: Set[str] = set()

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

    def get_mappings_by_kind(self, kind: MappingKind) -> List[SemanticMapping]:
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
    ) -> List[SemanticMapping]:
        """Get all mappings with a specific confidence tier.

        Args:
            tier: Confidence tier to filter by.

        Returns:
            List of mappings at that tier.
        """
        return [m for m in self.mappings.values() if m.confidence_tier == tier]

    def get_mapping(self, mapping_id: str) -> Optional[SemanticMapping]:
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

    def get_match_log(self) -> List[Dict[str, Any]]:
        """Get the match log.

        Returns:
            List of match events.
        """
        return self._match_log.copy()

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about translations.

        Returns:
            Dictionary with statistics.
        """
        by_kind = {}
        for mapping in self.mappings.values():
            kind = mapping.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

        by_tier = {}
        for mapping in self.mappings.values():
            tier = mapping.confidence_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        return {
            "total_mappings": len(self.mappings),
            "mappings_by_kind": by_kind,
            "mappings_by_confidence_tier": by_tier,
            "rules_registered": len(self.rules),
        }
