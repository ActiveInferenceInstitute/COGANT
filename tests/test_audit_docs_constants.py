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


def test_roundtrip_claim_audit_rejects_unqualified_legacy_claim(tmp_path: Path) -> None:
    audit = _load_audit_module()
    doc = tmp_path / "claim.md"
    doc.write_text("Roundtrip result: 23/23 ROLE_PRESERVED at s_role=1.0.\n")

    findings: list[str] = []
    audit.audit_roundtrip_legacy_claims({doc}, findings)

    assert findings
    assert "unqualified-roundtrip-legacy-claim" in findings[0]


def test_roundtrip_claim_audit_accepts_historical_legacy_claim(tmp_path: Path) -> None:
    audit = _load_audit_module()
    doc = tmp_path / "claim.md"
    doc.write_text(
        "Historical v0.5 benchmark: 23/23 ROLE_PRESERVED. "
        "Current v0.6 metrics classify that ledger as STALE_LEGACY.\n"
    )

    findings: list[str] = []
    audit.audit_roundtrip_legacy_claims({doc}, findings)

    assert findings == []
