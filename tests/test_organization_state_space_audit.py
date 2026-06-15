"""Tests for the provisional organization state-space audit helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "tools" / "organization_state_space_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("organization_state_space_audit", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_example_spec_passes_and_writes_json_markdown_svg(tmp_path: Path) -> None:
    module = _load_module()
    output_dir = tmp_path / "audit"

    assert module.main(["--output-dir", str(output_dir), "--strict"]) == 0
    payload = json.loads(
        (output_dir / "organization_state_space_audit.json").read_text(encoding="utf-8")
    )
    assert payload["status"] == "PASS"
    assert payload["ready_for_surrogate"] is True
    assert payload["differentiable_surrogate_claimed"] is True
    assert payload["optimization_loss_terms"] == 1
    assert payload["optimization_intervention_bounds"] == 1
    assert payload["optimization_evidence_links"] == 3
    assert payload["prohibited_decision_uses"] == 3
    assert payload["findings"] == []
    assert "not claim that COGANT models a legal entity" in payload["claim_boundary"]
    assert "literally differentiable" in payload["claim_boundary"]
    markdown = (output_dir / "organization_state_space_audit.md").read_text(
        encoding="utf-8"
    )
    assert "Status: **PASS**" in markdown
    svg = (output_dir / "organization_state_space_audit.svg").read_text(encoding="utf-8")
    assert "<svg" in svg
    assert "Dynamic evidence present" in svg
    assert "Differentiability scoped to surrogate" in svg
    assert "Non-use boundaries declared" in svg


def test_org_chart_only_negative_control_fails_strict(tmp_path: Path) -> None:
    module = _load_module()
    spec = module.example_spec()
    spec["dynamic_traces"] = []
    spec_path = tmp_path / "org_chart_only.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    output_dir = tmp_path / "audit"

    assert module.main(["--spec", str(spec_path), "--output-dir", str(output_dir)]) == 0
    assert module.main(
        ["--spec", str(spec_path), "--output-dir", str(output_dir), "--strict"]
    ) == 1
    payload = json.loads(
        (output_dir / "organization_state_space_audit.json").read_text(encoding="utf-8")
    )
    codes = {finding["code"] for finding in payload["findings"]}
    assert "dynamic_evidence_required" in codes
    assert "transition_needs_dynamic_trace" in codes


def test_trace_only_and_unknown_evidence_are_not_certified(tmp_path: Path) -> None:
    module = _load_module()
    spec = module.example_spec()
    spec["static_artifacts"] = []
    spec["factors"][0]["evidence"] = ["unit_platform", "missing_trace"]
    spec_path = tmp_path / "trace_only.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    surface = module.validate_spec(module.load_spec(spec_path))
    codes = {finding.code for finding in surface.findings}
    assert surface.status == "FAIL"
    assert "typed_artifact_required" in codes
    assert "unknown_factor_evidence" in codes
    assert "unknown_dynamic_link" in codes


def test_missing_negative_controls_block_surrogate_language() -> None:
    module = _load_module()
    spec = module.example_spec()
    spec["negative_controls"] = [{"id": "org_chart_only"}]

    surface = module.validate_spec(spec)
    codes = {finding.code for finding in surface.findings}
    assert surface.status == "FAIL"
    assert "negative_control_missing" in codes


def test_future_transition_evidence_is_not_certified() -> None:
    module = _load_module()
    spec = module.example_spec()
    spec["transitions"][0]["timestamp"] = "2026-06-01T10:05:00Z"

    surface = module.validate_spec(spec)
    codes = {finding.code for finding in surface.findings}
    assert surface.status == "FAIL"
    assert "future_transition_evidence" in codes


def test_invalid_timestamps_block_strict_surrogate_status() -> None:
    module = _load_module()
    spec = module.example_spec()
    spec["dynamic_traces"][0]["timestamp"] = "not-a-date"
    spec["transitions"][0]["timestamp"] = "2026-06-01T10:20:00"

    surface = module.validate_spec(spec)
    codes = {finding.code for finding in surface.findings}
    assert surface.status == "FAIL"
    assert "dynamic_timestamp_invalid" in codes
    assert "transition_timestamp_invalid" in codes


def test_transition_factor_roles_must_match_state_action_contract() -> None:
    module = _load_module()
    spec = module.example_spec()
    spec["transitions"][0]["from_state"] = "action_assign_oncall"
    spec["transitions"][0]["action"] = "state_incident_load"

    surface = module.validate_spec(spec)
    findings = [
        finding
        for finding in surface.findings
        if finding.code == "transition_factor_kind_mismatch"
    ]
    assert surface.status == "FAIL"
    assert len(findings) == 2
    assert {finding.location for finding in findings} == {
        "transitions.transition_triage_to_recovery.from_state",
        "transitions.transition_triage_to_recovery.action",
    }


def test_differentiable_surrogate_claim_requires_optimization_surface() -> None:
    module = _load_module()
    spec = module.example_spec()
    spec["optimization_surface"].pop("loss_terms")

    surface = module.validate_spec(spec)
    codes = {finding.code for finding in surface.findings}
    assert surface.status == "FAIL"
    assert "optimization_field_required" in codes
    assert "loss_terms_required" in codes


def test_differentiable_surrogate_claim_requires_non_use_categories() -> None:
    module = _load_module()
    spec = module.example_spec()
    spec["optimization_surface"]["prohibited_decision_uses"] = [
        "legal_entity_modeling"
    ]

    surface = module.validate_spec(spec)
    codes = {finding.code for finding in surface.findings}
    assert surface.status == "REVIEW"
    assert "prohibited_decision_category_missing" in codes
