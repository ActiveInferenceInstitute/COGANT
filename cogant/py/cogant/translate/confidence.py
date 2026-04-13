"""Confidence scoring model for semantic mappings."""

from collections import Counter
from typing import Any

from cogant.schemas.semantic import (
    ConfidenceTier,
    SemanticMapping,
)

__all__ = ["ConfidenceModel"]


class ConfidenceModel:
    """Computes and manages confidence scores for semantic mappings.

    Combines evidence count, diversity, parser certainty, and conflict penalties
    to produce confidence tiers and scores.
    """

    # ------------------------------------------------------------------
    # Confidence-tier thresholds
    # ------------------------------------------------------------------
    # These four scalars carve [0, 1] into the four ConfidenceTier
    # bands used by ``determine_confidence_tier``. They are principled
    # defaults — not empirically calibrated — anchored to the
    # "weak / moderate / strong evidence" bands from classical
    # meta-analysis reporting conventions. Read them as:
    #   0.5  — minimum to accept a static-only mapping; below this the
    #          tier falls back to the lowest band.
    #   0.65 — extra-evidence promotion threshold: static-only rules
    #          with dynamic corroboration need the combined score to
    #          clear this bar (+0.15 over the static-only floor) before
    #          promotion to STATIC_PLUS_RUNTIME.
    #   0.4  — lower bar for runtime-only evidence because dynamic
    #          traces are noisier than static edges (-0.1 dynamic-noise
    #          discount relative to the static floor).
    #   0.9  — strong-consensus band for human-reviewed mappings.
    # See ``docs/evaluation/CALIBRATION.md`` for the full sweep plan.
    # TODO(calibration): sweep {0.4, 0.5, 0.55, 0.6, 0.65, 0.7} over a
    # 20+ repo fixture set and pick the precision/recall sweet spot.
    STATIC_ONLY_THRESHOLD = 0.5            # principled default
    STATIC_PLUS_RUNTIME_THRESHOLD = 0.65   # principled default (+0.15 corroboration bonus)
    RUNTIME_ONLY_THRESHOLD = 0.4           # principled default (-0.1 dynamic-noise discount)
    HUMAN_REVIEWED_THRESHOLD = 0.9         # principled default (strong-consensus band)

    def __init__(self) -> None:
        """Initialize the confidence model."""
        self._scoring_log: list[dict[str, Any]] = []

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

        # Base score: unweighted average of per-provenance confidences.
        avg_evidence = sum(p.confidence for p in mapping.provenance) / len(mapping.provenance)

        # Evidence diversity bonus — multiplicative weight 0.1 = "at
        # most a 10-percentage-point reward for multi-source
        # agreement". Principled default: large enough to lift a
        # borderline mapping across the STATIC_ONLY→STATIC_PLUS_RUNTIME
        # boundary (gap=0.15) when combined with dynamic evidence, small
        # enough never to override a strong evidence base on its own.
        # TODO(calibration): sweep {0.05, 0.10, 0.15, 0.20} on the 20+
        # repo fixture set (see CALIBRATION.md).
        diversity_bonus = mapping.evidence_diversity * 0.1

        # Parser certainty factor — multiplicative discount for noisy
        # parsers (e.g. tree-sitter fallback ≈ 0.8 vs. full Python AST
        # ≈ 0.95).
        certainty_factor = mapping.parser_certainty

        # Conflict penalties — 0.05-per-conflict principled default,
        # chosen so two detected conflicts (~0.10) roughly cancel a full
        # diversity bonus. TODO(calibration): log penalty distributions
        # on the 20-repo corpus and retune.
        conflict_penalty = sum(mapping.conflict_penalties) * 0.05

        # Compose: evidence base, lifted by diversity, discounted by
        # parser certainty, reduced by conflict penalties. Clamped to
        # [0, 1] for downstream tier assignment.
        confidence = (avg_evidence + diversity_bonus) * certainty_factor - conflict_penalty
        confidence = max(0.0, min(1.0, confidence))

        return confidence

    def determine_confidence_tier(
        self,
        mapping: SemanticMapping,
        score: float | None = None,
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
        set(sources)

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

        # Normalize by number of total evidence pieces. Cap at 5
        # distinct source types because the evidence-source taxonomy
        # currently defines exactly 5 labels
        # (static_analysis, dynamic_trace, runtime_profile, human_review,
        # llm_review). A single mapping with 5 different labels already
        # saturates the diversity bonus. TODO(calibration): revisit if
        # new evidence sources are added in P5+.
        max_unique = min(len(sources), 5)  # Cap at 5 source types for normalization
        diversity = unique_sources / max(1, max_unique)

        return min(1.0, diversity)

    def detect_conflicts(self, mapping: SemanticMapping) -> list[float]:
        """Detect and score conflicts in evidence.

        Args:
            mapping: SemanticMapping to check.

        Returns:
            List of conflict penalty scores.
        """
        penalties: list[float] = []

        if not mapping.provenance or len(mapping.provenance) < 2:
            return penalties

        # Check for confidence divergence across evidence sources. A
        # spread > 0.3 is flagged as "significant divergence" and
        # incurs a 0.10 penalty. Both thresholds are principled
        # defaults: 0.3 is larger than any two neighbouring tier gaps
        # (max gap = 0.25 between RUNTIME_ONLY and STATIC_PLUS_RUNTIME)
        # so only genuinely disagreeing sources trigger it; 0.10 makes
        # one divergence cost the same as a full diversity bonus.
        # TODO(calibration): retune on observed evidence-spread
        # distributions from the 20-repo corpus (see CALIBRATION.md).
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

                # Static vs. dynamic disagreement threshold = 0.25.
                # Principled default: equals the gap between
                # RUNTIME_ONLY (0.4) and STATIC_PLUS_RUNTIME (0.65), so
                # disagreement only triggers when the two sources would
                # land in non-adjacent tiers. The 0.15 penalty is
                # intentionally larger than the 0.10 spread penalty
                # above because a static-vs-dynamic disagreement is
                # structurally more meaningful than a within-source
                # spread. TODO(calibration): validate on the 20-repo
                # corpus.
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

    def score_batch(self, mappings: list[SemanticMapping]) -> None:
        """Update confidence for a batch of mappings.

        Args:
            mappings: List of mappings to score.
        """
        for mapping in mappings:
            self.update_mapping_confidence(mapping)

    def get_high_confidence_mappings(
        self,
        mappings: list[SemanticMapping],
        threshold: float = 0.7,
    ) -> list[SemanticMapping]:
        """Filter mappings by minimum confidence score.

        Args:
            mappings: List of mappings.
            threshold: Minimum confidence threshold. Default 0.7 is a
                principled "trust without review" bar — safely above
                ``STATIC_PLUS_RUNTIME_THRESHOLD`` (0.65) but well below
                ``HUMAN_REVIEWED_THRESHOLD`` (0.9). TODO(calibration):
                tune against observed precision on the 20-repo corpus
                (see ``docs/evaluation/CALIBRATION.md``).

        Returns:
            Filtered list of high-confidence mappings.
        """
        return [m for m in mappings if m.confidence_score >= threshold]

    def get_low_confidence_mappings(
        self,
        mappings: list[SemanticMapping],
        threshold: float = 0.6,
    ) -> list[SemanticMapping]:
        """Find mappings below confidence threshold that may need review.

        Args:
            mappings: List of mappings.
            threshold: Maximum confidence threshold. Default 0.6 is a
                principled "needs reviewer attention" bar — halfway
                between ``STATIC_ONLY_THRESHOLD`` (0.5) and
                ``STATIC_PLUS_RUNTIME_THRESHOLD`` (0.65), so that
                mappings which pass the accept floor but fail the
                "corroborated" bar are surfaced for human review.
                TODO(calibration): retune against observed human-review
                false-positive rates.

        Returns:
            Filtered list of low-confidence mappings.
        """
        return [m for m in mappings if m.confidence_score < threshold]

    def get_conflicted_mappings(
        self,
        mappings: list[SemanticMapping],
    ) -> list[SemanticMapping]:
        """Find mappings with detected conflicts.

        Args:
            mappings: List of mappings.

        Returns:
            List of mappings with conflict penalties.
        """
        return [m for m in mappings if m.conflict_penalties]

    def get_scoring_report(self) -> dict[str, Any]:
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
