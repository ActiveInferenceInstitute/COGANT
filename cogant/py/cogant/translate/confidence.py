"""Confidence scoring model for semantic mappings."""

from typing import Any, Dict, List, Optional
from collections import Counter

from cogant.schemas.semantic import (
    SemanticMapping,
    ConfidenceTier,
    ProvenanceRecord,
)


class ConfidenceModel:
    """Computes and manages confidence scores for semantic mappings.

    Combines evidence count, diversity, parser certainty, and conflict penalties
    to produce confidence tiers and scores.
    """

    # Thresholds for confidence tiers
    STATIC_ONLY_THRESHOLD = 0.5
    STATIC_PLUS_RUNTIME_THRESHOLD = 0.65
    RUNTIME_ONLY_THRESHOLD = 0.4
    HUMAN_REVIEWED_THRESHOLD = 0.9

    def __init__(self):
        """Initialize the confidence model."""
        self._scoring_log: List[Dict[str, Any]] = []

    def compute(self, mapping: SemanticMapping) -> float:
        """Convenience alias for compute_confidence_score.

        Args:
            mapping: SemanticMapping to score.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        return self.compute_confidence_score(mapping)

    def compute_confidence_score(self, mapping: SemanticMapping) -> float:
        """Compute overall confidence score from evidence and metadata.

        Args:
            mapping: SemanticMapping to score.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if not mapping.provenance:
            return 0.0

        # Base score: average of evidence confidence
        avg_evidence = sum(p.confidence for p in mapping.provenance) / len(mapping.provenance)

        # Evidence diversity bonus (max 0.1)
        diversity_bonus = mapping.evidence_diversity * 0.1

        # Parser certainty factor
        certainty_factor = mapping.parser_certainty

        # Conflict penalties (cumulative)
        conflict_penalty = sum(mapping.conflict_penalties) * 0.05

        # Compute confidence
        confidence = (avg_evidence + diversity_bonus) * certainty_factor - conflict_penalty
        confidence = max(0.0, min(1.0, confidence))

        return confidence

    def determine_confidence_tier(
        self,
        mapping: SemanticMapping,
        score: Optional[float] = None,
    ) -> ConfidenceTier:
        """Determine confidence tier based on evidence sources and score.

        Args:
            mapping: SemanticMapping to tier.
            score: Optional precomputed confidence score.

        Returns:
            ConfidenceTier for the mapping.
        """
        if score is None:
            score = self.compute_confidence_score(mapping)

        # Check evidence sources
        sources = [p.source for p in mapping.provenance]
        source_types = set(sources)

        has_static = any("static" in s for s in sources)
        has_dynamic = any("dynamic" in s or "runtime" in s for s in sources)
        has_human = any("human" in s or "review" in s for s in sources)

        # Determine tier
        if has_human:
            return ConfidenceTier.HUMAN_REVIEWED

        if has_static and has_dynamic:
            if score >= self.STATIC_PLUS_RUNTIME_THRESHOLD:
                return ConfidenceTier.STATIC_PLUS_RUNTIME
            # Fallback to lower tier
            if score >= self.STATIC_ONLY_THRESHOLD:
                return ConfidenceTier.STATIC_ONLY

        if has_dynamic and not has_static:
            if score >= self.RUNTIME_ONLY_THRESHOLD:
                return ConfidenceTier.RUNTIME_ONLY

        if has_static:
            if score >= self.STATIC_ONLY_THRESHOLD:
                return ConfidenceTier.STATIC_ONLY

        # Default to lowest tier
        return ConfidenceTier.STATIC_ONLY

    def score_evidence_diversity(self, mapping: SemanticMapping) -> float:
        """Compute diversity score of evidence sources.

        Args:
            mapping: SemanticMapping with provenance.

        Returns:
            Diversity score between 0.0 and 1.0.
        """
        if not mapping.provenance:
            return 0.0

        # Count unique source types
        sources = [p.source for p in mapping.provenance]
        unique_sources = len(set(sources))

        # Normalize by number of total evidence pieces
        max_unique = min(len(sources), 5)  # Cap at 5 source types for normalization
        diversity = unique_sources / max(1, max_unique)

        return min(1.0, diversity)

    def detect_conflicts(self, mapping: SemanticMapping) -> List[float]:
        """Detect and score conflicts in evidence.

        Args:
            mapping: SemanticMapping to check.

        Returns:
            List of conflict penalty scores.
        """
        penalties = []

        if not mapping.provenance or len(mapping.provenance) < 2:
            return penalties

        # Check for confidence divergence
        confidence_values = [p.confidence for p in mapping.provenance]
        max_conf = max(confidence_values)
        min_conf = min(confidence_values)

        if (max_conf - min_conf) > 0.3:
            # Significant divergence
            penalties.append(0.1)

        # Check for conflicting source types
        sources = Counter(p.source for p in mapping.provenance)
        if len(sources) > 1:
            # Multiple source types - check for major conflicts
            static_count = sum(v for k, v in sources.items() if "static" in k)
            dynamic_count = sum(v for k, v in sources.items() if "dynamic" in k or "runtime" in k)

            if static_count > 0 and dynamic_count > 0:
                # Both static and dynamic - check for agreement
                static_conf = sum(p.confidence for p in mapping.provenance if "static" in p.source)
                dynamic_conf = sum(p.confidence for p in mapping.provenance if "dynamic" in p.source or "runtime" in p.source)

                static_avg = static_conf / max(1, static_count)
                dynamic_avg = dynamic_conf / max(1, dynamic_count)

                if abs(static_avg - dynamic_avg) > 0.25:
                    penalties.append(0.15)

        return penalties

    def update_mapping_confidence(self, mapping: SemanticMapping) -> None:
        """Update all confidence fields of a mapping in-place.

        Args:
            mapping: SemanticMapping to update.
        """
        # Count evidence
        mapping.evidence_count = len(mapping.provenance)

        # Compute diversity
        mapping.evidence_diversity = self.score_evidence_diversity(mapping)

        # Detect conflicts
        mapping.conflict_penalties = self.detect_conflicts(mapping)

        # Compute overall score
        mapping.confidence_score = self.compute_confidence_score(mapping)

        # Determine tier
        mapping.confidence_tier = self.determine_confidence_tier(mapping, mapping.confidence_score)

        # Log
        self._scoring_log.append({
            "mapping_id": mapping.id,
            "confidence_score": mapping.confidence_score,
            "confidence_tier": mapping.confidence_tier.value,
            "evidence_count": mapping.evidence_count,
        })

    def score_batch(self, mappings: List[SemanticMapping]) -> None:
        """Update confidence for a batch of mappings.

        Args:
            mappings: List of mappings to score.
        """
        for mapping in mappings:
            self.update_mapping_confidence(mapping)

    def get_high_confidence_mappings(
        self,
        mappings: List[SemanticMapping],
        threshold: float = 0.7,
    ) -> List[SemanticMapping]:
        """Filter mappings by minimum confidence score.

        Args:
            mappings: List of mappings.
            threshold: Minimum confidence threshold.

        Returns:
            Filtered list of high-confidence mappings.
        """
        return [m for m in mappings if m.confidence_score >= threshold]

    def get_low_confidence_mappings(
        self,
        mappings: List[SemanticMapping],
        threshold: float = 0.6,
    ) -> List[SemanticMapping]:
        """Find mappings below confidence threshold that may need review.

        Args:
            mappings: List of mappings.
            threshold: Maximum confidence threshold.

        Returns:
            Filtered list of low-confidence mappings.
        """
        return [m for m in mappings if m.confidence_score < threshold]

    def get_conflicted_mappings(
        self,
        mappings: List[SemanticMapping],
    ) -> List[SemanticMapping]:
        """Find mappings with detected conflicts.

        Args:
            mappings: List of mappings.

        Returns:
            List of mappings with conflict penalties.
        """
        return [m for m in mappings if m.conflict_penalties]

    def get_scoring_report(self) -> Dict[str, Any]:
        """Generate a report of confidence scoring.

        Returns:
            Dictionary with scoring statistics.
        """
        if not self._scoring_log:
            return {"total_scored": 0}

        tiers = Counter(entry["confidence_tier"] for entry in self._scoring_log)
        scores = [entry["confidence_score"] for entry in self._scoring_log]
        evidence_counts = [entry["evidence_count"] for entry in self._scoring_log]

        return {
            "total_scored": len(self._scoring_log),
            "average_confidence": sum(scores) / len(scores) if scores else 0.0,
            "min_confidence": min(scores) if scores else 0.0,
            "max_confidence": max(scores) if scores else 0.0,
            "average_evidence_count": sum(evidence_counts) / len(evidence_counts) if evidence_counts else 0,
            "tier_distribution": dict(tiers),
        }

    def clear_log(self) -> None:
        """Clear the scoring log."""
        self._scoring_log.clear()
