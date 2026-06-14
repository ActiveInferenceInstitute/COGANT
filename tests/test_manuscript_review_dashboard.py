from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from manuscript_review_dashboard import (  # noqa: E402
    build_review_dashboard,
    write_json,
    write_markdown,
    write_png,
)


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fixture_inputs(tmp_path: Path, *, visual_failed: int = 0, actionable: bool = False) -> dict[str, Path]:
    evidence = _write_json(
        tmp_path / "evidence.json",
        {
            "summary": {
                "total_sections": 2,
                "passed": 2,
                "failed": 0,
                "weakest_sections": [
                    {
                        "file": "thin.md",
                        "support_lane_count": 1,
                        "support_lanes": ["citations"],
                        "boundary_lane_present": True,
                        "review_actions": ["add_independent_lane"],
                        "review_action_text": [
                            "Add another evidence lane if the section carries substantive claims"
                        ],
                    }
                ],
                "review_queue": [
                    {
                        "file": "thin.md",
                        "support_lane_count": 1,
                        "support_lanes": ["citations"],
                        "boundary_lane_present": True,
                        "review_actions": ["add_independent_lane"],
                        "review_action_text": [
                            "Add another evidence lane if the section carries substantive claims"
                        ],
                    }
                ],
            }
        },
    )
    visual = _write_json(
        tmp_path / "visual.json",
        {"summary": {"total_figures": 1, "passed": 1 - visual_failed, "failed": visual_failed}},
    )
    claim_records = [
        {
            "file": "body.md",
            "line": 3,
            "kind": "literal_number",
            "text": "42",
            "evidence_hint": "manual review",
            "classification": "actionable_literal_number",
        }
    ] if actionable else []
    claims = _write_json(
        tmp_path / "claim_ledger.json",
        {"record_count": len(claim_records), "records": claim_records},
    )
    manifest = _write_json(
        tmp_path / "manifest.json",
        {
            "figures": [
                {
                    "copied": True,
                    "source_artifact_exists": True,
                    "destination_figure_sidecar_exists": True,
                    "metadata_complete": True,
                }
            ]
        },
    )
    return {
        "evidence_path": evidence,
        "visual_path": visual,
        "claim_path": claims,
        "figure_manifest_path": manifest,
    }


def test_review_dashboard_passes_clean_inputs(tmp_path: Path) -> None:
    report = build_review_dashboard(**_fixture_inputs(tmp_path))

    assert report["status"] == "pass"
    assert report["checks"]["evidence_audit_clean"] is True
    assert report["summary"]["claims"]["actionable_literal_numbers"] == 0
    assert report["summary"]["review_queue"][0]["file"] == "thin.md"


def test_review_dashboard_fails_visual_quality_failure(tmp_path: Path) -> None:
    report = build_review_dashboard(**_fixture_inputs(tmp_path, visual_failed=1))

    assert report["status"] == "fail"
    assert "visual quality audit has 1 failed figure(s)" in report["issues"]


def test_review_dashboard_fails_actionable_literal_claim(tmp_path: Path) -> None:
    report = build_review_dashboard(**_fixture_inputs(tmp_path, actionable=True))

    assert report["status"] == "fail"
    assert "claim ledger has 1 actionable literal number(s)" in report["issues"]


def test_review_dashboard_requires_inputs(tmp_path: Path) -> None:
    inputs = _fixture_inputs(tmp_path)
    inputs["claim_path"] = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        build_review_dashboard(**inputs)


def test_review_dashboard_writes_artifacts(tmp_path: Path) -> None:
    report = build_review_dashboard(**_fixture_inputs(tmp_path))

    json_path = write_json(report, tmp_path / "dashboard.json")
    md_path = write_markdown(report, tmp_path / "dashboard.md")
    png_path = write_png(report, tmp_path / "dashboard.png")

    assert json.loads(json_path.read_text(encoding="utf-8"))["status"] == "pass"
    assert "## Review Priorities" in md_path.read_text(encoding="utf-8")
    assert "## Review Queue" in md_path.read_text(encoding="utf-8")
    assert png_path.read_bytes().startswith(b"\x89PNG")
