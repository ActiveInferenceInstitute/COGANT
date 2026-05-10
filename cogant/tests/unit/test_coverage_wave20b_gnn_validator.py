"""Wave-20b coverage boost: ``cogant.gnn.validator`` edge-case branches.

Targets the specific lines that the existing validator-coverage tests
miss:

* ``_resolve_upstream_flag`` — explicit override, env-disabled (lines 44, 46)
* ``ValidationResult.to_markdown`` (lines 95-137) — every branch
* ``validate_matrices`` shape mismatches in A cols, B dims (lines 423, 441, 443)
* ``_check_manifest`` missing-file branch (lines 514-515)
* ``_check_json_files`` JSON-decode + read failures (lines 556-557)
* ``_check_markdown`` warnings extend (line 570) and read failure (582-583)
* ``_check_state_space`` warnings extend (line 597)
* ``_check_provenance`` warnings extend (line 615) and read failure (618-619)
* ``_check_checksums`` matching plain-text checksum (line 631 not really a branch but covered)
  and exception during checksum read (lines 641-642)

All real files / real JSON — no mocks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cogant.gnn.validator import (
    GNNValidator,
    ValidationResult,
    _resolve_upstream_flag,
)

# --------------------------------------------------------------------------- #
# _resolve_upstream_flag
# --------------------------------------------------------------------------- #


def test_resolve_upstream_flag_explicit_true_wins() -> None:
    """An explicit ``True`` overrides the environment (line 44 path)."""
    os.environ["COGANT_DISABLE_UPSTREAM_GNN"] = "1"
    try:
        assert _resolve_upstream_flag(True) is True
    finally:
        os.environ.pop("COGANT_DISABLE_UPSTREAM_GNN", None)


def test_resolve_upstream_flag_explicit_false_wins() -> None:
    """An explicit ``False`` overrides the environment (line 44 path)."""
    os.environ.pop("COGANT_DISABLE_UPSTREAM_GNN", None)
    assert _resolve_upstream_flag(False) is False


def test_resolve_upstream_flag_disabled_by_env() -> None:
    """``None`` + env=1 returns ``False`` (line 46 path)."""
    os.environ["COGANT_DISABLE_UPSTREAM_GNN"] = "true"
    try:
        assert _resolve_upstream_flag(None) is False
    finally:
        os.environ.pop("COGANT_DISABLE_UPSTREAM_GNN", None)


def test_resolve_upstream_flag_default_on() -> None:
    """``None`` + env unset returns ``True``."""
    os.environ.pop("COGANT_DISABLE_UPSTREAM_GNN", None)
    assert _resolve_upstream_flag(None) is True


# --------------------------------------------------------------------------- #
# ValidationResult.to_markdown — every section branch
# --------------------------------------------------------------------------- #


def test_to_markdown_minimal_valid() -> None:
    """A clean result emits header + score, no error/warning sections."""
    result = ValidationResult(valid=True, score=99.5)
    md = result.to_markdown()
    assert "# GNN Validation Report" in md
    assert "VALID" in md
    assert "99.5/100" in md
    # No section headers for empty containers
    assert "## Errors" not in md
    assert "## Warnings" not in md
    assert "## Section Scores" not in md
    assert "## Details" not in md


def test_to_markdown_with_errors_warnings_invalid() -> None:
    """Errors and warnings each get their own ``##`` section."""
    result = ValidationResult(
        valid=False,
        errors=["err A", "err B"],
        warnings=["warn 1"],
        score=42.0,
    )
    md = result.to_markdown()
    assert "INVALID" in md
    assert "## Errors" in md
    assert "err A" in md
    assert "err B" in md
    assert "## Warnings" in md
    assert "warn 1" in md


