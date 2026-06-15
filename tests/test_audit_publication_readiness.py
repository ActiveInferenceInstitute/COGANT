from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from audit_publication_readiness import (  # noqa: E402
    build_publication_readiness,
    classify_claim_record,
    render_markdown,
)


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_config(root: Path, rel_path: str, date: str = "") -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        'paper:\n'
        '  title: "COGANT: Deterministic Codebase-to-GNN Translation"\n'
        f'  date: "{date}"\n',
        encoding="utf-8",
    )


def _fixture_root(
    tmp_path: Path,
    *,
    source_date: str = "",
    output_date: str = "",
    claim_records: list[dict[str, object]] | None = None,
    review_queue: list[dict[str, object]] | None = None,
) -> Path:
    root = tmp_path / "project"
    _write_config(root, "manuscript/config.yaml", source_date)
    _write_config(root, "output/manuscript/config.yaml", output_date)
    _write_json(
        root / "output" / "claim_ledger.json",
        {
            "record_count": len(claim_records or []),
            "records": claim_records or [],
        },
    )
    _write_json(
        root / "output" / "analysis" / "manuscript_evidence_audit.json",
        {
            "summary": {
                "failed": 0,
                "review_queue": review_queue or [],
            },
            "sections": [],
        },
    )
    _write_json(
        root / "output" / "figures" / "visual_quality_audit.json",
        {
            "summary": {
                "failed": 0,
            },
            "figures": [],
        },
    )
    _write_json(
        root / "output" / "figures" / "manifest.json",
        {
            "figures": [
                {
                    "key": "graphical_abstract",
                    "source": "cogant/output/calculator/figures/graphical_abstract.png",
                    "metadata_complete": True,
                }
            ],
        },
    )
    _write_json(
        root / "output" / "analysis" / "manuscript_review_dashboard.json",
        {
            "status": "pass",
            "issues": [],
            "checks": [],
        },
    )
    return root


def _readiness(root: Path) -> dict[str, object]:
    return build_publication_readiness(root=root, run_external_audits=False)


def test_blank_publication_date_is_ready(tmp_path: Path) -> None:
    report = _readiness(_fixture_root(tmp_path))

    assert report["verdict"] == "ready"
    date_check = next(check for check in report["checks"] if check["name"] == "publication_date_autofill")
    assert date_check["passed"] is True


def test_fixed_publication_date_blocks_readiness(tmp_path: Path) -> None:
    report = _readiness(_fixture_root(tmp_path, source_date="2026-05-22"))

    assert report["verdict"] == "blocked"
    assert any("fixed publication date" in blocker for blocker in report["blockers"])


def test_actionable_literal_number_blocks_readiness(tmp_path: Path) -> None:
    root = _fixture_root(
        tmp_path,
        claim_records=[
            {
                "file": "01_introduction.md",
                "line": 10,
                "kind": "literal_number",
                "text": "42",
                "classification": "actionable_literal_number",
            }
        ],
    )

    report = _readiness(root)

    assert report["verdict"] == "blocked"
    assert report["claim_summary"]["unsupported_count"] == 1
    assert report["claim_summary"]["actionable_literal_count"] == 1


def test_review_queue_keeps_caveated_verdict(tmp_path: Path) -> None:
    report = _readiness(
        _fixture_root(
            tmp_path,
            review_queue=[
                {
                    "file": "01_introduction.md",
                    "support_lane_count": 2,
                }
            ],
        )
    )

    assert report["verdict"] == "ready_with_caveats"
    assert "review queue" in report["caveats"][0]
    assert "ready_with_caveats" in render_markdown(report)


def test_claim_classification_primitives() -> None:
    assert classify_claim_record({"kind": "placeholder", "text": "{{ROUNDTRIP_TARGETS}}"}) == "metric-backed"
    assert classify_claim_record({"kind": "citation", "text": "@fig:graphical-abstract"}) == "artifact-backed"
    assert classify_claim_record({"kind": "citation", "text": "@sec:evaluation"}) == "validator-backed"
    assert classify_claim_record({"kind": "citation", "text": "@def:program-graph"}) == "validator-backed"
    assert (
        classify_claim_record(
            {"kind": "citation", "text": "@prop:fixpoint-termination"}
        )
        == "validator-backed"
    )
    assert classify_claim_record({"kind": "citation", "text": "@friston2010freeEnergy"}) == "citation-backed"
    assert classify_claim_record({"kind": "path", "text": "`../cogant/output/run_manifest.json`"}) == "artifact-backed"
    assert (
        classify_claim_record(
            {
                "kind": "literal_number",
                "text": "0 of 24 is a limitation, not arbitrary-program semantic equivalence.",
                "classification": "metric_or_protocol_context",
            }
        )
        == "boundary/limitation"
    )
