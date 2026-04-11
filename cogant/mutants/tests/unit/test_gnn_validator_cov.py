"""Behavioral tests for cogant.gnn.validator.GNNValidator.

Drives validate_package end-to-end with real on-disk fixtures plus the
focused validate_markdown / validate_state_space / validate_matrices /
validate_provenance helpers.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cogant.gnn.validator import GNNValidator, ValidationResult

# --------------------------- ValidationResult --------------------------- #


def test_validation_result_default_state_is_invalid():
    """A fresh ValidationResult is invalid with empty errors and zero score."""
    r = ValidationResult()
    assert r.valid is False
    assert r.errors == []
    assert r.warnings == []
    assert r.score == 0.0
    assert r.details == {}


def test_validation_result_to_dict_round_trip():
    """to_dict surfaces every field of the result."""
    r = ValidationResult(valid=True, errors=["e"], warnings=["w"], score=88.0)
    d = r.to_dict()
    assert d == {
        "valid": True,
        "score": 88.0,
        "errors": ["e"],
        "warnings": ["w"],
        "details": {},
    }


def test_validation_result_badge_svg_includes_status_and_score():
    """badge_svg embeds the status and percentage."""
    svg = ValidationResult(valid=True, score=92.0).badge_svg()
    assert "<svg" in svg
    assert "VALID" in svg
    assert "92" in svg
    bad = ValidationResult(valid=False, score=10.0).badge_svg()
    assert "INVALID" in bad


# --------------------------- validate_markdown ------------------------- #


def _full_markdown() -> str:
    """Build a markdown document containing every required section header."""
    canonical = [
        "Model Metadata",
        "Repository Metadata",
        "Source Coverage",
        "State Space",
        "Observation Modalities",
        "Actions Policies",
        "Program Graph Connections",
        "Factors",
        "Transition Structure",
        "Likelihood Structure",
        "Preferences Constraints",
        "Time Settings",
        "Parameterization",
        "Ontology Mapping",
        "Markov Blanket",
        "Provenance",
        "Confidence",
        "Rendering Hints",
        "Validation Notes",
    ]
    upstream = [
        "GNNSection",
        "GNNVersionAndFlags",
        "ModelName",
        "StateSpaceBlock",
        "Connections",
        "InitialParameterization",
        "Time",
        "ActInfOntologyAnnotation",
    ]
    parts = [f"## {sec}\n\nbody\n" for sec in upstream]
    parts.extend(f"## {sec}\n\nbody\n" for sec in canonical)
    return "\n".join(parts)


def test_validate_markdown_with_complete_document_returns_no_errors():
    """A document with every required section passes validate_markdown."""
    errors = GNNValidator().validate_markdown(_full_markdown())
    assert errors == []


def test_validate_markdown_missing_canonical_section_is_reported():
    """Removing a canonical section produces an explicit missing-section error."""
    md = _full_markdown().replace("## Model Metadata\n\nbody\n", "")
    errors = GNNValidator().validate_markdown(md)
    assert any("Missing canonical section" in e for e in errors)


def test_validate_markdown_missing_upstream_section_is_reported():
    """Removing an upstream section produces a missing-upstream error."""
    md = _full_markdown().replace("## StateSpaceBlock\n\nbody\n", "")
    errors = GNNValidator().validate_markdown(md)
    assert any("Missing upstream GNN v1.1 section" in e for e in errors)


def test_validate_markdown_out_of_order_upstream_is_reported():
    """Upstream sections out of order trigger an order-violation error."""
    # Build the upstream sections in reverse order
    upstream = [
        "ActInfOntologyAnnotation",
        "Time",
        "InitialParameterization",
        "Connections",
        "StateSpaceBlock",
        "ModelName",
        "GNNVersionAndFlags",
        "GNNSection",
    ]
    canonical_part = _full_markdown().split("## ActInfOntologyAnnotation\n\nbody\n", 1)[1]
    md = "\n".join(f"## {s}\n\nbody\n" for s in upstream) + canonical_part
    errors = GNNValidator().validate_markdown(md)
    assert any("out of canonical order" in e for e in errors)


# --------------------------- validate_state_space ---------------------- #


def test_validate_state_space_complete_dict_passes():
    """A well-formed state space dict produces no errors."""
    errors = GNNValidator().validate_state_space(
        {
            "variables": [],
            "observations": [],
            "actions": [],
            "transitions": {},
        }
    )
    assert errors == []


def test_validate_state_space_missing_keys_reported():
    """Missing required keys produce explicit messages."""
    errors = GNNValidator().validate_state_space({})
    joined = " ".join(errors)
    for key in ("variables", "observations", "actions", "transitions"):
        assert key in joined


def test_validate_state_space_wrong_types_reported():
    """Wrong container types produce dedicated errors."""
    errors = GNNValidator().validate_state_space(
        {
            "variables": "not-a-list",
            "observations": "not-a-list",
            "actions": "not-a-list",
            "transitions": "not-a-dict",
        }
    )
    assert any("Variables must be a list" in e for e in errors)
    assert any("Observations must be a list" in e for e in errors)
    assert any("Actions must be a list" in e for e in errors)
    assert any("Transitions must be a dict" in e for e in errors)


# --------------------------- validate_matrices ------------------------- #


def test_validate_matrices_well_formed_2x2():
    """A canonical 2-state, 2-obs, 1-action matrix block validates cleanly."""
    block = {
        "A": [[1.0, 0.0], [0.0, 1.0]],
        "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
        "C": [0.0, 0.0],
        "D": [0.5, 0.5],
        "dimensions": {"n_states": 2, "n_obs": 2, "n_actions": 1},
    }
    errors = GNNValidator().validate_matrices(block)
    assert errors == []


def test_validate_matrices_missing_keys_reported():
    """Each absent matrix key produces a 'Missing matrix' error."""
    errors = GNNValidator().validate_matrices({})
    for key in ("A", "B", "C", "D"):
        assert any(f"Missing matrix: {key}" in e for e in errors)


def test_validate_matrices_a_row_sum_violation():
    """A rows that don't sum to 1 are flagged."""
    block = {
        "A": [[0.5, 0.5], [0.3, 0.4]],  # second row sums to 0.7
        "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
        "C": [0.0, 0.0],
        "D": [0.5, 0.5],
        "dimensions": {"n_states": 2, "n_obs": 2, "n_actions": 1},
    }
    errors = GNNValidator().validate_matrices(block)
    assert any("does not sum to 1" in e for e in errors)


