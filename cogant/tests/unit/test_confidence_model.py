"""Deep tests for :class:`cogant.translate.confidence.ConfidenceModel`.

The legacy ``test_confidence.py`` file tests a conceptual dict-based
confidence idea that has no relationship to the real ``ConfidenceModel``
in the codebase. This module tests the actual class against
:class:`SemanticMapping` instances, covering: the base scoring formula,
diversity bonus, tier promotion logic (including every branch of
:meth:`determine_confidence_tier`), conflict detection, batch updates,
filtering helpers, and the scoring-report aggregator.
"""

from __future__ import annotations

import pytest

from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)
from cogant.translate.confidence import ConfidenceModel

# ----------------------------------------------------------------- fixtures --


def _mapping(
    mid: str = "m1",
    kind: MappingKind = MappingKind.HIDDEN_STATE,
    provenance: list | None = None,
    parser_certainty: float = 1.0,
    evidence_diversity: float = 0.0,
    conflict_penalties: list | None = None,
) -> SemanticMapping:
    return SemanticMapping(
        id=mid,
        kind=kind,
        graph_fragment_node_ids=["n1"],
        semantic_label="test",
        description="test mapping",
        confidence_score=0.0,
        confidence_tier=ConfidenceTier.STATIC_ONLY,
        provenance=list(provenance or []),
        evidence_count=len(provenance or []),
        parser_certainty=parser_certainty,
        evidence_diversity=evidence_diversity,
        conflict_penalties=list(conflict_penalties or []),
    )


def _pr(source: str, confidence: float) -> ProvenanceRecord:
    return ProvenanceRecord(source=source, confidence=confidence)


# --------------------------------------------------------- compute_confidence


class TestComputeConfidenceScore:
    def test_empty_provenance_returns_zero(self):
        m = _mapping(provenance=[])
        assert ConfidenceModel().compute_confidence_score(m) == 0.0

    def test_average_evidence_only(self):
        m = _mapping(
            provenance=[_pr("static_analysis", 0.8), _pr("static_analysis", 0.6)],
            parser_certainty=1.0,
        )
        # avg 0.7, no diversity, no conflict → 0.7
        score = ConfidenceModel().compute_confidence_score(m)
        assert score == pytest.approx(0.7)

    def test_parser_certainty_multiplier(self):
        m = _mapping(provenance=[_pr("static_analysis", 0.8)], parser_certainty=0.5)
        assert ConfidenceModel().compute_confidence_score(m) == pytest.approx(0.4)

    def test_diversity_bonus(self):
        m = _mapping(
            provenance=[_pr("static_analysis", 0.5)],
            parser_certainty=1.0,
            evidence_diversity=1.0,
        )
        # (0.5 + 0.1) * 1.0 - 0 = 0.6
        assert ConfidenceModel().compute_confidence_score(m) == pytest.approx(0.6)

    def test_conflict_penalty_applied(self):
        m = _mapping(
            provenance=[_pr("static_analysis", 0.9)],
            parser_certainty=1.0,
            conflict_penalties=[1.0, 1.0],  # 2 * 0.05 = 0.1
        )
        assert ConfidenceModel().compute_confidence_score(m) == pytest.approx(0.8)

    def test_score_clamped_to_zero_one(self):
        low = _mapping(
            provenance=[_pr("static_analysis", 0.1)],
            parser_certainty=1.0,
            conflict_penalties=[10, 10, 10],
        )
        assert ConfidenceModel().compute_confidence_score(low) == 0.0
        high = _mapping(
            provenance=[_pr("static_analysis", 0.99)],
            parser_certainty=1.0,
            evidence_diversity=10.0,
        )
        assert ConfidenceModel().compute_confidence_score(high) == 1.0

    def test_alias_compute_matches(self):
        cm = ConfidenceModel()
        m = _mapping(provenance=[_pr("static_analysis", 0.75)])
        assert cm.compute(m) == cm.compute_confidence_score(m)


# -------------------------------------------------------------- tier promotion


