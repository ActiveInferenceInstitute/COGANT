"""Unit tests for the built-in ``SemanticMapping.compute_confidence`` method
and the ``ConfidenceTier`` / ``ProvenanceRecord`` value objects.

These tests complement ``test_confidence_model.py`` (which covers the
higher-level ``ConfidenceModel`` orchestrator) by pinning down the
dataclass-level confidence math that the model ultimately delegates to.

No dicts — every assertion touches the real ``SemanticMapping`` class.
"""

from __future__ import annotations

import pytest

from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    ProvenanceRecord,
    SemanticMapping,
)

pytestmark = pytest.mark.unit


# ----------------------------------------------------------------------- helpers


def _make_mapping(
    mid: str = "mapping:test",
    kind: MappingKind = MappingKind.HIDDEN_STATE,
    provenance: list[ProvenanceRecord] | None = None,
    parser_certainty: float = 1.0,
    evidence_diversity: float = 0.0,
    conflict_penalties: list[float] | None = None,
) -> SemanticMapping:
    return SemanticMapping(
        id=mid,
        kind=kind,
        graph_fragment_node_ids=["n1"],
        semantic_label="label",
        description="a mapping",
        provenance=list(provenance or []),
        parser_certainty=parser_certainty,
        evidence_diversity=evidence_diversity,
        conflict_penalties=list(conflict_penalties or []),
    )


# ------------------------------------------------------------------- construction


class TestSemanticMappingConstruction:
    """Tests for SemanticMapping construction and defaults."""

    def test_minimal_construction(self) -> None:
        m = SemanticMapping(id="m1", kind=MappingKind.OBSERVATION)
        assert m.id == "m1"
        assert m.kind is MappingKind.OBSERVATION
        assert m.confidence_score == 0.0
        assert m.confidence_tier is ConfidenceTier.STATIC_ONLY
        assert m.provenance == []
        assert m.evidence_count == 0
        assert m.status == "auto_proposed"

    def test_equality_by_id(self) -> None:
        m1 = SemanticMapping(id="same", kind=MappingKind.ACTION)
        m2 = SemanticMapping(id="same", kind=MappingKind.POLICY)
        m3 = SemanticMapping(id="other", kind=MappingKind.ACTION)
        assert m1 == m2
        assert m1 != m3
        assert hash(m1) == hash(m2)

    def test_mapping_kind_values(self) -> None:
        # Every enum member is a valid string for the dataclass field.
        for kind in MappingKind:
            m = SemanticMapping(id=f"id:{kind.value}", kind=kind)
            assert m.kind is kind

    def test_confidence_tier_string_values(self) -> None:
        assert ConfidenceTier.STATIC_ONLY.value == "static_only"
        assert ConfidenceTier.STATIC_PLUS_RUNTIME.value == "static_plus_runtime"
        assert ConfidenceTier.RUNTIME_ONLY.value == "runtime_only"
        assert ConfidenceTier.HUMAN_REVIEWED.value == "human_reviewed"


# ---------------------------------------------------------- compute_confidence


class TestComputeConfidence:
    """Tests for ``SemanticMapping.compute_confidence``."""

    def test_empty_provenance_returns_zero(self) -> None:
        m = _make_mapping(provenance=[])
        assert m.compute_confidence() == 0.0

    def test_single_perfect_evidence(self) -> None:
        m = _make_mapping(
            provenance=[ProvenanceRecord(source="static_analysis", confidence=1.0)],
            parser_certainty=1.0,
        )
        assert m.compute_confidence() == pytest.approx(1.0)

    def test_averaged_evidence(self) -> None:
        m = _make_mapping(
            provenance=[
                ProvenanceRecord(source="static_analysis", confidence=0.8),
                ProvenanceRecord(source="static_analysis", confidence=0.4),
            ],
            parser_certainty=1.0,
        )
        # avg 0.6, no diversity, no conflicts → 0.6
        assert m.compute_confidence() == pytest.approx(0.6)

    def test_parser_certainty_scales_confidence(self) -> None:
        m = _make_mapping(
            provenance=[ProvenanceRecord(source="static_analysis", confidence=0.8)],
            parser_certainty=0.5,
        )
        # (0.8 + 0) * 0.5 = 0.4
        assert m.compute_confidence() == pytest.approx(0.4)

    def test_diversity_bonus_added_before_scaling(self) -> None:
        m = _make_mapping(
            provenance=[ProvenanceRecord(source="static_analysis", confidence=0.5)],
            parser_certainty=1.0,
            evidence_diversity=1.0,
        )
        # (0.5 + 0.1) * 1.0 - 0 = 0.6
        assert m.compute_confidence() == pytest.approx(0.6)

    def test_conflict_penalty_subtracted(self) -> None:
        m = _make_mapping(
            provenance=[ProvenanceRecord(source="static_analysis", confidence=0.9)],
            parser_certainty=1.0,
            conflict_penalties=[1.0, 1.0, 1.0],  # 3 * 0.05 = 0.15
        )
        assert m.compute_confidence() == pytest.approx(0.75)

    def test_confidence_clamped_to_zero(self) -> None:
        m = _make_mapping(
            provenance=[ProvenanceRecord(source="static_analysis", confidence=0.1)],
            parser_certainty=1.0,
            conflict_penalties=[100, 100],
        )
        assert m.compute_confidence() == 0.0

    def test_confidence_clamped_to_one(self) -> None:
        m = _make_mapping(
            provenance=[ProvenanceRecord(source="static_analysis", confidence=0.99)],
            parser_certainty=1.0,
            evidence_diversity=5.0,  # huge bonus
        )
        assert m.compute_confidence() == 1.0


# ----------------------------------------------------------------- provenance


class TestProvenanceRecord:
    """Tests for the ProvenanceRecord dataclass."""

    def test_provenance_defaults(self) -> None:
        p = ProvenanceRecord(source="static_analysis")
        assert p.source == "static_analysis"
        assert p.confidence == 0.5
        assert p.metadata == {}
        assert p.timestamp is not None

    def test_provenance_with_metadata(self) -> None:
        p = ProvenanceRecord(
            source="runtime_trace",
            confidence=0.92,
            metadata={"test_id": "t7", "run": 3},
        )
        assert p.confidence == 0.92
        assert p.metadata["test_id"] == "t7"
        assert p.metadata["run"] == 3