def test_to_markdown_with_section_scores() -> None:
    """Section scores render with bar visualization."""
    result = ValidationResult(valid=True, score=85.0)
    result.section_scores = {"alpha": 50.0, "beta": 100.0}
    md = result.to_markdown()
    assert "## Section Scores" in md
    assert "alpha" in md
    assert "beta" in md
    # Bar rendering uses block characters
    assert "█" in md or "░" in md


def test_to_markdown_with_details_dict_and_scalar() -> None:
    """Details renders dict values with ``###`` subheadings, scalars inline."""
    result = ValidationResult(valid=True, score=80.0)
    result.details = {
        "scalar": "ready",
        "nested": {"inner_key": "inner_value", "count": 5},
    }
    md = result.to_markdown()
    assert "## Details" in md
    # Scalar branch: "- **scalar**: ready"
    assert "scalar" in md
    assert "ready" in md
    # Dict branch: "### nested" + "- inner_key: inner_value"
    assert "### nested" in md
    assert "inner_key" in md
    assert "inner_value" in md


def test_badge_svg_renders() -> None:
    """``badge_svg`` returns an SVG string with the validity status."""
    result = ValidationResult(valid=True, score=92.5)
    svg = result.badge_svg()
    assert "<svg" in svg
    assert "VALID" in svg
    assert "92" in svg


def test_to_dict_round_trip() -> None:
    result = ValidationResult(
        valid=False, errors=["e1"], warnings=["w1"], score=10.0
    )
    result.details = {"k": "v"}
    result.section_scores = {"s1": 1.0}
    out = result.to_dict()
    assert out["valid"] is False
    assert out["errors"] == ["e1"]
    assert out["warnings"] == ["w1"]
    assert out["score"] == 10.0
    assert out["details"] == {"k": "v"}
    assert out["section_scores"] == {"s1": 1.0}


# --------------------------------------------------------------------------- #
# validate_matrices — shape-mismatch branches
# --------------------------------------------------------------------------- #


def test_validate_matrices_a_column_count_mismatch() -> None:
    """A-matrix row width ≠ n_states is a structural error (line 423)."""
    validator = GNNValidator()
    errors = validator.validate_matrices(
        {
            # Two rows (n_obs=2) but only one column (should be n_states=3)
            "A": [[1.0], [1.0]],
            "B": [],
            "C": [0.0, 0.0],
            "D": [0.5, 0.5, 0.0],  # not validated when shape fails earlier
            "dimensions": {"n_states": 3, "n_obs": 2, "n_actions": 1},
        }
    )
    assert any("A column count mismatch" in e for e in errors)


def test_validate_matrices_b_second_dim_mismatch() -> None:
    """B[i] length ≠ n_states triggers ``B second dim mismatch`` (line 441)."""
    validator = GNNValidator()
    errors = validator.validate_matrices(
        {
            "A": [[0.5, 0.5]],
            # n_states=2 → outer len 2, but inner rows are length 3
            "B": [
                [[1.0], [0.0], [0.0]],
                [[0.0], [1.0], [0.0]],
            ],
            "C": [0.0],
            "D": [1.0, 0.0],
            "dimensions": {"n_states": 2, "n_obs": 1, "n_actions": 1},
        }
    )
    assert any("B second dim mismatch" in e for e in errors)


def test_validate_matrices_b_third_dim_mismatch() -> None:
    """B[i][j] length ≠ n_actions triggers ``B third dim mismatch`` (line 443)."""
    validator = GNNValidator()
    errors = validator.validate_matrices(
        {
            "A": [[0.5, 0.5]],
            # Correct first/second dims (2 x 2), wrong third (cells len 1, want 3)
            "B": [
                [[1.0], [0.0]],
                [[0.0], [1.0]],
            ],
            "C": [0.0],
            "D": [1.0, 0.0],
            "dimensions": {"n_states": 2, "n_obs": 1, "n_actions": 3},
        }
    )
    assert any("B third dim mismatch" in e for e in errors)


# --------------------------------------------------------------------------- #
# _check_manifest / _check_json_files / _check_markdown branches via real package
# --------------------------------------------------------------------------- #