class TestDetermineConfidenceTier:
    def test_human_beats_everything(self):
        m = _mapping(provenance=[_pr("static_analysis", 0.3), _pr("human_review", 0.9)])
        tier = ConfidenceModel().determine_confidence_tier(m)
        assert tier == ConfidenceTier.HUMAN_REVIEWED

    def test_static_plus_runtime_meets_threshold(self):
        m = _mapping(provenance=[_pr("static_analysis", 0.9), _pr("runtime_trace", 0.9)])
        cm = ConfidenceModel()
        tier = cm.determine_confidence_tier(m, score=0.9)
        assert tier == ConfidenceTier.STATIC_PLUS_RUNTIME

    def test_static_plus_runtime_falls_back_to_static_only(self):
        m = _mapping(provenance=[_pr("static_analysis", 0.6), _pr("runtime_trace", 0.6)])
        cm = ConfidenceModel()
        # score below STATIC_PLUS_RUNTIME_THRESHOLD (0.65) but ≥ STATIC_ONLY (0.5)
        tier = cm.determine_confidence_tier(m, score=0.55)
        assert tier == ConfidenceTier.STATIC_ONLY

    def test_runtime_only(self):
        m = _mapping(provenance=[_pr("dynamic_trace", 0.5)])
        tier = ConfidenceModel().determine_confidence_tier(m, score=0.5)
        assert tier == ConfidenceTier.RUNTIME_ONLY

    def test_static_only_threshold(self):
        m = _mapping(provenance=[_pr("static_analysis", 0.6)])
        tier = ConfidenceModel().determine_confidence_tier(m, score=0.6)
        assert tier == ConfidenceTier.STATIC_ONLY

    def test_below_all_thresholds_default(self):
        m = _mapping(provenance=[_pr("static_analysis", 0.1)])
        tier = ConfidenceModel().determine_confidence_tier(m, score=0.1)
        assert tier == ConfidenceTier.STATIC_ONLY  # default fallback

    def test_score_recomputed_when_none(self):
        m = _mapping(provenance=[_pr("static_analysis", 0.9)], parser_certainty=1.0)
        tier = ConfidenceModel().determine_confidence_tier(m)
        assert tier == ConfidenceTier.STATIC_ONLY


# ------------------------------------------------------------ diversity score


class TestScoreEvidenceDiversity:
    def test_empty_returns_zero(self):
        assert ConfidenceModel().score_evidence_diversity(_mapping(provenance=[])) == 0.0

    def test_single_source_full_normalization(self):
        m = _mapping(provenance=[_pr("static_analysis", 0.5)])
        assert ConfidenceModel().score_evidence_diversity(m) == pytest.approx(1.0)

    def test_two_distinct_sources(self):
        m = _mapping(provenance=[_pr("static_analysis", 0.5), _pr("runtime_trace", 0.5)])
        # unique=2, max_unique=min(2,5)=2 → 1.0
        assert ConfidenceModel().score_evidence_diversity(m) == pytest.approx(1.0)

    def test_duplicate_sources_lower(self):
        m = _mapping(
            provenance=[
                _pr("static_analysis", 0.5),
                _pr("static_analysis", 0.7),
                _pr("runtime_trace", 0.6),
            ]
        )
        # unique=2, max_unique=min(3,5)=3 → 0.667
        assert ConfidenceModel().score_evidence_diversity(m) == pytest.approx(2 / 3)


# ------------------------------------------------------------ conflict detect


