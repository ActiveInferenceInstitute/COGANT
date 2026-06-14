#!/usr/bin/env python3
"""Combine manuscript review artifacts into one dashboard.

Individual audits answer narrow questions: figure sidecars, evidence lanes,
and claim-token inventory. This dashboard gives reviewers a single current
surface for the manuscript's publication-readiness state while preserving the
source JSON paths for drill-down.
"""

from __future__ import annotations

import argparse
import json
import zlib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
ANALYSIS_DIR = OUTPUT_DIR / "analysis"
DEFAULT_EVIDENCE = ANALYSIS_DIR / "manuscript_evidence_audit.json"
DEFAULT_VISUAL = OUTPUT_DIR / "figures" / "visual_quality_audit.json"
DEFAULT_CLAIMS = OUTPUT_DIR / "claim_ledger.json"
DEFAULT_FIGURE_MANIFEST = OUTPUT_DIR / "figures" / "manifest.json"
DEFAULT_JSON = ANALYSIS_DIR / "manuscript_review_dashboard.json"
DEFAULT_MARKDOWN = ANALYSIS_DIR / "manuscript_review_dashboard.md"
DEFAULT_PNG = ANALYSIS_DIR / "manuscript_review_dashboard.png"

_FONT_5X7 = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10011", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00001", "00001", "00001", "00001", "10001", "10001", "01110"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"review input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _count_manifest_issue(figures: list[dict[str, Any]], key: str) -> int:
    return sum(1 for figure in figures if figure.get(key) is not True)


def build_review_dashboard(
    *,
    evidence_path: Path = DEFAULT_EVIDENCE,
    visual_path: Path = DEFAULT_VISUAL,
    claim_path: Path = DEFAULT_CLAIMS,
    figure_manifest_path: Path = DEFAULT_FIGURE_MANIFEST,
) -> dict[str, Any]:
    evidence = _read_json(evidence_path)
    visual = _read_json(visual_path)
    claims = _read_json(claim_path)
    manifest = _read_json(figure_manifest_path)

    records = claims.get("records", [])
    if not isinstance(records, list):
        records = []
    kind_counts = Counter(str(record.get("kind") or "") for record in records)
    actionable_numbers = [
        record
        for record in records
        if record.get("kind") == "literal_number"
        and record.get("classification") == "actionable_literal_number"
    ]

    figures = manifest.get("figures", [])
    if not isinstance(figures, list):
        figures = []
    visual_summary = visual.get("summary", {})
    evidence_summary = evidence.get("summary", {})
    manifest_summary = {
        "total_figures": len(figures),
        "missing_copies": _count_manifest_issue(figures, "copied"),
        "missing_source_artifacts": _count_manifest_issue(figures, "source_artifact_exists"),
        "missing_sidecars": _count_manifest_issue(figures, "destination_figure_sidecar_exists"),
        "incomplete_metadata": sum(1 for figure in figures if figure.get("metadata_complete") is False),
    }
    claim_summary = {
        "record_count": int(claims.get("record_count") or len(records)),
        "actionable_literal_numbers": len(actionable_numbers),
        "by_kind": dict(sorted(kind_counts.items())),
    }
    checks = {
        "evidence_audit_clean": int(evidence_summary.get("failed") or 0) == 0,
        "visual_quality_clean": int(visual_summary.get("failed") or 0) == 0,
        "claim_ledger_clean": len(actionable_numbers) == 0,
        "figure_manifest_clean": all(value == 0 for value in manifest_summary.values() if isinstance(value, int)) or (
            manifest_summary["total_figures"] > 0
            and manifest_summary["missing_copies"] == 0
            and manifest_summary["missing_source_artifacts"] == 0
            and manifest_summary["missing_sidecars"] == 0
            and manifest_summary["incomplete_metadata"] == 0
        ),
    }
    issues: list[str] = []
    if not checks["evidence_audit_clean"]:
        issues.append(f"evidence audit has {evidence_summary.get('failed')} failed section(s)")
    if not checks["visual_quality_clean"]:
        issues.append(f"visual quality audit has {visual_summary.get('failed')} failed figure(s)")
    if not checks["claim_ledger_clean"]:
        issues.append(f"claim ledger has {len(actionable_numbers)} actionable literal number(s)")
    if not checks["figure_manifest_clean"]:
        issues.append("figure manifest has missing copies, sources, sidecars, or metadata")

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "inputs": {
            "evidence_audit": _rel(evidence_path),
            "visual_quality_audit": _rel(visual_path),
            "claim_ledger": _rel(claim_path),
            "figure_manifest": _rel(figure_manifest_path),
        },
        "status": "pass" if not issues else "fail",
        "checks": checks,
        "issues": issues,
        "summary": {
            "evidence": evidence_summary,
            "visual_quality": visual_summary,
            "claims": claim_summary,
            "figure_manifest": manifest_summary,
            "weakest_sections": evidence_summary.get("weakest_sections", [])[:5],
            "review_queue": evidence_summary.get("review_queue", [])[:5],
            "actionable_literal_examples": actionable_numbers[:5],
        },
    }


