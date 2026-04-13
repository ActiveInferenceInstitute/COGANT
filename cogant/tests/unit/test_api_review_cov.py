"""Behavioral tests for cogant.api.review.ReviewAPI.

Exercises bundle loading, mapping accept/reject/edit lifecycle, and
curated-bundle persistence with real JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cogant.api.review import ReviewAPI, ReviewableMapping


def _write_bundle(tmp_path: Path, node_count: int = 5) -> Path:
    """Create a bundle JSON on disk with `node_count` reviewable mappings."""
    bundle = {
        "stage_results": {
            "translate": {
                "node_features": [{"idx": i} for i in range(node_count)],
            }
        },
    }
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle))
    return path


# --------------------------- load_bundle / extract ---------------------- #


def test_load_bundle_populates_mappings(tmp_path):
    """Loading a bundle extracts up to 5 reviewable mappings."""
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path, node_count=5)))
    assert len(api.mappings) == 5
    # First mapping has id "mapping_0" and confidence 0.8
    assert api.mappings[0].id == "mapping_0"
    assert api.mappings[0].confidence == pytest.approx(0.8)
    assert api.mappings[0].status == "pending"


def test_load_bundle_caps_at_first_five_mappings(tmp_path):
    """Even when the bundle has 10 node features, only 5 mappings are loaded."""
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path, node_count=10)))
    assert len(api.mappings) == 5


def test_load_bundle_empty_translate_results(tmp_path):
    """Bundle without translate stage yields no mappings."""
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"stage_results": {}}))
    api = ReviewAPI()
    api.load_bundle(str(path))
    assert api.mappings == []


def test_load_bundle_missing_file_raises(tmp_path):
    """load_bundle surfaces FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        ReviewAPI().load_bundle(str(tmp_path / "nope.json"))


# --------------------------- present / accept / reject ----------------- #


def test_present_mapping_returns_the_matching_mapping(tmp_path):
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    m = api.present_mapping("mapping_2")
    assert isinstance(m, ReviewableMapping)
    assert m.id == "mapping_2"


def test_present_mapping_missing_raises_keyerror(tmp_path):
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    with pytest.raises(KeyError):
        api.present_mapping("nonexistent")


def test_accept_mapping_updates_status_and_notes(tmp_path):
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    api.accept_mapping("mapping_1", notes="looks good")
    m = api.present_mapping("mapping_1")
    assert m.status == "accepted"
    assert m.notes == "looks good"


def test_accept_missing_raises_keyerror(tmp_path):
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    with pytest.raises(KeyError):
        api.accept_mapping("bogus")


def test_reject_mapping_updates_status(tmp_path):
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    api.reject_mapping("mapping_3", reason="incorrect target")
    m = api.present_mapping("mapping_3")
    assert m.status == "rejected"
    assert m.notes == "incorrect target"


def test_reject_missing_raises_keyerror(tmp_path):
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    with pytest.raises(KeyError):
        api.reject_mapping("not-there")


# --------------------------- edit --------------------------------------- #


def test_edit_mapping_applies_changes_and_marks_edited(tmp_path):
    """edit_mapping updates attributes that exist and marks as edited."""
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    updated = api.edit_mapping("mapping_0", target="new_target", confidence=0.95)
    assert updated.target == "new_target"
    assert updated.confidence == 0.95
    assert updated.status == "edited"


def test_edit_mapping_ignores_unknown_attributes(tmp_path):
    """Unknown attribute names are silently skipped."""
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    m = api.edit_mapping("mapping_0", bogus_field="x")
    assert not hasattr(m, "bogus_field")
    assert m.status == "edited"


def test_edit_missing_raises_keyerror(tmp_path):
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    with pytest.raises(KeyError):
        api.edit_mapping("gone", target="x")


# --------------------------- summary and filters ----------------------- #


def test_get_review_summary_counts_each_status(tmp_path):
    """Summary reflects accept/reject/edit/pending counts."""
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    api.accept_mapping("mapping_0")
    api.accept_mapping("mapping_1")
    api.reject_mapping("mapping_2")
    api.edit_mapping("mapping_3", target="t")
    summary = api.get_review_summary()
    assert summary["total"] == 5
    assert summary["accepted"] == 2
    assert summary["rejected"] == 1
    assert summary["edited"] == 1
    assert summary["pending"] == 1


def test_filter_helpers_return_expected_subsets(tmp_path):
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    api.accept_mapping("mapping_0")
    api.reject_mapping("mapping_1")
    # Pending: 3 remaining
    assert len(api.get_pending_mappings()) == 3
    assert len(api.get_accepted_mappings()) == 1
    assert len(api.get_rejected_mappings()) == 1


# --------------------------- save_curated_bundle ----------------------- #


def test_save_curated_bundle_writes_review_metadata(tmp_path):
    """save_curated_bundle writes the loaded bundle plus a 'review' section."""
    api = ReviewAPI()
    api.load_bundle(str(_write_bundle(tmp_path)))
    api.accept_mapping("mapping_0", notes="ok")
    api.reject_mapping("mapping_1", reason="bad")

    out = tmp_path / "curated.json"
    api.save_curated_bundle(str(out))
    data = json.loads(out.read_text())
    assert "review" in data
    assert "mappings" in data["review"]
    assert len(data["review"]["mappings"]) == 5
    assert data["review"]["summary"]["accepted"] == 1
    assert data["review"]["summary"]["rejected"] == 1


def test_save_curated_bundle_without_load_raises(tmp_path):
    """Saving before loading a bundle is an error."""
    with pytest.raises(RuntimeError):
        ReviewAPI().save_curated_bundle(str(tmp_path / "nope.json"))
