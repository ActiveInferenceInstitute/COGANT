"""Regression tests for ``tools/claim_ledger.py``."""

from __future__ import annotations

import importlib.util
import json
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


def test_strict_literal_number_gate_ignores_split_inline_math_numbers(tmp_path: Path) -> None:
    records = _records_for(
        tmp_path,
        "The update uses $B[s_t, s_{t-1}, a_{t-1}]\n"
        "\\cdot Q(s_{t-1})$ as a finite categorical product.\n",
    )

    assert _actionable(records) == []
    assert any(
        record.kind == "literal_number"
        and record.text == "1"
        and record.classification == "math_notation"
        for record in records
    )


def test_strict_literal_number_gate_reports_plain_prose_number(tmp_path: Path) -> None:
    records = _records_for(
        tmp_path,
        "This unsupported prose claim says the pipeline handled 42 repositories.\n",
    )

    actionable = _actionable(records)
    assert len(actionable) == 1
    assert actionable[0].text == "42"
    assert actionable[0].classification == "actionable_literal_number"


def test_formal_references_are_validator_backed_in_ledger(tmp_path: Path) -> None:
    records = _records_for(
        tmp_path,
        "The proof sketch refers to @def:program-graph and @prop:matrix-validity.\n",
    )

    formal_records = [record for record in records if record.kind == "citation"]
    assert {record.text for record in formal_records} == {
        "@def:program-graph",
        "@prop:matrix-validity",
    }
    assert {
        record.evidence_hint for record in formal_records
    } == {"validator-backed manuscript cross-reference"}


def test_write_ledger_emits_template_evidence_seed(tmp_path: Path) -> None:
    module = _load_module()
    records = _records_for(
        tmp_path,
        "The proof sketch cites @def:program-graph and reports 42 review rows.\n",
    )

    paths = module.write_ledger(records, tmp_path / "output")

    seed_path = paths["template_evidence"]
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    claims = payload["claims"]
    assert seed_path.name == "template_evidence_claim_ledger.json"
    assert any(
        claim["kind"] == "citation" and claim["value"] == "def:program-graph"
        for claim in claims
    )
    assert any(claim["kind"] == "number" and claim["value"] == "42" for claim in claims)