def write_json(report: dict[str, Any], path: Path = DEFAULT_JSON) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_markdown(report: dict[str, Any], path: Path = DEFAULT_MARKDOWN) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = report["summary"]
    lines = [
        "# Manuscript Review Dashboard",
        "",
        "This dashboard combines the figure-quality audit, section evidence audit, figure manifest, and claim ledger.",
        "",
        f"Overall status: **{report['status']}**",
        "",
        "| Surface | Status | Key count |",
        "|---|---|---:|",
        f"| Evidence audit | {'pass' if report['checks']['evidence_audit_clean'] else 'fail'} | {summary['evidence'].get('passed', 0)}/{summary['evidence'].get('total_sections', 0)} sections passed |",
        f"| Visual quality audit | {'pass' if report['checks']['visual_quality_clean'] else 'fail'} | {summary['visual_quality'].get('passed', 0)}/{summary['visual_quality'].get('total_figures', 0)} figures passed |",
        f"| Claim ledger | {'pass' if report['checks']['claim_ledger_clean'] else 'fail'} | {summary['claims'].get('actionable_literal_numbers', 0)} actionable literal numbers |",
        f"| Figure manifest | {'pass' if report['checks']['figure_manifest_clean'] else 'fail'} | {summary['figure_manifest'].get('total_figures', 0)} registered figures |",
        "",
        "## Review Priorities",
        "",
        "| Section | Support lanes | Boundary lane | Suggested action |",
        "|---|---:|---|---|",
    ]
    for item in summary.get("weakest_sections", []):
        lanes = ", ".join(item.get("support_lanes") or []) or "none"
        boundary = "yes" if item.get("boundary_lane_present") else "no"
        actions = "; ".join(item.get("review_action_text") or []) or "none"
        lines.append(
            f"| `{item.get('file')}` | {item.get('support_lane_count')}: {lanes} | {boundary} | {actions} |"
        )
    lines.extend(["", "## Review Queue", "", "| Section | Suggested action |", "|---|---|"])
    for item in summary.get("review_queue", []):
        actions = "; ".join(item.get("review_action_text") or []) or "none"
        lines.append(f"| `{item.get('file')}` | {actions} |")
    if report["issues"]:
        lines.extend(["", "## Blocking Issues", ""])
        lines.extend(f"- {issue}" for issue in report["issues"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return len(payload).to_bytes(4, "big") + kind + payload + crc.to_bytes(4, "big")


def _draw_dashboard_png(report: dict[str, Any], path: Path) -> Path:
    width = 980
    height = 430
    bg_rgb = (246, 248, 251)
    text_rgb = (31, 41, 55)
    ok_rgb = (0, 114, 178)
    fail_rgb = (213, 94, 0)
    pale_rgb = (214, 221, 231)
    white_rgb = (255, 255, 255)
    pixels = bytearray(bg_rgb * (width * height))

    def set_pixel(x: int, y: int, rgb: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            pos = (y * width + x) * 3
            pixels[pos : pos + 3] = bytes(rgb)

    def fill_rect(x0: int, y0: int, rect_w: int, rect_h: int, rgb: tuple[int, int, int]) -> None:
        for yy in range(y0, y0 + rect_h):
            for xx in range(x0, x0 + rect_w):
                set_pixel(xx, yy, rgb)

    def draw_text(text: str, x0: int, y0: int, rgb: tuple[int, int, int]) -> None:
        x = x0
        cleaned = "".join(char if char.isalnum() or char in " -./" else " " for char in text.upper())
        for char in cleaned[:110]:
            glyph = _FONT_5X7.get(char, _FONT_5X7[" "])
            for gy, line in enumerate(glyph):
                for gx, bit in enumerate(line):
                    if bit == "1":
                        set_pixel(x + gx, y0 + gy, rgb)
            x += 6

    draw_text("COGANT MANUSCRIPT REVIEW DASHBOARD", 28, 26, text_rgb)
    draw_text(f"STATUS {report['status']}", 28, 48, ok_rgb if report["status"] == "pass" else fail_rgb)
    cards = [
        ("EVIDENCE", report["checks"]["evidence_audit_clean"], f"{report['summary']['evidence'].get('passed', 0)}/{report['summary']['evidence'].get('total_sections', 0)} SECTIONS"),
        ("FIGURES", report["checks"]["visual_quality_clean"], f"{report['summary']['visual_quality'].get('passed', 0)}/{report['summary']['visual_quality'].get('total_figures', 0)} PASS"),
        ("CLAIMS", report["checks"]["claim_ledger_clean"], f"{report['summary']['claims'].get('actionable_literal_numbers', 0)} ACTIONABLE"),
        ("MANIFEST", report["checks"]["figure_manifest_clean"], f"{report['summary']['figure_manifest'].get('total_figures', 0)} FIGURES"),
    ]
    card_w = 220
    for idx, (label, ok, value) in enumerate(cards):
        x = 28 + idx * (card_w + 14)
        y = 88
        fill_rect(x, y, card_w, 86, ok_rgb if ok else fail_rgb)
        draw_text(label, x + 12, y + 18, white_rgb)
        draw_text("PASS" if ok else "FAIL", x + 12, y + 40, white_rgb)
        draw_text(value, x + 12, y + 62, white_rgb)

    draw_text("REVIEW QUEUE", 28, 218, text_rgb)
    y = 246
    queue = report["summary"].get("review_queue") or report["summary"].get("weakest_sections", [])
    for item in queue[:5]:
        fill_rect(28, y - 5, 924, 26, pale_rgb)
        draw_text(str(item.get("file", ""))[:42], 40, y + 3, text_rgb)
        draw_text(f"LANES {item.get('support_lane_count')}", 410, y + 3, text_rgb)
        actions = " ".join(item.get("review_actions") or item.get("support_lanes") or [])
        draw_text(actions[:46], 520, y + 3, text_rgb)
        y += 32

    ihdr = width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
    scanlines = b"".join(
        b"\x00" + pixels[y * width * 3 : (y + 1) * width * 3]
        for y in range(height)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(scanlines, 9))
        + _png_chunk(b"IEND", b"")
    )
    return path


def write_png(report: dict[str, Any], path: Path = DEFAULT_PNG) -> Path:
    return _draw_dashboard_png(report, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--visual", type=Path, default=DEFAULT_VISUAL)
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    parser.add_argument("--figure-manifest", type=Path, default=DEFAULT_FIGURE_MANIFEST)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--output-png", type=Path, default=DEFAULT_PNG)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    report = build_review_dashboard(
        evidence_path=args.evidence,
        visual_path=args.visual,
        claim_path=args.claims,
        figure_manifest_path=args.figure_manifest,
    )
    json_path = write_json(report, args.output_json)
    write_markdown(report, args.output_md)
    write_png(report, args.output_png)
    print(f"manuscript_review_dashboard: {report['status']} -> {json_path}")
    print(f"manuscript_review_dashboard: matrix -> {args.output_png}")
    return 1 if args.strict and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
