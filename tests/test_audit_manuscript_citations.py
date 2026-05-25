"""Regression tests for ``tools/audit_manuscript_citations.py``."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "audit_manuscript_citations.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_manuscript_citations", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_fixture(tmp_path: Path, body: str, bib: str) -> tuple[Path, Path]:
    manuscript_dir = tmp_path / "manuscript"
    manuscript_dir.mkdir()
    (manuscript_dir / "01_body.md").write_text(body, encoding="utf-8")
    (manuscript_dir / "SYNTAX.md").write_text("@missingFromSyntax", encoding="utf-8")
    bib_path = manuscript_dir / "references.bib"
    bib_path.write_text(bib, encoding="utf-8")
    return manuscript_dir, bib_path


def test_audit_accepts_known_keys_and_ignores_code_and_crossrefs(tmp_path: Path) -> None:
    module = _load_module()
    manuscript_dir, bib_path = _write_fixture(
        tmp_path,
        "A cited claim [@known]. A section pointer @sec:intro.\n"
        "`@not_a_citation`\n"
        "```text\n@also_not_a_citation\n```\n",
        "@article{known,\n  title = {Known},\n  year = {2026}\n}\n",
    )

    missing, duplicates, unused = module.audit(manuscript_dir, bib_path)

    assert missing == []
    assert duplicates == []
    assert unused == []


def test_audit_reports_missing_used_key(tmp_path: Path) -> None:
    module = _load_module()
    manuscript_dir, bib_path = _write_fixture(
        tmp_path,
        "A cited claim [@missing].\n",
        "@article{known,\n  title = {Known},\n  year = {2026}\n}\n",
    )

    missing, duplicates, unused = module.audit(manuscript_dir, bib_path)

    assert missing == ["missing"]
    assert duplicates == []
    assert unused == ["known"]


def test_audit_reports_duplicate_bib_key(tmp_path: Path) -> None:
    module = _load_module()
    manuscript_dir, bib_path = _write_fixture(
        tmp_path,
        "A cited claim [@known].\n",
        "@article{known,\n  title = {Known A},\n  year = {2026}\n}\n"
        "@misc{known,\n  title = {Known B},\n  year = {2026}\n}\n",
    )

    missing, duplicates, unused = module.audit(manuscript_dir, bib_path)

    assert missing == []
    assert duplicates == ["known"]
    assert unused == []
