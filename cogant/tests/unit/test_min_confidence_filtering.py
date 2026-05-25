"""Tests for the ``--min-confidence`` translate-stage threshold (FAQ #17, TODO #3).

The FAQ promises: "You can lower the threshold with ``--min-confidence`` if you
want to include them." This was previously documented but never test-anchored.
The flag is wired through ``cli/main.py`` (lines 690, 725, 729 — translate path
and the analyze path mirror at 952, 1010, 1014) and consumed inside
``api.orchestration._filter_semantic_mappings``. These tests pin the threshold
semantics so a future refactor cannot silently re-introduce the documentation /
behaviour split.
"""

from __future__ import annotations

import pytest

from cogant.api.orchestration import _filter_semantic_mappings
from cogant.schemas.semantic import (
    ConfidenceTier,
    MappingKind,
    SemanticMapping,
)


def _make_mapping(confidence: float, mapping_id: str = "m0") -> SemanticMapping:
    """Build a SemanticMapping whose ``confidence_score`` is ``confidence``.

    Tier is ``STATIC_ONLY`` regardless of score — the filter cares about the
    numeric score, not the tier label. Tier semantics are about *evidence
    type* (static vs runtime vs human-reviewed), independent of the band cuts
    a threshold imposes.
    """
    return SemanticMapping(
        id=mapping_id,
        kind=MappingKind.HIDDEN_STATE,
        graph_fragment_node_ids=[mapping_id],
        confidence_score=confidence,
        confidence_tier=ConfidenceTier.STATIC_ONLY,
    )


def test_filter_keeps_high_confidence_mappings_above_threshold() -> None:
    """High-confidence mappings remain after a 0.40 threshold filter."""
    mappings = [
        _make_mapping(0.90, "n1"),
        _make_mapping(0.85, "n2"),
        _make_mapping(0.40, "n3"),
    ]
    kept = _filter_semantic_mappings(mappings, min_confidence=0.40)
    assert len(kept) == 3
    assert {m.id for m in kept} == {"n1", "n2", "n3"}


def test_filter_drops_mappings_strictly_below_threshold() -> None:
    """Mappings strictly below the threshold are excluded (FAQ #17 promise)."""
    mappings = [
        _make_mapping(0.90, "kept"),
        _make_mapping(0.39, "dropped"),
        _make_mapping(0.10, "dropped2"),
    ]
    kept = _filter_semantic_mappings(mappings, min_confidence=0.40)
    assert {m.id for m in kept} == {"kept"}


def test_filter_lowering_threshold_includes_low_band_mappings() -> None:
    """Lowering the threshold to 0.10 readmits LOW-tier mappings.

    This is the case the FAQ documents: "You can lower the threshold with
    ``--min-confidence`` if you want to include them."
    """
    mappings = [
        _make_mapping(0.05, "very_low"),
        _make_mapping(0.20, "low"),
        _make_mapping(0.80, "high"),
    ]
    kept = _filter_semantic_mappings(mappings, min_confidence=0.10)
    assert {m.id for m in kept} == {"low", "high"}


def test_filter_at_zero_threshold_keeps_everything() -> None:
    """Threshold of 0.0 admits every mapping (degenerate but documented case)."""
    mappings = [_make_mapping(c, f"n{i}") for i, c in enumerate([0.0, 0.1, 0.5, 1.0])]
    kept = _filter_semantic_mappings(mappings, min_confidence=0.0)
    assert len(kept) == 4


def test_filter_at_unity_threshold_keeps_only_perfect_confidence() -> None:
    """Threshold of 1.0 admits only confidence==1.0 mappings — the strict ceiling."""
    mappings = [
        _make_mapping(1.00, "perfect"),
        _make_mapping(0.99, "almost"),
        _make_mapping(0.95, "high_but_not_perfect"),
    ]
    kept = _filter_semantic_mappings(mappings, min_confidence=1.0)
    assert {m.id for m in kept} == {"perfect"}


def test_filter_on_empty_input_returns_empty_list() -> None:
    """Empty input is preserved — defensive against pipelines whose translate
    stage produced no mappings."""
    assert _filter_semantic_mappings([], min_confidence=0.5) == []


@pytest.mark.parametrize("bad_threshold", [-0.01, 1.01, -1.0, 2.0])
def test_filter_does_not_validate_threshold_range_itself(bad_threshold: float) -> None:
    """The CLI validates ``[0.0, 1.0]`` before this filter ever runs (cli/main.py
    lines 725-728). The filter is left tolerant — passing it an out-of-range
    threshold returns the natural mathematical result. This documents the
    layering: validation belongs at the CLI boundary, not the lib API.
    """
    mappings = [_make_mapping(0.5, "n1")]
    kept = _filter_semantic_mappings(mappings, min_confidence=bad_threshold)
    if bad_threshold <= 0.5:
        assert kept == mappings
    else:
        assert kept == []