def _scaffold_minimal_package(pkg_dir: Path, *, with_manifest: bool = True) -> None:
    """Create just enough of a GNN package for the validator to run end-to-end.

    The matrix block is skipped (the validator doesn't require it).
    """
    pkg_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Any] = {
        "model.gnn.json": {"sections": []},
        "state_space.json": {
            "variables": [],
            "observations": [],
            "actions": [],
            "transitions": {},
        },
        "observations.json": [],
        "actions.json": [],
        "transitions.json": {},
        "preferences.json": [],
        "factors.json": [],
        "provenance.json": {"timestamp": "2026-01-01", "sources": {}},
        "ontology.json": {},
        "actions_policies.json": [],
        "connections.json": [],
        "preferences_constraints.json": [],
        "markov_blanket.json": {},
        "markov_network.json": {},
    }
    for name, content in files.items():
        (pkg_dir / name).write_text(json.dumps(content), encoding="utf-8")
    (pkg_dir / "model.gnn.md").write_text(
        "# Model\n## Model Metadata\n## Repository Metadata\n", encoding="utf-8"
    )
    if with_manifest:
        (pkg_dir / "manifest.json").write_text(
            json.dumps({"name": "test", "checksums": {}}), encoding="utf-8"
        )


def test_validate_package_missing_manifest_emits_error(tmp_path: Path) -> None:
    """A package without manifest.json adds an explicit error (lines 514-515)."""
    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg, with_manifest=False)
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    # Must register a "Missing required file: manifest.json" or similar
    assert any("manifest.json" in e for e in result.errors)


def test_validate_package_invalid_manifest_json(tmp_path: Path) -> None:
    """Garbled manifest.json registers an "Invalid JSON" error (line 524-525)."""
    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    (pkg / "manifest.json").write_text("{not valid json", encoding="utf-8")
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    assert any("Invalid JSON in manifest.json" in e for e in result.errors)


def test_validate_package_missing_directory_short_circuits(tmp_path: Path) -> None:
    """Non-existent package directory short-circuits with a single error."""
    nonexistent = tmp_path / "nope"
    result = GNNValidator().validate_package(str(nonexistent), upstream_gnn=False)
    assert result.valid is False
    assert result.score == 0.0
    assert any("not found" in e for e in result.errors)


def test_validate_package_invalid_state_space_json(tmp_path: Path) -> None:
    """Garbled state_space.json adds a JSON-decode error (line 555)."""
    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    (pkg / "state_space.json").write_text("not json", encoding="utf-8")
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    assert any("state_space.json" in e for e in result.errors)


def test_validate_package_markdown_missing_canonical_sections(tmp_path: Path) -> None:
    """A markdown file lacking canonical sections produces warnings (line 570)."""
    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    (pkg / "model.gnn.md").write_text("# Title only\n", encoding="utf-8")
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    # Many missing canonical sections → warnings list grows
    assert any("Missing canonical section" in w for w in result.warnings)


def test_validate_package_state_space_missing_keys_warns(tmp_path: Path) -> None:
    """state_space.json missing required keys triggers warnings (line 597)."""
    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    (pkg / "state_space.json").write_text(json.dumps({"variables": []}), encoding="utf-8")
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    # validate_state_space returns errors; _check_state_space appends them as warnings
    assert any("Missing state space key" in w for w in result.warnings)


def test_validate_package_provenance_missing_keys_warns(tmp_path: Path) -> None:
    """provenance.json missing required keys triggers warnings (line 615)."""
    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    (pkg / "provenance.json").write_text(json.dumps({}), encoding="utf-8")
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    assert any("Missing provenance key" in w for w in result.warnings)


def test_validate_package_invalid_provenance_json(tmp_path: Path) -> None:
    """Garbled provenance.json triggers the read-failure branch (lines 618-619)."""
    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    (pkg / "provenance.json").write_text("{nope", encoding="utf-8")
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    assert any("provenance.json" in e for e in result.errors)


