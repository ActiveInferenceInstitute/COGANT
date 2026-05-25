"""Targeted branch tests for ``cogant.api.review``.

Targets the residual uncovered branches in ``review.py``:

* Lines 97-99 — ``_normalise_status`` accepts a known curated status
  (``"accepted"``/``"rejected"``/``"edited"``) and an unknown status
  that falls through to ``"pending"``.
* Line 123 — ``_extract_mappings`` early-return when ``current_bundle`` is None.
* Lines 129-132 — ``_extract_mappings`` handles list and unknown shapes
  for ``_semantic_mappings``.
* Line 137 — non-dict / empty-dict entries are skipped.
* Line 140 — ``kind`` carries a ``.value`` attribute (Enum-like).
* Lines 164-168 — legacy fallback when ``_semantic_mappings`` is absent
  but ``stage_results['translate']['node_features']`` is present.

All tests use real JSON files and real ReviewAPI instances. No mocks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pytest

from cogant.api.review import ReviewableMapping, ReviewAPI

pytestmark = pytest.mark.unit


# ============================================================ _normalise_status


class TestNormaliseStatus:
    """Cover every branch of the static ``_normalise_status`` helper."""

    def test_pending_bundle_status_maps_to_pending(self) -> None:
        for raw in ["", "auto_proposed", "in_review", "pending", None]:
            assert ReviewAPI._normalise_status(raw) == "pending"

    def test_accepted_status_passes_through(self) -> None:
        """Cover line 97-98: ``text in _REVIEW_STATUSES`` returns ``text``."""
        assert ReviewAPI._normalise_status("accepted") == "accepted"

    def test_rejected_status_passes_through(self) -> None:
        assert ReviewAPI._normalise_status("rejected") == "rejected"

    def test_edited_status_passes_through(self) -> None:
        assert ReviewAPI._normalise_status("edited") == "edited"

    def test_unknown_status_falls_through_to_pending(self) -> None:
        """Cover line 99: unknown text → ``"pending"``."""
        assert ReviewAPI._normalise_status("totally-unknown-status") == "pending"

    def test_uppercase_status_is_lowered(self) -> None:
        """``str(raw or "").lower()`` lowercases input."""
        assert ReviewAPI._normalise_status("ACCEPTED") == "accepted"

    def test_none_raw_input_maps_to_pending(self) -> None:
        assert ReviewAPI._normalise_status(None) == "pending"

    def test_int_raw_input_maps_to_pending(self) -> None:
        """Non-string raw → str() conversion → unknown → pending."""
        assert ReviewAPI._normalise_status(42) == "pending"


# ============================================================ _extract_mappings


class TestExtractMappingsEdgeCases:
    """Cover the empty-bundle / list / unknown-shape branches."""

    def test_no_bundle_extracts_nothing(self) -> None:
        """Cover line 122-123: empty current_bundle short-circuits."""
        api = ReviewAPI()
        # Manually trigger _extract_mappings with no bundle.
        api._extract_mappings()
        assert api.mappings == []

    def test_list_shape_for_semantic_mappings(self, tmp_path: Path) -> None:
        """Cover line 129-130: list-shape ``_semantic_mappings`` is enumerated."""
        bundle = {
            "artifacts": {
                "_semantic_mappings": [
                    {
                        "id": "list_mapping_0",
                        "kind": "OBSERVATION",
                        "graph_fragment_node_ids": ["n0"],
                        "confidence_score": 0.5,
                        "description": "first list mapping",
                        "status": "auto_proposed",
                    },
                    {
                        "id": "list_mapping_1",
                        "kind": "ACTION",
                        "graph_fragment_node_ids": ["n1"],
                        "confidence_score": 0.7,
                        "description": "second list mapping",
                    },
                ]
            }
        }
        bundle_path = tmp_path / "bundle.json"
        bundle_path.write_text(json.dumps(bundle))
        api = ReviewAPI()
        api.load_bundle(str(bundle_path))
        assert len(api.mappings) == 2
        ids = {m.id for m in api.mappings}
        assert ids == {"list_mapping_0", "list_mapping_1"}

    def test_unknown_shape_for_semantic_mappings(self, tmp_path: Path) -> None:
        """Cover line 131-132: a non-dict, non-list raw_mappings → empty entries."""
        bundle = {
            "artifacts": {
                # raw_mappings is the literal int 42 → unknown shape branch
                "_semantic_mappings": 42,
            }
        }
        bundle_path = tmp_path / "bundle.json"
        bundle_path.write_text(json.dumps(bundle))
        api = ReviewAPI()
        api.load_bundle(str(bundle_path))
        # No mappings extracted; legacy fallback also produces nothing.
        assert api.mappings == []

    def test_skip_non_dict_entries_in_list(self, tmp_path: Path) -> None:
        """Cover line 136-137: non-dict / empty-dict entries are skipped."""
        bundle = {
            "artifacts": {
                "_semantic_mappings": [
                    "this is a string, not a dict",  # has __dict__? str does not.
                    {},  # empty dict
                    {
                        "id": "real_mapping",
                        "kind": "OBSERVATION",
                        "graph_fragment_node_ids": ["n0"],
                        "confidence_score": 0.4,
                    },
                ]
            }
        }
        bundle_path = tmp_path / "bundle.json"
        bundle_path.write_text(json.dumps(bundle))
        api = ReviewAPI()
        api.load_bundle(str(bundle_path))
        # Only the real dict-with-data entry survives.
        assert len(api.mappings) == 1
        assert api.mappings[0].id == "real_mapping"

    def test_kind_with_value_attribute_is_unwrapped(self) -> None:
        """Cover line 139-140: ``kind.value`` → enum-like → unwrap.

        We bypass the JSON load path because Enums don't survive JSON
        round-trips; instead we attach an ``_semantic_mappings`` artifact
        with an Enum value directly to ``current_bundle`` and call
        ``_extract_mappings``.
        """

        class FakeKind(Enum):
            OBSERVATION = "OBSERVATION"

        api = ReviewAPI()
        api.current_bundle = {
            "artifacts": {
                "_semantic_mappings": {
                    "m1": {
                        "id": "m1",
                        "kind": FakeKind.OBSERVATION,
                        "graph_fragment_node_ids": ["n0"],
                        "confidence_score": 0.9,
                        "description": "enum-shaped kind",
                    }
                }
            }
        }
        api._extract_mappings()
        assert len(api.mappings) == 1
        assert api.mappings[0].target == "OBSERVATION"

    def test_object_with_dunder_dict_is_treated_as_dict(self) -> None:
        """Cover line 135: ``getattr(entry, "__dict__", {})`` for non-dict
        entries that *do* expose ``__dict__`` (e.g. dataclass instances)."""

        @dataclass
        class FakeMapping:
            id: str
            kind: str
            graph_fragment_node_ids: list[str]
            confidence_score: float
            description: str

        api = ReviewAPI()
        api.current_bundle = {
            "artifacts": {
                "_semantic_mappings": [
                    FakeMapping(
                        id="dataclass_m",
                        kind="OBSERVATION",
                        graph_fragment_node_ids=["n0"],
                        confidence_score=0.6,
                        description="from dataclass",
                    )
                ]
            }
        }
        api._extract_mappings()
        assert len(api.mappings) == 1
        assert api.mappings[0].id == "dataclass_m"

    def test_semantic_label_fallback_for_source(self, tmp_path: Path) -> None:
        """Empty ``graph_fragment_node_ids`` → ``semantic_label`` is used."""
        bundle = {
            "artifacts": {
                "_semantic_mappings": {
                    "m1": {
                        "id": "m1",
                        "kind": "ACTION",
                        "graph_fragment_node_ids": [],
                        "semantic_label": "fallback_label",
                        "confidence_score": 0.3,
                    }
                }
            }
        }
        bundle_path = tmp_path / "bundle.json"
        bundle_path.write_text(json.dumps(bundle))
        api = ReviewAPI()
        api.load_bundle(str(bundle_path))
        assert len(api.mappings) == 1
        assert api.mappings[0].source == "fallback_label"

    def test_evidence_default_for_no_description_or_label(
        self, tmp_path: Path
    ) -> None:
        """Cover the ``"Static analysis"`` default for evidence."""
        bundle = {
            "artifacts": {
                "_semantic_mappings": {
                    "m1": {
                        "id": "m1",
                        "kind": "OBSERVATION",
                        "graph_fragment_node_ids": ["n0"],
                        "confidence_score": 0.5,
                    }
                }
            }
        }
        bundle_path = tmp_path / "bundle.json"
        bundle_path.write_text(json.dumps(bundle))
        api = ReviewAPI()
        api.load_bundle(str(bundle_path))
        assert api.mappings[0].evidence == "Static analysis"


# ============================================================ legacy fallback


class TestLegacyNodeFeaturesFallback:
    """Cover lines 161-176: fallback to ``stage_results.translate.node_features``."""

    def test_legacy_node_features_extracted_when_no_semantic_mappings(
        self, tmp_path: Path
    ) -> None:
        bundle = {
            "stage_results": {
                "translate": {
                    "node_features": [
                        {
                            "id": "legacy_m1",
                            "kind": "OBSERVATION",
                            "confidence": 0.65,
                        },
                        {
                            "id": "legacy_m2",
                            "kind": "ACTION",
                            "confidence": 0.85,
                        },
                    ]
                }
            }
        }
        bundle_path = tmp_path / "bundle.json"
        bundle_path.write_text(json.dumps(bundle))
        api = ReviewAPI()
        api.load_bundle(str(bundle_path))
        assert len(api.mappings) == 2
        ids = {m.id for m in api.mappings}
        assert ids == {"legacy_m1", "legacy_m2"}
        # Source equals id in legacy mode.
        for m in api.mappings:
            assert m.source == m.id

    def test_legacy_skips_non_dict_node_features(self, tmp_path: Path) -> None:
        """Cover line 164-165: non-dict node_feature is skipped."""
        bundle = {
            "stage_results": {
                "translate": {
                    "node_features": [
                        "not-a-dict",
                        {
                            "id": "good",
                            "kind": "OBSERVATION",
                            "confidence": 0.5,
                        },
                    ]
                }
            }
        }
        bundle_path = tmp_path / "bundle.json"
        bundle_path.write_text(json.dumps(bundle))
        api = ReviewAPI()
        api.load_bundle(str(bundle_path))
        assert len(api.mappings) == 1
        assert api.mappings[0].id == "good"

    def test_legacy_handles_missing_translate_key(self, tmp_path: Path) -> None:
        """Bundle with ``stage_results`` but no translate → empty mappings."""
        bundle = {"stage_results": {"other_stage": {}}}
        bundle_path = tmp_path / "bundle.json"
        bundle_path.write_text(json.dumps(bundle))
        api = ReviewAPI()
        api.load_bundle(str(bundle_path))
        assert api.mappings == []

    def test_legacy_handles_empty_node_features(self, tmp_path: Path) -> None:
        """Empty list → no mappings."""
        bundle = {"stage_results": {"translate": {"node_features": []}}}
        bundle_path = tmp_path / "bundle.json"
        bundle_path.write_text(json.dumps(bundle))
        api = ReviewAPI()
        api.load_bundle(str(bundle_path))
        assert api.mappings == []


# ============================================================ ReviewableMapping


class TestReviewableMappingDataclass:
    def test_default_status_is_pending(self) -> None:
        m = ReviewableMapping(
            id="x",
            source="src",
            target="tgt",
            confidence=0.5,
            evidence="ev",
        )
        assert m.status == "pending"
        assert m.notes == ""

    def test_custom_status_and_notes(self) -> None:
        m = ReviewableMapping(
            id="x",
            source="src",
            target="tgt",
            confidence=0.5,
            evidence="ev",
            status="accepted",
            notes="ok",
        )
        assert m.status == "accepted"
        assert m.notes == "ok"


# ============================================================ ReviewAPI lifecycle


class TestReviewAPILifecycle:
    """Round-trip: load → accept/reject/edit → save curated bundle → verify."""

    def _make_bundle(self, tmp_path: Path) -> Path:
        bundle = {
            "artifacts": {
                "_semantic_mappings": {
                    "m1": {
                        "id": "m1",
                        "kind": "OBSERVATION",
                        "graph_fragment_node_ids": ["n0"],
                        "confidence_score": 0.7,
                        "description": "first",
                    },
                    "m2": {
                        "id": "m2",
                        "kind": "ACTION",
                        "graph_fragment_node_ids": ["n1"],
                        "confidence_score": 0.8,
                        "description": "second",
                    },
                }
            }
        }
        path = tmp_path / "bundle.json"
        path.write_text(json.dumps(bundle))
        return path

    def test_save_curated_bundle_round_trip(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        api.load_bundle(str(self._make_bundle(tmp_path)))
        api.accept_mapping("m1", notes="accepted")
        api.reject_mapping("m2", reason="bad")

        out_path = tmp_path / "curated.json"
        api.save_curated_bundle(str(out_path))

        with open(out_path) as f:
            saved = json.load(f)
        assert "review" in saved
        assert saved["review"]["summary"]["total"] == 2
        assert saved["review"]["summary"]["accepted"] == 1
        assert saved["review"]["summary"]["rejected"] == 1
        decisions = {m["id"]: m for m in saved["review"]["mappings"]}
        assert decisions["m1"]["status"] == "accepted"
        assert decisions["m1"]["notes"] == "accepted"
        assert decisions["m2"]["status"] == "rejected"
        assert decisions["m2"]["notes"] == "bad"

    def test_save_without_load_raises_runtime_error(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        with pytest.raises(RuntimeError, match="No bundle loaded"):
            api.save_curated_bundle(str(tmp_path / "x.json"))

    def test_get_pending_filters_correctly(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        api.load_bundle(str(self._make_bundle(tmp_path)))
        api.accept_mapping("m1")
        pending = api.get_pending_mappings()
        assert len(pending) == 1
        assert pending[0].id == "m2"

    def test_get_accepted_filters_correctly(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        api.load_bundle(str(self._make_bundle(tmp_path)))
        api.accept_mapping("m1")
        accepted = api.get_accepted_mappings()
        assert [m.id for m in accepted] == ["m1"]

    def test_get_rejected_filters_correctly(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        api.load_bundle(str(self._make_bundle(tmp_path)))
        api.reject_mapping("m1")
        rejected = api.get_rejected_mappings()
        assert [m.id for m in rejected] == ["m1"]

    def test_edit_mapping_changes_target(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        api.load_bundle(str(self._make_bundle(tmp_path)))
        edited = api.edit_mapping("m1", target="NEW_KIND", confidence=0.99)
        assert edited.target == "NEW_KIND"
        assert edited.confidence == pytest.approx(0.99)
        assert edited.status == "edited"

    def test_edit_unknown_field_silently_skipped(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        api.load_bundle(str(self._make_bundle(tmp_path)))
        edited = api.edit_mapping("m1", definitely_not_a_field="ignored")
        # Status still flips to "edited".
        assert edited.status == "edited"
        # Field was not added.
        assert not hasattr(edited, "definitely_not_a_field")

    def test_present_unknown_mapping_raises(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        api.load_bundle(str(self._make_bundle(tmp_path)))
        with pytest.raises(KeyError):
            api.present_mapping("nope")

    def test_accept_unknown_mapping_raises(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        api.load_bundle(str(self._make_bundle(tmp_path)))
        with pytest.raises(KeyError):
            api.accept_mapping("nope")

    def test_reject_unknown_mapping_raises(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        api.load_bundle(str(self._make_bundle(tmp_path)))
        with pytest.raises(KeyError):
            api.reject_mapping("nope")

    def test_edit_unknown_mapping_raises(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        api.load_bundle(str(self._make_bundle(tmp_path)))
        with pytest.raises(KeyError):
            api.edit_mapping("nope", target="X")

    def test_load_bundle_missing_file_raises(self, tmp_path: Path) -> None:
        api = ReviewAPI()
        with pytest.raises(FileNotFoundError):
            api.load_bundle(str(tmp_path / "no-such-file.json"))

    def test_present_mapping_returns_object(self, tmp_path: Path) -> None:
        """Cover line 193: ``present_mapping`` happy-path return."""
        api = ReviewAPI()
        api.load_bundle(str(self._make_bundle(tmp_path)))
        mapping = api.present_mapping("m1")
        assert mapping.id == "m1"
        assert isinstance(mapping, ReviewableMapping)
