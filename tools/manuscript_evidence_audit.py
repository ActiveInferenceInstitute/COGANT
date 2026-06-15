#!/usr/bin/env python3
"""Build a section-by-section manuscript evidence matrix.

The claim ledger records individual claims. This audit answers a different
review question: does each manuscript section expose at least one evidence lane
for readers to follow? It scans manuscript source fragments and summarizes
citations, metric tokens, figure references, artifact paths, validator commands,
and limitation/boundary wording into JSON, Markdown, and a compact PNG matrix.
"""

from __future__ import annotations

import argparse
import json
import re
import zlib
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
OUTPUT_DIR = ROOT / "output" / "analysis"
DEFAULT_JSON = OUTPUT_DIR / "manuscript_evidence_audit.json"
DEFAULT_MARKDOWN = OUTPUT_DIR / "manuscript_evidence_audit.md"
DEFAULT_PNG = OUTPUT_DIR / "manuscript_evidence_audit.png"

EXCLUDED_FILES = {
    "AGENTS.md",
    "README.md",
    "SYNTAX.md",
    "config.yaml",
    "preamble.md",
    "references.bib",
}
REFERENCE_PREFIXES = (
    "sec",
    "tbl",
    "fig",
    "eq",
    "lst",
    "def",
    "prop",
    "inv",
    "conj",
    "alg",
    "thm",
)

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
CITATION_RE = re.compile(r"(?<![\w`])@([A-Za-z][A-Za-z0-9_:-]+)")
FIGURE_RE = re.compile(r"!\[[^\]]*\]\((?:\.\./)?figures/[^)]+\)|@fig:[A-Za-z0-9_:-]+")
PATH_RE = re.compile(
    r"`((?:\.\./)?(?:cogant|tools|scripts|output|manuscript)/[^`]+|"
    r"(?:cogant|tools|scripts|output)/[^`]+)`"
)
VALIDATOR_RE = re.compile(
    r"\b(uv run|pytest|ruff|mypy|audit_[A-Za-z0-9_]+|verify_[A-Za-z0-9_]+|"
    r"claim_ledger|manuscript_figures|visualization_quality_audit)\b"
)
BOUNDARY_RE = re.compile(
    r"\b(does not|do not|not a|not an|not claim|not prove|not sufficient|"
    r"future work|limitation|scope|boundary|caveat|degraded-output)\b",
    re.IGNORECASE,
)

LANES = (
    ("citations", "Citations"),
    ("metric_tokens", "Metrics"),
    ("figures", "Figures"),
    ("artifact_paths", "Artifacts"),
    ("validators", "Validators"),
    ("boundary_terms", "Boundaries"),
)
SUPPORT_LANES = (
    "citations",
    "metric_tokens",
    "figures",
    "artifact_paths",
    "validators",
)
LANE_DEFINITIONS = {
    "citations": "Scholarly or source citation keys, excluding intra-manuscript cross-references.",
    "metric_tokens": "Template variables resolved from METRICS.yaml or generated artifacts.",
    "figures": "Figure references or figure cross-references.",
    "artifact_paths": "Backticked paths to package, tool, output, script, or manuscript artifacts.",
    "validators": "Command or tool references that readers can run as checks.",
    "boundary_terms": "Limitation, caveat, future-work, or negative-scope language.",
}
REVIEW_ACTIONS = {
    "add_independent_lane": "Add another evidence lane if the section carries substantive claims",
    "add_boundary": "Check whether limitation or scope-boundary wording is needed",
    "add_scholarly_anchor": "Add or verify a primary scholarly/source citation anchor",
    "add_validator_or_artifact": "Add or verify a runnable validator, metric, figure, or artifact path",
}

_FONT_5X7 = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
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


def _body_files(manuscript_dir: Path) -> list[Path]:
    return [
        path
        for path in sorted(manuscript_dir.glob("*.md"))
        if path.name not in EXCLUDED_FILES
    ]


def _citation_count(text: str) -> int:
    count = 0
    for match in CITATION_RE.finditer(text):
        key = match.group(1)
        if key.split(":", 1)[0] in REFERENCE_PREFIXES:
            continue
        count += 1
    return count