def test_validate_matrices_d_sum_violation():
    """D vectors that don't sum to 1 are flagged."""
    block = {
        "A": [[1.0, 0.0], [0.0, 1.0]],
        "B": [[[1.0], [0.0]], [[0.0], [1.0]]],
        "C": [0.0, 0.0],
        "D": [0.7, 0.5],  # sum = 1.2
        "dimensions": {"n_states": 2, "n_obs": 2, "n_actions": 1},
    }
    errors = GNNValidator().validate_matrices(block)
    assert any("D does not sum to 1" in e for e in errors)


def test_validate_matrices_dimension_mismatches():
    """Wrong A row count, C length and B dims are all reported."""
    block = {
        "A": [[1.0, 0.0]],  # 1 row instead of 2
        "B": [[[1.0]]],     # wrong shape
        "C": [0.0],         # wrong length
        "D": [1.0],         # wrong length
        "dimensions": {"n_states": 2, "n_obs": 2, "n_actions": 1},
    }
    errors = GNNValidator().validate_matrices(block)
    joined = " ".join(errors)
    assert "A row count" in joined
    assert "C length" in joined
    assert "D length" in joined


# --------------------------- validate_provenance ----------------------- #


def test_validate_provenance_complete_dict_passes():
    """A provenance with timestamp + sources dict passes."""
    errors = GNNValidator().validate_provenance(
        {"timestamp": "now", "sources": {"a": "b"}}
    )
    assert errors == []


def test_validate_provenance_missing_keys_reported():
    """Missing top-level keys yield explicit errors."""
    errors = GNNValidator().validate_provenance({})
    joined = " ".join(errors)
    assert "timestamp" in joined
    assert "sources" in joined


def test_validate_provenance_sources_must_be_dict():
    """Non-dict 'sources' triggers a dedicated error."""
    errors = GNNValidator().validate_provenance(
        {"timestamp": "now", "sources": ["not", "a", "dict"]}
    )
    assert any("sources must be a dict" in e for e in errors)


# --------------------------- validate_package end-to-end ---------------- #


