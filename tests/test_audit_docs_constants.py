"""Tests for documentation constant and evidence-boundary audits."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "tools" / "audit_docs_constants.py"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_docs_constants", AUDIT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_roundtrip_claim_audit_rejects_unqualified_all_target_claim(tmp_path: Path) -> None:
    audit = _load_audit_module()
    doc = tmp_path / "claim.md"
    doc.write_text("Roundtrip result: 24/24 ROLE_PRESERVED at s_role=1.0.\n")

    findings: list[str] = []
    audit.audit_roundtrip_previous_claims({doc}, findings)

    assert findings
    assert "unqualified-roundtrip-current-claim" in findings[0]


def test_roundtrip_claim_audit_accepts_current_ledger_claim(tmp_path: Path) -> None:
    audit = _load_audit_module()
    doc = tmp_path / "claim.md"
    doc.write_text(
        "Current ledger: 24/24 ROLE_PRESERVED. "
        "Current metrics classification is documented in METRICS.yaml.\n"
    )

    findings: list[str] = []
    audit.audit_roundtrip_previous_claims({doc}, findings)

    assert findings == []


def test_roundtrip_current_count_audit_rejects_out_of_sync_current_ledger_count(
    tmp_path: Path,
) -> None:
    audit = _load_audit_module()
    doc = tmp_path / "claim.md"
    doc.write_text("Current ledger: 22/24 ROLE_PRESERVED and 2 DRIFT.\n")

    findings: list[str] = []
    audit.audit_roundtrip_current_counts({doc}, findings)

    assert len(findings) == 2
    assert all("out-of-sync-roundtrip-current-count" in finding for finding in findings)


def test_roundtrip_mean_score_audit_rejects_out_of_sync_current_ledger_score(
    tmp_path: Path,
) -> None:
    audit = _load_audit_module()
    doc = tmp_path / "claim.md"
    doc.write_text("| Mean role-preservation score | 0.9167 |\n")

    findings: list[str] = []
    audit.audit_roundtrip_mean_score({doc}, findings)

    assert len(findings) == 1
    assert "out-of-sync-roundtrip-mean-score" in findings[0]


def test_current_doc_audit_rejects_unsupported_project_paths(tmp_path: Path) -> None:
    audit = _load_audit_module()
    doc = tmp_path / "README.md"
    doc.write_text("Run from projects_in_progress/cogant.\n")
    pattern = next(p for p in audit.BANNED_PATTERNS if p.name == "unsupported-project-path")

    assert pattern.regex.search(doc.read_text())