def test_validate_package_invalid_other_json(tmp_path: Path) -> None:
    """Garbled non-state non-provenance JSON adds errors (line 555-557)."""
    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    (pkg / "actions.json").write_text("garbage", encoding="utf-8")
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    assert any("actions.json" in e for e in result.errors)


# --------------------------------------------------------------------------- #
# _check_checksums — mismatch + match branches
# --------------------------------------------------------------------------- #


def test_validate_package_checksum_mismatch_warns(tmp_path: Path) -> None:
    """Checksums mismatch produces warnings (line 644-647)."""
    import hashlib

    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    # Override manifest with a deliberately wrong checksum for actions.json
    bogus = "0" * 64  # not the real sha256 of the file
    (pkg / "manifest.json").write_text(
        json.dumps({"name": "test", "checksums": {"actions.json": bogus}}),
        encoding="utf-8",
    )
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    assert any("Checksum mismatch" in w for w in result.warnings)
    # Sanity: the actual sha256 of the canonical-encoded JSON is reproducible
    real_sha = hashlib.sha256(
        json.dumps([], sort_keys=True, default=str).encode()
    ).hexdigest()
    assert real_sha != bogus


def test_validate_package_checksum_matches_no_warning(tmp_path: Path) -> None:
    """A correct checksum passes silently (line 649)."""
    import hashlib

    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    # actions.json was scaffolded as `[]`. Compute its real canonical sha256.
    real_sha = hashlib.sha256(
        json.dumps([], sort_keys=True, default=str).encode()
    ).hexdigest()
    (pkg / "manifest.json").write_text(
        json.dumps({"name": "test", "checksums": {"actions.json": real_sha}}),
        encoding="utf-8",
    )
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    # No "Checksum mismatch" warning for actions.json
    assert not any("Checksum mismatch for actions.json" in w for w in result.warnings)


def test_validate_package_checksum_skips_missing_file(tmp_path: Path) -> None:
    """Manifest checksum referencing a missing file is skipped silently (line 630-631)."""
    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    (pkg / "manifest.json").write_text(
        json.dumps(
            {"name": "test", "checksums": {"phantom.json": "deadbeef" * 8}}
        ),
        encoding="utf-8",
    )
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    # Missing file → not flagged via the checksum check
    assert not any("Checksum mismatch for phantom.json" in w for w in result.warnings)


def test_validate_package_no_checksums_warns(tmp_path: Path) -> None:
    """Manifest without a checksums dict adds a no-checksums warning (line 625)."""
    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    (pkg / "manifest.json").write_text(json.dumps({"name": "test"}), encoding="utf-8")
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    assert any("no checksums" in w for w in result.warnings)


def test_validate_package_plain_text_checksum(tmp_path: Path) -> None:
    """Non-.json files use plain-text checksum branch (lines 640-642)."""
    import hashlib

    pkg = tmp_path / "pkg"
    _scaffold_minimal_package(pkg)
    md_text = (pkg / "model.gnn.md").read_text(encoding="utf-8")
    real_sha = hashlib.sha256(md_text.encode()).hexdigest()
    (pkg / "manifest.json").write_text(
        json.dumps({"name": "test", "checksums": {"model.gnn.md": real_sha}}),
        encoding="utf-8",
    )
    result = GNNValidator().validate_package(str(pkg), upstream_gnn=False)
    assert not any("Checksum mismatch for model.gnn.md" in w for w in result.warnings)


# --------------------------------------------------------------------------- #
# generate_validation_badge wraps badge_svg
# --------------------------------------------------------------------------- #


def test_generate_validation_badge_delegates() -> None:
    validator = GNNValidator()
    result = ValidationResult(valid=True, score=88.0)
    svg = validator.generate_validation_badge(result)
    assert "<svg" in svg
    assert "VALID" in svg