def _line_count(text: str, regex: re.Pattern[str]) -> int:
    return sum(1 for line in text.splitlines() if regex.search(line))


def _file_record(path: Path, manuscript_dir: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    counts = {
        "citations": _citation_count(text),
        "metric_tokens": len(PLACEHOLDER_RE.findall(text)),
        "figures": len(FIGURE_RE.findall(text)),
        "artifact_paths": len(PATH_RE.findall(text)),
        "validators": _line_count(text, VALIDATOR_RE),
        "boundary_terms": _line_count(text, BOUNDARY_RE),
    }
    lanes_present = [name for name, _ in LANES if counts[name] > 0]
    findings: list[str] = []
    support_lanes = [name for name in SUPPORT_LANES if counts[name] > 0]
    if not support_lanes:
        findings.append("no evidence support lane")
    if path.name.startswith(("08_", "S05_")) and counts["citations"] == 0:
        findings.append("scholarship section has no citation lane")
    if path.name.startswith(("04_", "06_", "07_", "09_")) and not (
        counts["figures"]
        or counts["artifact_paths"]
        or counts["validators"]
        or counts["metric_tokens"]
    ):
        findings.append(
            "empirical/reproducibility section has no artifact, validator, figure, or metric lane"
        )
    review_actions: list[str] = []
    if len(support_lanes) < 3:
        review_actions.append("add_independent_lane")
    if counts["boundary_terms"] == 0:
        review_actions.append("add_boundary")
    if path.name.startswith(("08_", "S05_")) and counts["citations"] == 0:
        review_actions.append("add_scholarly_anchor")
    if path.name.startswith(("04_", "06_", "07_", "09_")) and counts["validators"] == 0:
        review_actions.append("add_validator_or_artifact")
    return {
        "file": path.relative_to(manuscript_dir).as_posix(),
        "counts": counts,
        "lanes_present": lanes_present,
        "support_lanes": support_lanes,
        "support_lane_count": len(support_lanes),
        "boundary_lane_present": counts["boundary_terms"] > 0,
        "review_actions": review_actions,
        "review_action_text": [REVIEW_ACTIONS[action] for action in review_actions],
        "status": "pass" if not findings else "fail",
        "findings": findings,
    }


def build_manuscript_evidence_audit(
    manuscript_dir: Path = MANUSCRIPT_DIR,
) -> dict[str, Any]:
    """Return the section evidence matrix for source manuscript fragments."""

    if not manuscript_dir.is_dir():
        raise FileNotFoundError(f"manuscript directory not found: {manuscript_dir}")
    sections = [_file_record(path, manuscript_dir) for path in _body_files(manuscript_dir)]
    failed = [record for record in sections if record["status"] != "pass"]
    by_lane: dict[str, dict[str, int]] = {}
    for name, _label in LANES:
        present = sum(1 for record in sections if record["counts"][name] > 0)
        by_lane[name] = {"present": present, "absent": len(sections) - present}
    weakest_sections = sorted(
        (
            {
                "file": record["file"],
                "status": record["status"],
                "support_lane_count": record["support_lane_count"],
                "support_lanes": record["support_lanes"],
                "boundary_lane_present": record["boundary_lane_present"],
                "review_actions": record["review_actions"],
                "review_action_text": record["review_action_text"],
                "findings": record["findings"],
            }
            for record in sections
        ),
        key=lambda item: (
            item["support_lane_count"],
            item["boundary_lane_present"],
            item["file"],
        ),
    )[:8]
    review_queue = [
        {
            "file": record["file"],
            "status": record["status"],
            "support_lane_count": record["support_lane_count"],
            "boundary_lane_present": record["boundary_lane_present"],
            "review_actions": record["review_actions"],
            "review_action_text": record["review_action_text"],
            "findings": record["findings"],
        }
        for record in sorted(
            sections,
            key=lambda record: (
                0 if record["findings"] else 1,
                record["support_lane_count"],
                record["boundary_lane_present"],
                -len(record["review_actions"]),
                record["file"],
            ),
        )
        if record["findings"] or record["review_actions"]
    ][:10]
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "manuscript_dir": (
            str(manuscript_dir.relative_to(ROOT))
            if manuscript_dir.is_relative_to(ROOT)
            else str(manuscript_dir)
        ),
        "summary": {
            "total_sections": len(sections),
            "passed": len(sections) - len(failed),
            "failed": len(failed),
            "by_lane": by_lane,
            "weakest_sections": weakest_sections,
            "review_queue": review_queue,
        },
        "review_action_definitions": REVIEW_ACTIONS,
        "lane_definitions": LANE_DEFINITIONS,
        "sections": sections,
    }


