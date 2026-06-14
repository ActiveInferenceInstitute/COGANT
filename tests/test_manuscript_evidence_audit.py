from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from manuscript_evidence_audit import (  # noqa: E402
    build_manuscript_evidence_audit,
    write_json,
    write_markdown,
    write_png_matrix,
)


def _write_section(manuscript_dir: Path, name: str, body: str) -> None:
    manuscript_dir.mkdir(parents=True, exist_ok=True)
    (manuscript_dir / name).write_text(body, encoding="utf-8")


def test_evidence_audit_passes_supported_section(tmp_path: Path) -> None:
    manuscript_dir = tmp_path / "manuscript"
    _write_section(
        manuscript_dir,
        "06_00_experimental_setup.md",
        "The run uses {{TEST_COUNT}} and `../cogant/tests/`.\n\n"
        "```bash\n"
        "uv run pytest tests/ -q\n"
        "```\n",
    )

    report = build_manuscript_evidence_audit(manuscript_dir)

    assert report["summary"]["failed"] == 0
    assert report["sections"][0]["counts"]["metric_tokens"] == 1
    assert report["sections"][0]["counts"]["validators"] == 1
    assert report["sections"][0]["support_lane_count"] == 3


def test_evidence_audit_fails_plain_unsupported_section(tmp_path: Path) -> None:
    manuscript_dir = tmp_path / "manuscript"
    _write_section(manuscript_dir, "03_api_and_workflows.md", "This is unsupported prose.\n")

    report = build_manuscript_evidence_audit(manuscript_dir)

    assert report["summary"]["failed"] == 1
    assert report["sections"][0]["findings"] == ["no evidence support lane"]


def test_evidence_audit_requires_citations_for_scholarship_sections(
    tmp_path: Path,
) -> None:
    manuscript_dir = tmp_path / "manuscript"
    _write_section(
        manuscript_dir,
        "08_00_scope_and_related_work.md",
        "This section has a path `../cogant/docs/reference/implementation_status.md` "
        "but no scholarly citation.\n",
    )

    report = build_manuscript_evidence_audit(manuscript_dir)

    assert report["summary"]["failed"] == 1
    assert "scholarship section has no citation lane" in report["sections"][0]["findings"]


def test_evidence_audit_writes_review_artifacts(tmp_path: Path) -> None:
    manuscript_dir = tmp_path / "manuscript"
    _write_section(
        manuscript_dir,
        "08_01_landscape_and_tool_categories.md",
        "Program analysis is an anchor [@cousot1977abstract].\n",
    )
    report = build_manuscript_evidence_audit(manuscript_dir)

    json_path = write_json(report, tmp_path / "audit.json")
    md_path = write_markdown(report, tmp_path / "audit.md")
    png_path = write_png_matrix(report, tmp_path / "audit.png")

    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["passed"] == 1
    assert "| `08_01_landscape_and_tool_categories.md` | pass |" in md_path.read_text(
        encoding="utf-8"
    )
    assert png_path.is_file()
    assert png_path.read_bytes().startswith(b"\x89PNG")


def test_evidence_audit_prioritizes_thin_sections(tmp_path: Path) -> None:
    manuscript_dir = tmp_path / "manuscript"
    _write_section(
        manuscript_dir,
        "01_introduction.md",
        "This section has a metric {{COUNT}} and a boundary limitation.\n",
    )
    _write_section(
        manuscript_dir,
        "04_examples_and_failure_modes.md",
        "This section has a metric {{COUNT}}, `../cogant/output/data.json`, "
        "and a validator command `uv run pytest tests/ -q`.\n",
    )

    report = build_manuscript_evidence_audit(manuscript_dir)
    weakest = report["summary"]["weakest_sections"]

    assert weakest[0]["file"] == "01_introduction.md"
    assert weakest[0]["support_lane_count"] == 1
    assert weakest[0]["review_actions"] == ["add_independent_lane"]
    assert weakest[1]["file"] == "04_examples_and_failure_modes.md"
    assert weakest[1]["support_lane_count"] == 3


def test_evidence_audit_queues_nonfatal_review_actions(tmp_path: Path) -> None:
    manuscript_dir = tmp_path / "manuscript"
    _write_section(manuscript_dir, "supplementary.md", "{{COUNT}} and `../output/data.json`.\n")

    report = build_manuscript_evidence_audit(manuscript_dir)

    assert report["summary"]["failed"] == 0
    assert report["sections"][0]["review_actions"] == [
        "add_independent_lane",
        "add_boundary",
    ]
    assert report["summary"]["review_queue"][0]["file"] == "supplementary.md"
    assert "Check whether limitation or scope-boundary wording" in report["sections"][0][
        "review_action_text"
    ][1]


def test_evidence_audit_markdown_includes_review_priorities(tmp_path: Path) -> None:
    manuscript_dir = tmp_path / "manuscript"
    _write_section(manuscript_dir, "03_api_and_workflows.md", "`../tools/demo.py`\n")
    report = build_manuscript_evidence_audit(manuscript_dir)

    md_path = write_markdown(report, tmp_path / "audit.md")
    text = md_path.read_text(encoding="utf-8")

    assert "## Review Priorities" in text
    assert "## Suggested Review Queue" in text
    assert "| `03_api_and_workflows.md` | pass | 1: artifact_paths | no |" in text
