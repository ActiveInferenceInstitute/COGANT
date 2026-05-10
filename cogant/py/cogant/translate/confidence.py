"""Confidence scoring model for COGANT semantic mappings.

Overview
========

This module implements the confidence layer that sits between
COGANT's translation rules (``cogant.translate.rules.*``) and the
state-space / GNN consumers downstream. Every :class:`SemanticMapping`
emitted by a rule carries (i) a continuous **confidence score** in
``[0, 1]`` and (ii) a discrete **confidence tier** drawn from
:class:`ConfidenceTier`. Both are produced by :class:`ConfidenceModel`
and form the canonical signal that downstream code (state-space
compilation, conflict resolution, GNN matrix synthesis) uses to decide
whether a mapping is trustworthy enough to keep, surface for review,
or discard.

The model is deliberately *parametric* and *transparent*: every
threshold is a class-level constant or a per-method default, every
constant has an inline rationale, and every empirically-tunable
constant is annotated with a ``TODO(calibration)`` marker linking it
to the 20-repo calibration plan. See
``docs/reference/calibration_guide.md`` for the corpus, methodology,
and per-threshold sweep ranges; see ``docs/evaluation/CALIBRATION.md``
for the parameter registry; see ``docs/evaluation/MUTATION_REPORT.md``
for the mutation-testing audit (item M9 covers the boundary semantics
of this module).

Confidence-tier model
=====================

COGANT distinguishes **four** tiers along an evidence-quality axis:

================================  =====  ================================================
Tier (``ConfidenceTier`` value)   Floor  Meaning
================================  =====  ================================================
``STATIC_ONLY``                   0.50   Static analysis only (AST / tree-sitter); the
                                         baseline tier when no runtime evidence exists.
``RUNTIME_ONLY``                  0.40   Runtime / dynamic-trace evidence with no static
                                         corroboration. The floor is intentionally below
                                         ``STATIC_ONLY`` to reflect a ``-0.10``
                                         *dynamic-noise discount*: traces are noisier
                                         than AST edges, so we accept them at a lower
                                         absolute score.
``STATIC_PLUS_RUNTIME``           0.65   Both static and runtime evidence present. The
                                         floor is ``+0.15`` above ``STATIC_ONLY`` — a
                                         *corroboration bonus* — so corroborated mappings
                                         must clear a strictly higher bar than either
                                         source on its own.
``HUMAN_REVIEWED``                0.90   Reviewed and approved by a human; aligned with
                                         the *strong-consensus* band from classical
                                         meta-analysis reporting conventions.
================================  =====  ================================================

The "three-tier model" referred to in design discussions is the
*evidence-source* sub-hierarchy (``STATIC_ONLY``, ``RUNTIME_ONLY``,
``STATIC_PLUS_RUNTIME``); ``HUMAN_REVIEWED`` is an orthogonal override
that always wins regardless of computed score (see
:meth:`ConfidenceModel.determine_confidence_tier`).

Threshold table
---------------

The following table summarises every numeric knob owned by this
module. All values are *principled defaults* (motivated by convention
or algebraic rationale, not yet empirically fit) unless otherwise
noted.

==========================================  =====  ==============================  ==========================
Constant                                    Value  Sweep range                     Calibration marker
==========================================  =====  ==============================  ==========================
``STATIC_ONLY_THRESHOLD``                   0.50   ``{0.4, 0.5, 0.55, 0.6}``       line ~40 (class scope)
``STATIC_PLUS_RUNTIME_THRESHOLD``           0.65   ``{0.55, 0.6, 0.65, 0.7}``      line ~40 (class scope)
``RUNTIME_ONLY_THRESHOLD``                  0.40   ``{0.3, 0.35, 0.4, 0.45}``      line ~40 (class scope)
``HUMAN_REVIEWED_THRESHOLD``                0.90   ``{0.85, 0.9, 0.95}``           line ~40 (class scope)
``diversity_bonus`` multiplier              0.10   ``{0.05, 0.10, 0.15, 0.20}``    :meth:`compute_confidence_score`
``conflict_penalty`` per-conflict           0.05   ``{0.02, 0.05, 0.08, 0.10}``    :meth:`compute_confidence_score`
divergence-flag spread                      0.30   ``{0.2, 0.3, 0.4}``             :meth:`detect_conflicts`
divergence penalty (mild)                   0.10   ``{0.05, 0.10, 0.15}``          :meth:`detect_conflicts`
static-vs-dynamic disagreement spread       0.25   ``{0.15, 0.20, 0.25, 0.30}``    :meth:`detect_conflicts`
static-vs-dynamic disagreement penalty      0.15   ``{0.10, 0.15, 0.20}``          :meth:`detect_conflicts`
``get_high_confidence_mappings`` default    0.70   ``{0.65, 0.70, 0.75, 0.80}``    :meth:`get_high_confidence_mappings`
``get_low_confidence_mappings`` default     0.60   ``{0.50, 0.55, 0.60, 0.65}``    :meth:`get_low_confidence_mappings`
unique-source cap (diversity normaliser)    5      not calibrated (taxonomy-fixed) :meth:`score_evidence_diversity`
==========================================  =====  ==============================  ==========================

Eight of these knobs carry a ``TODO(calibration)`` marker in this
file (see ``docs/reference/calibration_guide.md``, *Confidence
combiner* section, for the resolution recipe).

Calibration methodology (summary)
=================================

Calibration here means **threshold tuning against a labelled corpus**,
*not* model training in the machine-learning sense. The model itself
(linear blend of evidence terms) is held fixed; only the scalar
constants in the table above are swept. The procedure is:

1. **Corpus.** Twenty repositories under
   ``cogant/tests/fixtures/repos/`` (Python + JS/TS, balanced
   small/medium/large). Each repo has a hand-labelled gold-standard
   set of correct mappings under ``evaluation/gold_standards/`` (TBD;
   see ``CALIBRATION.md`` §4).
2. **Sweep.** For each constant, run COGANT end-to-end across the
   corpus with the constant pinned to each candidate value in its
   sweep range; collect the resulting :class:`SemanticMapping`
   population.
3. **Score.** Compute precision / recall / F1 against the gold
   labels, plus the tier-confusion matrix. For continuous parameters
   (e.g. ``diversity_bonus``) report the L2 error of the score
   distribution against an L1-normalised target.
4. **Pick.** Choose the value at the elbow of the F1 curve. Tie-break
   in favour of recall for ``RUNTIME_ONLY_THRESHOLD`` (we want noisy
   traces to surface for review) and in favour of precision for
   ``STATIC_PLUS_RUNTIME_THRESHOLD`` (we want corroborated mappings to
   be trustworthy by default).
5. **Document.** Replace the ``TODO(calibration)`` annotation with
   ``empirically validated — see CALIBRATION.md §X`` and update the
   manuscript supplement with the sweep curve.

Public surface
==============

The module exports a single class, :class:`ConfidenceModel`. The
relevant *types* are imported from :mod:`cogant.schemas.semantic`:

* :class:`SemanticMapping` — the canonical mapping dataclass (graph
  fragment + semantic label + ``provenance``, ``evidence_count``,
  ``evidence_diversity``, ``parser_certainty``, ``conflict_penalties``,
  ``confidence_score``, ``confidence_tier``). This is the input to
  every public method on :class:`ConfidenceModel` and is mutated
  in-place by :meth:`ConfidenceModel.update_mapping_confidence`.
* :class:`ConfidenceTier` — the four-tier ``StrEnum`` described above.
* :class:`ProvenanceRecord` — one piece of evidence (``source``,
  ``timestamp``, ``metadata``, per-source ``confidence``). Every
  :class:`SemanticMapping` carries a ``list[ProvenanceRecord]``.

Note on naming: ``cogant.types.ConfidenceScore`` is a ``float`` type
alias for documentation purposes (range ``[0.0, 1.0]``); it is **not**
a separate dataclass. The actual confidence data lives on
:class:`SemanticMapping` (fields ``confidence_score`` and
``confidence_tier``); this module's job is to compute those fields.

End-to-end flow of ``compute_confidence_score``
===============================================

For a mapping ``m`` with ``len(m.provenance) == n``:

1. **Empty-evidence guard.** If ``n == 0`` the score is ``0.0`` —
   un-evidenced mappings are not trusted at all.
2. **Evidence base.** ``avg_evidence = mean(p.confidence for p in
   m.provenance)``. Unweighted mean rather than max so that adding
   weak corroborating evidence does not artificially inflate a strong
   primary source.
3. **Diversity bonus.** ``diversity_bonus = m.evidence_diversity *
   0.10``. ``evidence_diversity`` is precomputed by
   :meth:`score_evidence_diversity` as ``unique_sources /
   min(n, 5)``, capped at the five-label evidence taxonomy. The
   ``0.10`` multiplier is sized so that maximum diversity (1.0)
   contributes exactly one tier-gap of lift (the
   ``STATIC_ONLY``→``STATIC_PLUS_RUNTIME`` gap is 0.15, and a lone
   diversity bonus must not overshoot it on its own).
4. **Parser-certainty discount.** ``certainty_factor =
   m.parser_certainty``. This is a multiplicative reliability discount
   from the underlying parser (≈0.95 for full Python AST,
   ≈0.80 for the tree-sitter fallback band). Applying it
   *before* the conflict penalty is intentional: a noisy parser
   should reduce both the evidence base and any diversity bonus, but
   conflicts (which are signal, not noise) survive the discount.
5. **Conflict penalty.** ``conflict_penalty =
   sum(m.conflict_penalties) * 0.05``. The list is precomputed by
   :meth:`detect_conflicts` and contains one entry per detected
   conflict (``0.10`` for spread divergence, ``0.15`` for
   static-vs-dynamic disagreement). The ``0.05`` multiplier means two
   typical conflicts (~``0.10`` total before multiplication) roughly
   cancel a full diversity bonus.
6. **Compose and clamp.**
   ``confidence = (avg_evidence + diversity_bonus) * certainty_factor
   - conflict_penalty``, then clamped to ``[0, 1]``.

The resulting score feeds :meth:`determine_confidence_tier`, which
applies the four-tier decision tree:

* ``has_human`` → ``HUMAN_REVIEWED`` (overrides everything).
* ``has_static and has_dynamic`` → ``STATIC_PLUS_RUNTIME`` if
  ``score >= STATIC_PLUS_RUNTIME_THRESHOLD``, otherwise fall through
  to ``STATIC_ONLY`` if it meets ``STATIC_ONLY_THRESHOLD``.
* ``has_dynamic and not has_static`` → ``RUNTIME_ONLY`` if
  ``score >= RUNTIME_ONLY_THRESHOLD``.
* ``has_static`` → ``STATIC_ONLY`` if ``score >=
  STATIC_ONLY_THRESHOLD``.
* Otherwise → ``STATIC_ONLY`` (lowest-tier fallback; the mapping is
  retained but flagged for downstream review).

:meth:`update_mapping_confidence` orchestrates all of the above:
counts evidence, computes diversity, detects conflicts, computes the
score, assigns the tier, and appends a record to the internal scoring
log (which feeds :meth:`get_scoring_report`). :meth:`score_batch` is a
trivial loop over :meth:`update_mapping_confidence` for ergonomic
batch processing.

Cross-references
================

* ``docs/reference/calibration_guide.md`` — methodology, sweep
  recipes, and resolution checklist for every ``TODO(calibration)``
  marker in this module.
* ``docs/evaluation/CALIBRATION.md`` — repository-wide parameter
  registry (§2.3 covers this module specifically).
* ``docs/evaluation/MUTATION_REPORT.md`` — boundary-semantics audit
  (item M9 covers the ``>=`` / ``>`` decisions in the tier
  decision tree).
* :mod:`cogant.translate.rules` — the rules whose mappings consume
  this module's output.
* :mod:`cogant.statespace.variables` — the downstream consumer that
  collapses the four tiers into the coarser ``ConfidenceLevel``
  categorical view.
"""

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
    STATIC_ONLY_THRESHOLD = 0.5  # principled default
    STATIC_PLUS_RUNTIME_THRESHOLD = 0.65  # principled default (+0.15 corroboration bonus)
    RUNTIME_ONLY_THRESHOLD = 0.4  # principled default (-0.1 dynamic-noise discount)
    HUMAN_REVIEWED_THRESHOLD = 0.9  # principled default (strong-consensus band)

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
                dynamic_conf = sum(
                    p.confidence
                    for p in mapping.provenance
                    if "dynamic" in p.source or "runtime" in p.source
                )

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
        self._scoring_log.append(
            {
                "mapping_id": mapping.id,
                "confidence_score": mapping.confidence_score,
                "confidence_tier": mapping.confidence_tier.value,
                "evidence_count": mapping.evidence_count,
            }
        )

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
            "average_evidence_count": sum(evidence_counts) / len(evidence_counts)
            if evidence_counts
            else 0,
            "tier_distribution": dict(tiers),
        }

    def clear_log(self) -> None:
        """Clear the scoring log."""
        self._scoring_log.clear()