def write_json(report: dict[str, Any], path: Path = DEFAULT_JSON) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _issue_text(issues: Iterable[str]) -> str:
    joined = "; ".join(issues)
    return joined if joined else "none"


def _action_text(actions: Iterable[str]) -> str:
    labels = [REVIEW_ACTIONS.get(action, action) for action in actions]
    return "; ".join(labels) if labels else "none"


def write_markdown(report: dict[str, Any], path: Path = DEFAULT_MARKDOWN) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = report["summary"]
    lines = [
        "# Manuscript Evidence Audit",
        "",
        "This report summarizes section-level evidence lanes in source manuscript fragments.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total sections | {summary['total_sections']} |",
        f"| Passed | {summary['passed']} |",
        f"| Failed | {summary['failed']} |",
        "",
        "## Review Priorities",
        "",
        "Lowest support-lane sections are not automatically wrong, but they are the first places to inspect when strengthening scholarship, reproducibility, or claim boundaries.",
        "",
        "| Section | Status | Support lanes | Boundary lane | Reviewer action | Findings |",
        "|---|---|---:|---|---|---|",
    ]
    for item in summary["weakest_sections"]:
        lanes = ", ".join(item["support_lanes"]) if item["support_lanes"] else "none"
        boundary = "yes" if item["boundary_lane_present"] else "no"
        lines.append(
            "| `{file}` | {status} | {count}: {lanes} | {boundary} | {actions} | {findings} |".format(
                file=item["file"],
                status=item["status"],
                count=item["support_lane_count"],
                lanes=lanes,
                boundary=boundary,
                actions=_action_text(item["review_actions"]),
                findings=_issue_text(item["findings"]),
            )
        )
    lines.extend(
        [
            "",
            "## Suggested Review Queue",
            "",
            "These are non-fatal cues. They help reviewers distinguish a clean but thin section from a blocked section.",
            "",
            "| Section | Suggested action | Current support lanes |",
            "|---|---|---:|",
        ]
    )
    for item in summary["review_queue"]:
        lines.append(
            "| `{file}` | {actions} | {count} |".format(
                file=item["file"],
                actions=_action_text(item["review_actions"]),
                count=item["support_lane_count"],
            )
        )
    lines.extend(
        [
            "",
            "## Section Matrix",
            "",
            "| Section | Status | Citations | Metrics | Figures | Artifacts | Validators | Boundaries | Findings |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for item in report["sections"]:
        counts = item["counts"]
        lines.append(
            "| `{file}` | {status} | {citations} | {metrics} | {figures} | {artifacts} | "
            "{validators} | {boundaries} | {findings} |".format(
                file=item["file"],
                status=item["status"],
                citations=counts["citations"],
                metrics=counts["metric_tokens"],
                figures=counts["figures"],
                artifacts=counts["artifact_paths"],
                validators=counts["validators"],
                boundaries=counts["boundary_terms"],
                findings=_issue_text(item["findings"]),
            )
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return (
        len(payload).to_bytes(4, "big")
        + kind
        + payload
        + crc.to_bytes(4, "big")
    )


def _clean_label(text: str, max_chars: int) -> str:
    return re.sub(r"[^A-Z0-9 -]", " ", text.upper())[:max_chars]


def _write_native_png_matrix(report: dict[str, Any], path: Path) -> Path:
    sections = report["sections"]
    cell_w = 76
    cell_h = 22
    label_w = 314
    top_h = 58
    margin = 14
    width = label_w + len(LANES) * cell_w + margin
    height = top_h + max(1, len(sections)) * cell_h + margin
    ok_rgb = (0, 114, 178)
    empty_rgb = (214, 221, 231)
    fail_rgb = (213, 94, 0)
    grid_rgb = (255, 255, 255)
    bg_rgb = (246, 248, 251)
    text_rgb = (31, 41, 55)
    pixels = bytearray(bg_rgb * width * height)

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
        for char in _clean_label(text, 120):
            glyph = _FONT_5X7.get(char, _FONT_5X7[" "])
            for gy, line in enumerate(glyph):
                for gx, bit in enumerate(line):
                    if bit == "1":
                        set_pixel(x + gx, y0 + gy, rgb)
            x += 6

    draw_text("MANUSCRIPT EVIDENCE LANES", margin, 14, text_rgb)
    for col, (_name, label) in enumerate(LANES):
        draw_text(label, label_w + col * cell_w + 4, 38, text_rgb)

    for row_idx, section in enumerate(sections):
        y0 = top_h + row_idx * cell_h
        label_rgb = fail_rgb if section["status"] != "pass" else text_rgb
        draw_text(section["file"].replace(".md", ""), margin, y0 + 7, label_rgb)
        for col, (name, _label) in enumerate(LANES):
            x0 = label_w + col * cell_w
            present = section["counts"][name] > 0
            color = ok_rgb if present else empty_rgb
            fill_rect(x0 + 1, y0 + 1, cell_w - 2, cell_h - 2, color)
            draw_text("YES" if present else "--", x0 + 26, y0 + 7, grid_rgb)

    scanlines = b"".join(
        b"\x00" + pixels[y * width * 3 : (y + 1) * width * 3]
        for y in range(height)
    )
    ihdr = width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(scanlines, 9))
        + _png_chunk(b"IEND", b"")
    )
    return path


def _write_matplotlib_png(report: dict[str, Any], path: Path) -> Path | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
    except Exception:
        return None

    sections = [section["file"].replace(".md", "") for section in report["sections"]]
    values = [
        [1 if section["counts"][name] > 0 else 0 for name, _label in LANES]
        for section in report["sections"]
    ]
    height = max(8.0, min(14.0, 1.1 + 0.31 * max(1, len(sections))))
    fig, ax = plt.subplots(figsize=(9.5, height), dpi=180)
    ax.imshow(values, aspect="auto", cmap=ListedColormap(["#d8dee8", "#0072b2"]))
    ax.set_xticks(
        range(len(LANES)),
        [label for _name, label in LANES],
        rotation=30,
        ha="right",
    )
    ax.set_yticks(range(len(sections)), sections)
    ax.tick_params(axis="both", labelsize=7, length=0)
    for y_idx, section in enumerate(report["sections"]):
        if section["status"] != "pass":
            ax.get_yticklabels()[y_idx].set_color("#b00020")
            ax.get_yticklabels()[y_idx].set_fontweight("bold")
    ax.set_title("Manuscript Evidence Lanes by Section", fontsize=11, pad=12)
    ax.set_xlabel("Evidence lane")
    ax.set_ylabel("Source manuscript section")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([x - 0.5 for x in range(1, len(LANES))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(sections))], minor=True)
    ax.grid(which="minor", color="white", linewidth=1.0)
    ax.tick_params(which="minor", bottom=False, left=False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def write_png_matrix(report: dict[str, Any], path: Path = DEFAULT_PNG) -> Path:
    rendered = _write_matplotlib_png(report, path)
    if rendered is not None:
        return rendered
    return _write_native_png_matrix(report, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript-dir", type=Path, default=MANUSCRIPT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--output-png", type=Path, default=DEFAULT_PNG)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero if any section fails.")
    args = parser.parse_args()

    report = build_manuscript_evidence_audit(args.manuscript_dir)
    write_json(report, args.output_json)
    write_markdown(report, args.output_md)
    write_png_matrix(report, args.output_png)
    failed = report["summary"]["failed"]
    print(
        "manuscript_evidence_audit: "
        f"{report['summary']['passed']} passed, {failed} failed -> {args.output_json}"
    )
    print(f"manuscript_evidence_audit: matrix -> {args.output_png}")
    return 1 if args.strict and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
