from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import audit_current_only_language as audit  # noqa: E402


def test_current_only_language_audit_rejects_removed_gnn_marker(tmp_path: Path) -> None:
    doc = tmp_path / "bad.md"
    doc.write_text("## GNNVersionAndFlags\nGNN v" + "1\n", encoding="utf-8")

    findings = audit.audit([doc])

    assert findings
    assert "removed-gnn-version" in findings[0]


def test_current_only_language_audit_accepts_current_gnn_marker(tmp_path: Path) -> None:
    doc = tmp_path / "good.md"
    doc.write_text("## GNNVersionAndFlags\nGNN v2.0.0\n", encoding="utf-8")

    assert audit.audit([doc]) == []
