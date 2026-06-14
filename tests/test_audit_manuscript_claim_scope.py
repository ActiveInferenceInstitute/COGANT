from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import audit_manuscript_claim_scope as audit  # noqa: E402


def test_claim_scope_audit_rejects_positive_guarantee(tmp_path: Path) -> None:
    doc = tmp_path / "bad.md"
    doc.write_text("The method guarantees semantic correctness.\n", encoding="utf-8")

    findings = audit.audit([doc])

    assert findings
    assert "positive-guarantee" in findings[0]


def test_claim_scope_audit_allows_negated_guarantee(tmp_path: Path) -> None:
    doc = tmp_path / "good.md"
    doc.write_text("The method does not guarantee semantic correctness.\n", encoding="utf-8")

    assert audit.audit([doc]) == []


def test_claim_scope_audit_rejects_uncaveated_confidence_interval(tmp_path: Path) -> None:
    doc = tmp_path / "bad.md"
    doc.write_text("We report a confidence interval for the fixture score.\n", encoding="utf-8")

    findings = audit.audit([doc])

    assert findings
    assert "uncaveated-inferential-statistics" in findings[0]


def test_claim_scope_audit_allows_no_confidence_interval_caveat(tmp_path: Path) -> None:
    doc = tmp_path / "good.md"
    doc.write_text("There is no confidence interval on this in-sample aggregate.\n", encoding="utf-8")

    assert audit.audit([doc]) == []


def test_claim_scope_audit_rejects_semantic_totality(tmp_path: Path) -> None:
    doc = tmp_path / "bad.md"
    doc.write_text("The matrices fully capture source-code behavior.\n", encoding="utf-8")

    findings = audit.audit([doc])

    assert findings
    assert "semantic-totality-overclaim" in findings[0]


def test_claim_scope_audit_allows_negated_semantic_totality(tmp_path: Path) -> None:
    doc = tmp_path / "good.md"
    doc.write_text("The validator does not prove that matrices fully capture behavior.\n", encoding="utf-8")

    assert audit.audit([doc]) == []
