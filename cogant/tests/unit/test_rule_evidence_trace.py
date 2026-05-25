"""Tests for translation rule-evidence trace artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from cogant.schemas.semantic import ConfidenceTier, MappingKind, ProvenanceRecord, SemanticMapping
from cogant.translate.evidence import (
    apply_reviewer_annotations,
    build_rule_evidence_trace,
    calibrate_rule_evidence_trace,
    load_reviewer_annotations,
)


def _mapping(mapping_id: str, *, rule: str, confidence: float) -> SemanticMapping:
    return SemanticMapping(
        id=mapping_id,
        kind=MappingKind.ACTION,
        graph_fragment_node_ids=["node_1"],
        semantic_label="act",
        confidence_score=confidence,
        confidence_tier=ConfidenceTier.STATIC_ONLY,
        provenance=[ProvenanceRecord(source="static_analysis", confidence=confidence)],
        evidence_count=1,
        evidence_diversity=0.2,
        parser_certainty=0.9,
        metadata={"rule_id": rule, "rule_priority": 2, "match": {"node_id": "node_1"}},
    )


def test_build_rule_evidence_trace_records_rule_and_confidence_components() -> None:
    trace = build_rule_evidence_trace([_mapping("m1", rule="ActionRule", confidence=0.75)])

    assert trace["mapping_count"] == 1
    assert trace["rule_summary"] == {"ActionRule": 1}
    [record] = trace["mappings"]
    assert record["mapping_id"] == "m1"
    assert record["confidence_components"]["provenance_confidence_mean"] == 0.75
    assert record["match"] == {"node_id": "node_1"}


def test_reviewer_annotations_calibrate_precision_proxy(tmp_path: Path) -> None:
    annotations = tmp_path / "annotations.json"
    annotations.write_text(
        json.dumps({"annotations": [{"mapping_id": "m1", "status": "accepted"}]}),
        encoding="utf-8",
    )
    trace = build_rule_evidence_trace([_mapping("m1", rule="ActionRule", confidence=0.75)])

    apply_reviewer_annotations(trace, load_reviewer_annotations(annotations))
    calibration = calibrate_rule_evidence_trace(trace)

    assert trace["mappings"][0]["final_mapping_status"] == "accepted"
    assert calibration["overall"]["precision_proxy"] == 1.0
    assert calibration["per_rule"][0]["review_coverage"] == 1.0