class TestDetectConflicts:
    def test_no_conflict_single_provenance(self):
        m = _mapping(provenance=[_pr("static_analysis", 0.9)])
        assert ConfidenceModel().detect_conflicts(m) == []

    def test_no_conflict_similar_confidences(self):
        m = _mapping(
            provenance=[
                _pr("static_analysis", 0.8),
                _pr("static_analysis", 0.75),
            ]
        )
        assert ConfidenceModel().detect_conflicts(m) == []

    def test_divergence_penalty(self):
        m = _mapping(
            provenance=[
                _pr("static_analysis", 0.9),
                _pr("static_analysis", 0.2),
            ]
        )
        # 0.9 - 0.2 = 0.7 > 0.3 → 0.1 penalty
        assert 0.1 in ConfidenceModel().detect_conflicts(m)

    def test_static_dynamic_disagreement(self):
        m = _mapping(
            provenance=[
                _pr("static_analysis", 0.9),
                _pr("dynamic_trace", 0.3),
            ]
        )
        penalties = ConfidenceModel().detect_conflicts(m)
        # divergence (0.6>0.3) → 0.1; static_dynamic disagreement (0.6>0.25) → 0.15
        assert 0.1 in penalties
        assert 0.15 in penalties

    def test_runtime_source_treated_as_dynamic(self):
        m = _mapping(
            provenance=[
                _pr("static_analysis", 0.9),
                _pr("runtime_probe", 0.3),
            ]
        )
        penalties = ConfidenceModel().detect_conflicts(m)
        assert 0.15 in penalties


# ----------------------------------------------------------- update + report


class TestUpdateAndReport:
    def test_update_mapping_rewrites_all_fields(self):
        cm = ConfidenceModel()
        m = _mapping(
            provenance=[
                _pr("static_analysis", 0.8),
                _pr("runtime_trace", 0.75),
            ],
            parser_certainty=1.0,
        )
        cm.update_mapping_confidence(m)
        assert m.evidence_count == 2
        assert m.evidence_diversity == pytest.approx(1.0)
        assert 0.0 <= m.confidence_score <= 1.0
        assert isinstance(m.confidence_tier, ConfidenceTier)
        assert cm._scoring_log and cm._scoring_log[0]["mapping_id"] == "m1"

    def test_score_batch(self):
        cm = ConfidenceModel()
        ms = [_mapping(mid=f"m{i}", provenance=[_pr("static_analysis", 0.8)]) for i in range(3)]
        cm.score_batch(ms)
        assert len(cm._scoring_log) == 3
        assert all(m.confidence_score > 0 for m in ms)

    def test_filter_high_and_low(self):
        cm = ConfidenceModel()
        hi = _mapping(mid="hi", provenance=[_pr("static_analysis", 0.9)])
        lo = _mapping(mid="lo", provenance=[_pr("static_analysis", 0.3)])
        cm.update_mapping_confidence(hi)
        cm.update_mapping_confidence(lo)
        high = cm.get_high_confidence_mappings([hi, lo], threshold=0.7)
        low = cm.get_low_confidence_mappings([hi, lo], threshold=0.6)
        assert high == [hi]
        assert low == [lo]

    def test_get_conflicted_mappings(self):
        cm = ConfidenceModel()
        clean = _mapping(mid="c", provenance=[_pr("static_analysis", 0.8)])
        dirty = _mapping(
            mid="d",
            provenance=[
                _pr("static_analysis", 0.9),
                _pr("static_analysis", 0.2),
            ],
        )
        cm.update_mapping_confidence(clean)
        cm.update_mapping_confidence(dirty)
        conflicted = cm.get_conflicted_mappings([clean, dirty])
        assert conflicted == [dirty]

    def test_scoring_report_empty(self):
        cm = ConfidenceModel()
        assert cm.get_scoring_report() == {"total_scored": 0}

    def test_scoring_report_aggregate(self):
        cm = ConfidenceModel()
        cm.score_batch(
            [
                _mapping(mid="a", provenance=[_pr("static_analysis", 0.9)]),
                _mapping(mid="b", provenance=[_pr("static_analysis", 0.3)]),
                _mapping(mid="c", provenance=[_pr("static_analysis", 0.6)]),
            ]
        )
        report = cm.get_scoring_report()
        assert report["total_scored"] == 3
        assert 0.0 < report["average_confidence"] < 1.0
        assert report["min_confidence"] <= report["max_confidence"]
        assert report["average_evidence_count"] == pytest.approx(1.0)
        assert "tier_distribution" in report

    def test_clear_log(self):
        cm = ConfidenceModel()
        cm.score_batch([_mapping(provenance=[_pr("static_analysis", 0.5)])])
        assert cm._scoring_log
        cm.clear_log()
        assert cm._scoring_log == []
