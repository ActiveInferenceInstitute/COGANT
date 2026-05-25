"""Regression tests for ``tools/claim_ledger.py``."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "claim_ledger.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("claim_ledger", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _records_for(tmp_path: Path, body: str):
    manuscript_dir = tmp_path / "manuscript"
    manuscript_dir.mkdir()
    (manuscript_dir / "01_body.md").write_text(body, encoding="utf-8")
    return _load_module().build_claim_ledger(manuscript_dir)


def _actionable(records) -> list:
    module = _load_module()
    return module.actionable_literal_numbers(records)


def test_strict_literal_number_gate_ignores_structural_markdown_numbers(tmp_path: Path) -> None:
    records = _records_for(
        tmp_path,
        "# Section 08.02 {#sec:08-02-program-analysis}\n"
        "See @sec:06-03-performance-and-fixture-metrics and @tbl:repo-2026-results.\n"
        "| Target | Score |\n"
        "|---|---:|\n"
        "| `calculator` | 100.0 |\n"
        "`../cogant/evaluation/dataset/roundtrip_results.jsonl` records rank 23.\n"
        "```text\n"
        "literal 99 in a code block\n"
        "```\n",
    )

    assert _actionable(records) == []


def test_strict_literal_number_gate_reports_plain_prose_number(tmp_path: Path) -> None:
    records = _records_for(
        tmp_path,
        "This unsupported prose claim says the pipeline handled 42 repositories.\n",
    )

    actionable = _actionable(records)
    assert len(actionable) == 1
    assert actionable[0].text == "42"
    assert actionable[0].classification == "actionable_literal_number"