def _build_full_package(root: Path) -> None:
    """Write a complete GNN package directory with valid manifest + sections."""
    root.mkdir(parents=True, exist_ok=True)
    md = _full_markdown()
    (root / "model.gnn.md").write_text(md)
    state_space = {
        "variables": [],
        "observations": [],
        "actions": [],
        "transitions": {},
    }
    provenance = {"timestamp": "2026-01-01", "sources": {}}
    json_files = {
        "model.gnn.json": {},
        "state_space.json": state_space,
        "observations.json": {},
        "actions.json": {},
        "transitions.json": {},
        "preferences.json": {},
        "factors.json": {},
        "provenance.json": provenance,
        "ontology.json": {},
        "actions_policies.json": {},
        "connections.json": {},
        "preferences_constraints.json": {},
        "markov_blanket.json": {},
        "markov_network.json": {},
    }
    for name, payload in json_files.items():
        (root / name).write_text(json.dumps(payload))

    # Compute checksums for the JSON files only (the validator only checks
    # files actually present in the manifest's checksum table).
    checksums = {}
    for name, payload in json_files.items():
        canon = json.dumps(payload, sort_keys=True, default=str).encode()
        checksums[name] = hashlib.sha256(canon).hexdigest()
    manifest = {"name": "test", "checksums": checksums}
    (root / "manifest.json").write_text(json.dumps(manifest))


def test_validate_package_missing_directory_returns_invalid(tmp_path):
    """A non-existent directory yields a single error and zero score."""
    result = GNNValidator().validate_package(str(tmp_path / "missing"))
    assert result.valid is False
    assert result.score == 0.0
    assert any("not found" in e for e in result.errors)


def test_validate_package_full_package_is_valid(tmp_path):
    """A complete GNN package passes validation cleanly."""
    pkg = tmp_path / "pkg"
    _build_full_package(pkg)
    result = GNNValidator().validate_package(str(pkg))
    # No hard errors and the score is at the top end.
    assert result.errors == []
    assert result.score >= 80.0
    assert result.valid is True


def test_validate_package_partial_directory_collects_missing_file_errors(tmp_path):
    """A directory missing required files reports each as an error."""
    pkg = tmp_path / "partial"
    pkg.mkdir()
    # Only write the manifest with no checksums and no other files
    (pkg / "manifest.json").write_text(json.dumps({"name": "x"}))
    result = GNNValidator().validate_package(str(pkg))
    assert result.valid is False
    # Many "Missing required file" errors expected
    missing_errors = [e for e in result.errors if "Missing required file" in e]
    assert len(missing_errors) >= 5


def test_validate_package_invalid_json_in_manifest(tmp_path):
    """Malformed manifest JSON is reported as an error."""
    pkg = tmp_path / "bad_manifest"
    pkg.mkdir()
    (pkg / "manifest.json").write_text("{not valid json")
    result = GNNValidator().validate_package(str(pkg))
    assert any("Invalid JSON in manifest.json" in e for e in result.errors)


def test_validate_package_invalid_json_in_data_file(tmp_path):
    """Malformed JSON in any required file produces an error."""
    pkg = tmp_path / "bad_data"
    _build_full_package(pkg)
    (pkg / "state_space.json").write_text("not json")
    result = GNNValidator().validate_package(str(pkg))
    # state_space.json failure shows up as either Invalid JSON or
    # Failed to validate state_space
    joined = " ".join(result.errors)
    assert "state_space" in joined


def test_validate_package_checksum_mismatch_warns(tmp_path):
    """A checksum mismatch is captured as a warning, not an error."""
    pkg = tmp_path / "tampered"
    _build_full_package(pkg)
    # Tamper with one file after writing manifest
    (pkg / "factors.json").write_text(json.dumps({"tampered": True}))
    result = GNNValidator().validate_package(str(pkg))
    assert any("Checksum mismatch for factors.json" in w for w in result.warnings)


def test_validate_package_manifest_without_checksums_warns(tmp_path):
    """A manifest with no 'checksums' table emits a single warning."""
    pkg = tmp_path / "no_checksums"
    _build_full_package(pkg)
    # Overwrite the manifest, dropping checksums
    (pkg / "manifest.json").write_text(json.dumps({"name": "x"}))
    result = GNNValidator().validate_package(str(pkg))
    assert any("contains no checksums" in w for w in result.warnings)


def test_generate_validation_badge_returns_svg_string(tmp_path):
    """generate_validation_badge delegates to ValidationResult.badge_svg."""
    pkg = tmp_path / "pkg"
    _build_full_package(pkg)
    v = GNNValidator()
    result = v.validate_package(str(pkg))
    badge = v.generate_validation_badge(result)
    assert "<svg" in badge
