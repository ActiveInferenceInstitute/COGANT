#!/usr/bin/env python3
"""Summarize manuscript figure visual QA into reviewable artifacts.

The strict figure copier proves each registered publication PNG can be promoted.
This audit is the compact review surface over that proof: it reads
``output/figures/manifest.json`` plus neighboring sidecars, checks every copied
figure against a small set of publication criteria, and writes JSON, Markdown,
and optionally a PNG matrix for human review.
"""

from __future__ import annotations

import argparse
import json
import zlib
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "output" / "figures" / "manifest.json"
DEFAULT_JSON = ROOT / "output" / "figures" / "visual_quality_audit.json"
DEFAULT_MARKDOWN = ROOT / "output" / "figures" / "visual_quality_audit.md"
DEFAULT_PNG = ROOT / "output" / "figures" / "visual_quality_audit.png"

CHECK_LABELS = {
    "sidecar": "Sidecar",
    "source": "Source",
    "nonblank": "Nonblank",
    "color": "Color",
    "dimensions": "Size",
    "degraded": "Renderer",
    "publication": "Publication",
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


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    return root / value


def _flag(record: dict[str, Any], key: str) -> bool:
    value = record.get(key)
    return value is True


def _nested_flag(record: dict[str, Any], key: str) -> bool:
    if _flag(record, key):
        return True
    source_meta = record.get("source_figure_metadata")
    if isinstance(source_meta, dict) and source_meta.get(key) is True:
        return True
    return False


def _dimension_pair(record: dict[str, Any]) -> tuple[int | None, int | None]:
    dims = record.get("dimensions_px")
    if isinstance(dims, dict):
        width = dims.get("width")
        height = dims.get("height")
        return (width if isinstance(width, int) else None, height if isinstance(height, int) else None)
    return None, None


def _check_record(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    key = str(record.get("key") or "")
    issues: list[str] = []
    checks: dict[str, bool] = {}

    def check(name: str, condition: bool, issue: str) -> None:
        checks[name] = condition
        if not condition:
            issues.append(issue)

    sidecar_path = _resolve(root, record.get("destination_figure_sidecar"))
    sidecar_exists = bool(record.get("destination_figure_sidecar_exists"))
    if sidecar_path is not None:
        sidecar_exists = sidecar_exists and sidecar_path.is_file()
    check("sidecar", sidecar_exists, "missing destination sidecar")

    source_artifact = record.get("source_artifact")
    source_digest = (
        record.get("source_artifact_digest")
        or record.get("source_artifact_sha256")
        or record.get("data_digest_sha256")
    )
    check(
        "source",
        isinstance(source_artifact, str) and bool(source_artifact) and isinstance(source_digest, str),
        "missing source artifact or digest",
    )

    visual_qa = record.get("visual_qa") if isinstance(record.get("visual_qa"), dict) else {}
    check("nonblank", visual_qa.get("nonblank") is True, "image is blank or nonblank QA is absent")
    check(
        "color",
        visual_qa.get("color_diversity_ok") is True,
        "color diversity QA is absent or below threshold",
    )

    width, height = _dimension_pair(record)
    min_width = record.get("min_width_px")
    min_height = record.get("min_height_px")
    dimension_ok = (
        isinstance(width, int)
        and isinstance(height, int)
        and isinstance(min_width, int)
        and isinstance(min_height, int)
        and width >= min_width
        and height >= min_height
        and visual_qa.get("min_dimension_ok") is True
    )
    check("dimensions", dimension_ok, "image dimensions do not satisfy publication minima")

    render_backend = str(record.get("render_backend") or "")
    degraded = (
        _nested_flag(record, "degraded_renderer")
        or _nested_flag(record, "degraded_rasterization")
        or "degraded" in render_backend.lower()
    )
    check("degraded", not degraded, "degraded renderer metadata is present")

    publication_ok = True
    if key == "graphical_abstract":
        publication_ok = render_backend == "matplotlib_native"
        if not publication_ok:
            issues.append("graphical abstract is not native matplotlib PNG")
    if key in {
        "roundtrip_visual_diff",
        "rule_evidence_trace",
        "confidence_calibration",
        "inference_trace",
    }:
        publication_ok = render_backend == "matplotlib_native"
        if not publication_ok:
            issues.append("publication detail panel is not native matplotlib PNG")
    if key == "roundtrip_batch_gantt" and isinstance(width, int) and isinstance(height, int):
        aspect = width / height if height else 0.0
        publication_ok = height <= 1400 and aspect >= 1.6
        if not publication_ok:
            issues.append("timeline dimensions are not publication readable")
    check("publication", publication_ok, "publication-specific figure policy failed")

    return {
        "key": key,
        "destination": record.get("destination"),
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "checks": checks,
        "dimensions_px": {"width": width, "height": height},
        "render_backend": record.get("render_backend"),
        "source_artifact": source_artifact,
        "source_artifact_digest": source_digest,
        "selected_target_id": record.get("selected_target_id"),
        "displayed_counts": record.get("displayed_counts"),
    }


def build_visualization_quality_audit(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Build a publication-figure visual QA report from a manifest."""

    manifest = _read_json(manifest_path)
    figures = manifest.get("figures")
    if not isinstance(figures, list):
        raise ValueError(f"{manifest_path} does not contain a figures list")
    records = [_check_record(root, item) for item in figures if isinstance(item, dict)]
    failed = [item for item in records if item["status"] != "pass"]
    by_check: dict[str, dict[str, int]] = {}
    for check_name in CHECK_LABELS:
        passed = sum(1 for item in records if item["checks"].get(check_name) is True)
        failed_count = sum(1 for item in records if item["checks"].get(check_name) is False)
        by_check[check_name] = {"passed": passed, "failed": failed_count}
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest": str(manifest_path.relative_to(root)) if manifest_path.is_relative_to(root) else str(manifest_path),
        "summary": {
            "total_figures": len(records),
            "passed": len(records) - len(failed),
            "failed": len(failed),
            "by_check": by_check,
        },
        "figures": records,
    }


def write_json(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _issue_text(issues: Iterable[str]) -> str:
    joined = "; ".join(issues)
    return joined if joined else "none"


def write_markdown(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = report["summary"]
    lines = [
        "# Visualization Quality Audit",
        "",
        "This report summarizes registered manuscript figure sidecars after strict promotion.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total figures | {summary['total_figures']} |",
        f"| Passed | {summary['passed']} |",
        f"| Failed | {summary['failed']} |",
        "",
        "| Figure | Status | Dimensions | Source artifact | Issues |",
        "|---|---|---:|---|---|",
    ]
    for item in report["figures"]:
        dims = item["dimensions_px"]
        dim_text = f"{dims.get('width')} x {dims.get('height')}"
        lines.append(
            "| {key} | {status} | {dims} | `{source}` | {issues} |".format(
                key=item["key"],
                status=item["status"],
                dims=dim_text,
                source=item.get("source_artifact") or "",
                issues=_issue_text(item["issues"]),
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


def _write_native_png_matrix(report: dict[str, Any], path: Path) -> Path | None:
    figures = report["figures"]
    if not figures:
        return None
    check_names = list(CHECK_LABELS)
    cell_w = 86
    cell_h = 22
    label_w = 232
    top_h = 42
    margin = 12
    width = label_w + len(check_names) * cell_w + margin
    height = top_h + len(figures) * cell_h + margin
    pass_rgb = (0, 114, 178)
    fail_rgb = (213, 94, 0)
    grid_rgb = (255, 255, 255)
    bg_rgb = (246, 248, 251)
    text_rgb = (31, 41, 55)
    pixels = bytearray(bg_rgb * (width * height))

    def set_pixel(x: int, y: int, rgb: tuple[int, int, int]) -> None:
        if x < 0 or y < 0 or x >= width or y >= height:
            return
        pos = (y * width + x) * 3
        pixels[pos : pos + 3] = bytes(rgb)

    def fill_rect(x0: int, y0: int, rect_w: int, rect_h: int, rgb: tuple[int, int, int]) -> None:
        for yy in range(y0, y0 + rect_h):
            for xx in range(x0, x0 + rect_w):
                set_pixel(xx, yy, rgb)

    def draw_text(text: str, x0: int, y0: int, rgb: tuple[int, int, int]) -> None:
        x = x0
        for char in text.upper():
            glyph = _FONT_5X7.get(char, _FONT_5X7[" "])
            for gy, line in enumerate(glyph):
                for gx, bit in enumerate(line):
                    if bit == "1":
                        set_pixel(x + gx, y0 + gy, rgb)
            x += 6

    for col, name in enumerate(check_names):
        x = label_w + col * cell_w + 4
        draw_text(CHECK_LABELS[name], x, 17, text_rgb)

    for row_idx, item in enumerate(figures):
        y = top_h + row_idx * cell_h
        label = str(item["key"]).replace("_", " ")[:36]
        draw_text(label, margin, y + 7, text_rgb)
        for col, name in enumerate(check_names):
            x = label_w + col * cell_w
            ok = item["checks"].get(name) is True
            fill_rect(x + 1, y + 1, cell_w - 2, cell_h - 2, pass_rgb if ok else fail_rgb)
            draw_text("OK" if ok else "NO", x + cell_w // 2 - 6, y + 7, grid_rgb)

    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(
            b"IDAT",
            zlib.compress(
                b"".join(
                    b"\x00" + pixels[y * width * 3 : (y + 1) * width * 3]
                    for y in range(height)
                ),
                9,
            ),
        )
        + _png_chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path


def write_png_matrix(report: dict[str, Any], path: Path) -> Path | None:
    try:
        import matplotlib
    except ImportError:
        return _write_native_png_matrix(report, path)
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    figures = report["figures"]
    if not figures:
        return None
    check_names = list(CHECK_LABELS)
    matrix: list[list[int]] = []
    for item in figures:
        row = [1 if item["checks"].get(name) else 0 for name in check_names]
        matrix.append(row)

    height = max(4.8, 0.34 * len(figures) + 1.8)
    width = max(8.5, 0.88 * len(check_names) + 4.0)
    fig, ax = plt.subplots(figsize=(width, height), dpi=150)
    cmap = ListedColormap(["#D55E00", "#0072B2"])
    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(check_names)), [CHECK_LABELS[name] for name in check_names], rotation=30, ha="right")
    ax.set_yticks(range(len(figures)), [item["key"] for item in figures])
    for y, row in enumerate(matrix):
        for x, value in enumerate(row):
            ax.text(x, y, "P" if value else "F", ha="center", va="center", color="white", fontsize=8)
    ax.set_title("COGANT manuscript figure visual QA")
    ax.tick_params(axis="both", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--output-png", type=Path, default=DEFAULT_PNG)
    parser.add_argument("--no-png", action="store_true", help="Skip PNG matrix rendering.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero if any figure fails QA.")
    args = parser.parse_args()

    report = build_visualization_quality_audit(args.manifest)
    write_json(report, args.output_json)
    write_markdown(report, args.output_md)
    png_path = None if args.no_png else write_png_matrix(report, args.output_png)
    failed = report["summary"]["failed"]
    print(
        "visualization_quality_audit: "
        f"{report['summary']['passed']} passed, {failed} failed -> {args.output_json}"
    )
    if png_path is not None:
        print(f"visualization_quality_audit: matrix -> {png_path}")
    return 1 if args.strict and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
