"""Prepare rendered COGANT figures for the manuscript output tree.

The inner COGANT package writes real run artifacts under ``cogant/output``.
The template renderer expects manuscript-local assets under ``output/figures``
next to ``output/manuscript``. This module defines the curated bridge between
those two locations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


_TOOLS_DIR = Path(__file__).resolve().parent
COGANT_STAGING_ROOT = _TOOLS_DIR.parent
OUTPUT_FIGURES_DIR = COGANT_STAGING_ROOT / "output" / "figures"
FIGURE_MANIFEST_SCHEMA_VERSION = "1.2"
FIGURE_SIDECAR_SCHEMA_VERSION = "1.2"


from manuscript_figure_registry import MANUSCRIPT_FIGURES, ManuscriptFigure



def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _png_dimensions(path: Path) -> dict[str, int] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return {
        "width": int.from_bytes(data[16:20], "big"),
        "height": int.from_bytes(data[20:24], "big"),
    }


def _png_chunks(data: bytes) -> Iterable[tuple[bytes, bytes]]:
    offset = 8
    while offset + 12 <= len(data):
        length = int.from_bytes(data[offset : offset + 4], "big")
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        yield kind, payload
        offset += 12 + length
        if kind == b"IEND":
            break


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _png_visual_metrics(path: Path) -> dict[str, object] | None:
    """Return lightweight publication QA metrics for an 8-bit PNG.

    This deliberately avoids Pillow so strict manuscript checks work in the
    small template-tooling environment. Unsupported PNG encodings still report
    dimensions and mark colour-diversity fields as unavailable.
    """

    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None

    ihdr = data[16:29]
    width = int.from_bytes(ihdr[0:4], "big")
    height = int.from_bytes(ihdr[4:8], "big")
    bit_depth = ihdr[8]
    color_type = ihdr[9]
    metrics: dict[str, object] = {
        "width": width,
        "height": height,
        "min_dimension_ok": width >= 320 and height >= 180,
        "png_bit_depth": bit_depth,
        "png_color_type": color_type,
    }

    channels_by_type = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    channels = channels_by_type.get(color_type)
    if bit_depth != 8 or channels is None:
        metrics.update(
            {
                "sampled_pixels": 0,
                "estimated_unique_colors": None,
                "nonblank": None,
                "color_diversity_ok": None,
            }
        )
        return metrics

    idat = b"".join(payload for kind, payload in _png_chunks(data) if kind == b"IDAT")
    try:
        raw = zlib.decompress(idat)
    except zlib.error:
        metrics.update(
            {
                "sampled_pixels": 0,
                "estimated_unique_colors": None,
                "nonblank": None,
                "color_diversity_ok": None,
            }
        )
        return metrics

    stride = width * channels
    bpp = channels
    rows: list[bytes] = []
    pos = 0
    prior = bytes(stride)
    for _ in range(height):
        if pos >= len(raw):
            break
        filter_type = raw[pos]
        pos += 1
        row = bytearray(raw[pos : pos + stride])
        pos += stride
        for i, value in enumerate(row):
            left = row[i - bpp] if i >= bpp else 0
            up = prior[i] if i < len(prior) else 0
            up_left = prior[i - bpp] if i >= bpp and i - bpp < len(prior) else 0
            if filter_type == 1:
                row[i] = (value + left) & 0xFF
            elif filter_type == 2:
                row[i] = (value + up) & 0xFF
            elif filter_type == 3:
                row[i] = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                row[i] = (value + _paeth(left, up, up_left)) & 0xFF
        prior = bytes(row)
        rows.append(prior)

    if not rows:
        metrics.update(
            {
                "sampled_pixels": 0,
                "estimated_unique_colors": 0,
                "nonblank": False,
                "color_diversity_ok": False,
            }
        )
        return metrics

    step = max(1, int(((width * height) / 10_000) ** 0.5))
    unique: set[tuple[int, ...]] = set()
    sampled = 0
    for y in range(0, len(rows), step):
        row = rows[y]
        for x in range(0, width, step):
            start = x * channels
            unique.add(tuple(row[start : start + channels]))
            sampled += 1
    unique_count = len(unique)
    metrics.update(
        {
            "sampled_pixels": sampled,
            "estimated_unique_colors": unique_count,
            "nonblank": unique_count > 1,
            "color_diversity_ok": unique_count >= 4,
        }
    )
    return metrics


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _fixture_metrics_summary(data: dict[str, object]) -> dict[str, object] | None:
    """Summarize ``evaluation/figures/metrics.json`` style fixture metrics."""

    fixture_rows = [value for value in data.values() if isinstance(value, dict)]
    if not fixture_rows:
        return None
    if not any(
        {"nodes", "edges", "mappings_total", "state_variables", "elapsed_s"} & set(row)
        for row in fixture_rows
    ):
        return None

    node_kinds: set[str] = set()
    groups: set[str] = set()
    for row in fixture_rows:
        raw_node_kinds = row.get("nodes_by_kind")
        if isinstance(raw_node_kinds, dict):
            node_kinds.update(str(key) for key in raw_node_kinds)
        raw_group = row.get("group")
        if raw_group:
            groups.add(str(raw_group))

    return {
        "fixture_count": len(fixture_rows),
        "fixture_names": sorted(str(key) for key, value in data.items() if isinstance(value, dict)),
        "fixture_group_count": len(groups),
        "fixture_groups": sorted(groups),
        "node_kind_count": len(node_kinds),
        "node_kinds": sorted(node_kinds),
        "total_nodes": sum(_as_int(row.get("nodes")) for row in fixture_rows),
        "total_edges": sum(_as_int(row.get("edges")) for row in fixture_rows),
        "total_mappings": sum(_as_int(row.get("mappings_total")) for row in fixture_rows),
        "total_state_variables": sum(
            _as_int(row.get("state_variables")) for row in fixture_rows
        ),
        "total_observations": sum(_as_int(row.get("observations")) for row in fixture_rows),
        "total_actions": sum(_as_int(row.get("actions")) for row in fixture_rows),
        "total_transitions": sum(_as_int(row.get("transitions")) for row in fixture_rows),
        "total_elapsed_s": round(sum(_as_float(row.get("elapsed_s")) for row in fixture_rows), 3),
    }


def _stage_base(step: object) -> str:
    text = str(step or "stage")
    return text.split(":", 1)[0].replace("_", " ")


def _render_publication_batch_timeline(
    root: Path,
    *,
    allow_subprocess: bool = True,
) -> Path | None:
    """Render a light manuscript-grade timeline from run_all's manifest."""

    manifest_path = root / "cogant" / "output" / "run_manifest.json"
    if not manifest_path.is_file():
        return None

    manifest = _load_json_object(manifest_path)
    targets = [item for item in manifest.get("targets", []) if isinstance(item, dict)]
    rows: list[dict[str, object]] = []
    for target in targets:
        target_id = str(target.get("id") or target.get("target_id") or "target")
        elapsed = 0.0
        commands = [item for item in target.get("commands", []) if isinstance(item, dict)]
        for order, command in enumerate(commands):
            duration = max(_as_float(command.get("wall_time_s")), 0.0)
            step = str(command.get("step") or command.get("name") or f"stage_{order + 1}")
            returncode = command.get("returncode")
            failed = returncode not in (None, 0, "0")
            rows.append(
                {
                    "target_id": target_id,
                    "step": step,
                    "stage": _stage_base(step),
                    "start": elapsed,
                    "duration": duration,
                    "end": elapsed + duration,
                    "failed": failed,
                }
            )
            elapsed += duration
    if not rows:
        return None

    output = root / "cogant" / "output" / "dashboard" / "run_gantt.png"
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
    except Exception:
        if allow_subprocess and (root / "cogant" / "pyproject.toml").is_file():
            script = (
                "from pathlib import Path\n"
                "import sys\n"
                "sys.path.insert(0, str(Path.cwd().parent / 'tools'))\n"
                "from manuscript_figures import _render_publication_batch_timeline\n"
                "_render_publication_batch_timeline(Path.cwd().parent, allow_subprocess=False)\n"
            )
            subprocess.run(
                ["uv", "run", "python", "-c", script],
                cwd=root / "cogant",
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return output if output.is_file() else None
        return None

    palette = {
        "translate": "#2f6f9f",
        "scan": "#6b7c93",
        "graph": "#7a5cfa",
        "export gnn": "#0b7a75",
        "render": "#4f7d4f",
        "viz": "#8c4a6f",
        "validate": "#c46a2f",
        "roundtrip": "#d79b35",
        "analyze graph": "#546a7b",
        "analyze static": "#6f4e7c",
        "export multi": "#2d7f5e",
        "visualize": "#3d6f8f",
    }
    fig_height = max(5.6, 0.42 * len(rows) + 2.4)
    fig, ax = plt.subplots(figsize=(12.5, fig_height), dpi=150)
    ax.set_facecolor("#f7f8fb")
    fig.patch.set_facecolor("#f7f8fb")

    y_positions = list(range(len(rows)))
    y_labels: list[str] = []
    total_duration = max(_as_float(row["end"]) for row in rows)
    gate_stages = {"validate", "roundtrip"}
    qa_gate_markers = 0
    for idx, row in enumerate(reversed(rows)):
        y = y_positions[idx]
        stage = str(row["stage"])
        color = "#2f6f9f" if row.get("failed") else palette.get(stage, "#546a7b")
        if row.get("failed"):
            color = "#b23a48"
        start = _as_float(row["start"])
        duration = _as_float(row["duration"])
        ax.barh(
            y,
            duration,
            left=start,
            height=0.68,
            color=color,
            edgecolor="#172033" if stage in gate_stages else "white",
            linewidth=1.3 if stage in gate_stages else 1.2,
        )
        if stage in gate_stages:
            qa_gate_markers += 1
            ax.scatter(
                start + duration,
                y,
                marker="D",
                s=46,
                color="#172033",
                edgecolor="white",
                linewidth=0.9,
                zorder=4,
            )
        label = f"{duration:.2f}s"
        text_x = start + duration + max(total_duration * 0.012, 0.08)
        ax.text(text_x, y, label, va="center", ha="left", fontsize=8.5, color="#243142")
        y_labels.append(f"{row['target_id']} - {stage}")

    ax.set_yticks(y_positions, labels=y_labels)
    ax.tick_params(axis="y", labelsize=8.5)
    ax.tick_params(axis="x", labelsize=9)
    ax.set_xlabel("Elapsed time within recorded run (seconds)", fontsize=10, color="#243142")
    ax.set_title(
        "COGANT batch run timeline with explicit roundtrip stage",
        fontsize=15,
        fontweight="bold",
        color="#172033",
        pad=14,
    )
    ax.grid(axis="x", color="#d5dce6", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#9aa6b2")
    ax.set_xlim(0, max(total_duration * 1.12, 1.0))
    legend_handles = [
        Line2D([0], [0], color="#6b7c93", lw=8, label="executed stage duration"),
        Line2D(
            [0],
            [0],
            marker="D",
            color="none",
            markerfacecolor="#172033",
            markeredgecolor="white",
            markersize=7,
            label="validation or roundtrip gate",
        ),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper right",
        frameon=True,
        framealpha=0.94,
        facecolor="#ffffff",
        edgecolor="#d5dce6",
        fontsize=8.5,
    )
    failed_count = sum(1 for row in rows if row.get("failed"))
    fig.text(
        0.01,
        0.025,
        (
            f"Source: cogant/output/run_manifest.json; targets={len(targets)}, "
            f"stages={len(rows)}, gate_markers={qa_gate_markers}, failed_steps={failed_count}. "
            "Durations are audit metadata, not benchmark results."
        ),
        fontsize=8.5,
        color="#526070",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.96))
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)

    sidecar = {
        "schema_version": FIGURE_SIDECAR_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "key": "roundtrip_batch_gantt",
        "figure": output.name,
        "renderer": "tools.manuscript_figures.render_publication_batch_timeline",
        "source_artifact": str(manifest_path.relative_to(root)),
        "source_artifact_digest": _sha256_file(manifest_path),
        "layout_method": "horizontal elapsed-time timeline with fixed manifest stage order",
        "layout_seed": None,
        "displayed_counts": {
            "targets_count": len(targets),
            "stages": len(rows),
            "qa_gate_markers": qa_gate_markers,
            "failed_steps": failed_count,
            "total_wall_time_s": round(total_duration, 3),
        },
        "panel_metadata": {
            "panel": "roundtrip_batch_gantt",
            "reading_order": "target/stage labels, elapsed timeline, duration annotations, source footer",
        },
        "panels": [
            {
                "key": "roundtrip_batch_gantt",
                "displayed_counts": {
                    "targets_count": len(targets),
                    "stages": len(rows),
                    "qa_gate_markers": qa_gate_markers,
                    "failed_steps": failed_count,
                    "total_wall_time_s": round(total_duration, 3),
                },
                "reading_order": (
                    "top-to-bottom manifest stage order within each target; "
                    "dark diamonds mark validation or roundtrip gates"
                ),
            }
        ],
        "known_limitations": "Single recorded run; timing varies by machine and is not a benchmark.",
    }
    output.with_suffix(".figure.json").write_text(
        json.dumps(sidecar, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def _score_bucket(score: object) -> str:
    value = _as_float(score, -1.0)
    if value < 0:
        return "no score"
    if value >= 100:
        return "100"
    if value >= 90:
        return "90-99"
    if value >= 70:
        return "70-89"
    return "<70"


def _batch_visual_bucket(target: dict[str, object]) -> str:
    presence = target.get("presence")
    presence_map = presence if isinstance(presence, dict) else {}
    has_dashboard = bool(presence_map.get("inspection_dashboard"))
    has_abstract = bool(presence_map.get("graphical_abstract"))
    has_roundtrip = bool(presence_map.get("roundtrip_metrics"))
    if has_dashboard and has_abstract and has_roundtrip:
        return "dashboard+abstract+roundtrip"
    if has_dashboard or has_abstract or has_roundtrip:
        return "partial"
    return "missing"


def _increment_count(counts: dict[str, int], key: str, value: int = 1) -> None:
    counts[key] = counts.get(key, 0) + value


def _batch_evidence_counts(metrics_path: Path) -> dict[str, object]:
    payload = _load_json_object(metrics_path)
    targets = [row for row in payload.get("targets", []) if isinstance(row, dict)]
    role_totals: dict[str, int] = {}
    score_buckets: dict[str, int] = {}
    roundtrip_statuses: dict[str, int] = {}
    visual_buckets: dict[str, int] = {}
    total_nodes = 0
    total_edges = 0
    total_mappings = 0
    visual_artifacts = 0
    validation_score_count = 0
    complete_evidence_target_count = 0

    for target in targets:
        node_count = _as_int(target.get("node_count"))
        edge_count = _as_int(target.get("edge_count"))
        mapping_count = _as_int(target.get("mapping_count"))
        total_nodes += node_count
        total_edges += edge_count
        total_mappings += mapping_count

        roles = _int_dict(target.get("role_distribution"))
        for role, count in roles.items():
            _increment_count(role_totals, role, count)

        score = target.get("score")
        if isinstance(score, int | float) and not isinstance(score, bool):
            validation_score_count += 1
        _increment_count(score_buckets, _score_bucket(score))

        roundtrip_status = str(target.get("roundtrip_status") or "not_present")
        _increment_count(roundtrip_statuses, roundtrip_status)

        visual_count = _as_int(target.get("visual_artifact_count"))
        visual_artifacts += visual_count
        _increment_count(visual_buckets, _batch_visual_bucket(target))

        if (
            node_count > 0
            and edge_count > 0
            and mapping_count > 0
            and roles
            and isinstance(score, int | float)
            and not isinstance(score, bool)
            and bool(roundtrip_status)
            and visual_count > 0
        ):
            complete_evidence_target_count += 1

    return {
        "target_count": len(targets),
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "total_mappings": total_mappings,
        "validation_score_count": validation_score_count,
        "role_kind_count": len(role_totals),
        "role_total_count": sum(role_totals.values()),
        "roundtrip_status_kind_count": len(roundtrip_statuses),
        "visual_artifact_total_count": visual_artifacts,
        "complete_evidence_target_count": complete_evidence_target_count,
        "role_totals": dict(sorted(role_totals.items(), key=lambda item: (-item[1], item[0]))),
        "score_buckets": dict(sorted(score_buckets.items(), key=lambda item: item[0])),
        "roundtrip_statuses": dict(
            sorted(roundtrip_statuses.items(), key=lambda item: (-item[1], item[0]))
        ),
        "visual_buckets": dict(sorted(visual_buckets.items(), key=lambda item: (-item[1], item[0]))),
    }


def _draw_bar_panel(
    ax: object,
    title: str,
    counts: dict[str, int],
    *,
    color: str,
    xlabel: str,
) -> None:
    labels = list(counts) or ["none"]
    values = [counts.get(label, 0) for label in labels]
    y_positions = list(range(len(labels)))
    ax.barh(y_positions, values, color=color, edgecolor="white", linewidth=1.1)
    ax.set_yticks(y_positions, labels=labels)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, fontsize=9, color="#243142")
    ax.set_title(title, fontsize=12, fontweight="bold", color="#172033", loc="left")
    ax.grid(axis="x", color="#d5dce6", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#9aa6b2")
    max_value = max(values) if values else 0
    ax.set_xlim(0, max(max_value * 1.18, 1))
    for y, value in zip(y_positions, values, strict=True):
        ax.text(
            value + max(max_value * 0.025, 0.08),
            y,
            str(value),
            va="center",
            ha="left",
            fontsize=9,
            color="#243142",
        )


def _render_publication_batch_evidence_summary(
    root: Path,
    *,
    allow_subprocess: bool = True,
) -> Path | None:
    """Render a manuscript-grade aggregate dashboard figure from batch JSON."""

    metrics_path = root / "cogant" / "output" / "dashboard" / "metrics_per_target.json"
    if not metrics_path.is_file():
        return None
    counts = _batch_evidence_counts(metrics_path)
    output = root / "cogant" / "output" / "dashboard" / "batch_evidence_summary.png"
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        if allow_subprocess and (root / "cogant" / "pyproject.toml").is_file():
            script = (
                "from pathlib import Path\n"
                "import sys\n"
                "sys.path.insert(0, str(Path.cwd().parent / 'tools'))\n"
                "from manuscript_figures import _render_publication_batch_evidence_summary\n"
                "_render_publication_batch_evidence_summary(Path.cwd().parent, allow_subprocess=False)\n"
            )
            subprocess.run(
                ["uv", "run", "python", "-c", script],
                cwd=root / "cogant",
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return output if output.is_file() else None
        return None

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.2), dpi=150)
    fig.patch.set_facecolor("#f7f8fb")
    for ax in axes.flat:
        ax.set_facecolor("#f7f8fb")

    palette = {
        "roles": "#2f6f9f",
        "scores": "#0b7a75",
        "roundtrip": "#d79b35",
        "visuals": "#8c4a6f",
    }
    _draw_bar_panel(
        axes[0, 0],
        "Semantic roles emitted across targets",
        counts["role_totals"],  # type: ignore[arg-type]
        color=palette["roles"],
        xlabel="mapping count",
    )
    _draw_bar_panel(
        axes[0, 1],
        "Validation score buckets",
        counts["score_buckets"],  # type: ignore[arg-type]
        color=palette["scores"],
        xlabel="target count",
    )
    _draw_bar_panel(
        axes[1, 0],
        "Roundtrip status",
        counts["roundtrip_statuses"],  # type: ignore[arg-type]
        color=palette["roundtrip"],
        xlabel="target count",
    )
    _draw_bar_panel(
        axes[1, 1],
        "Visual workbench completeness",
        counts["visual_buckets"],  # type: ignore[arg-type]
        color=palette["visuals"],
        xlabel="target count",
    )

    fig.suptitle(
        "COGANT batch dashboard evidence summary",
        fontsize=16,
        fontweight="bold",
        color="#172033",
        x=0.02,
        ha="left",
    )
    fig.text(
        0.02,
        0.02,
        (
            "Source: cogant/output/dashboard/metrics_per_target.json; "
            f"targets={counts['target_count']}, nodes={counts['total_nodes']}, "
            f"edges={counts['total_edges']}, mappings={counts['total_mappings']}, "
            f"complete_evidence_targets={counts['complete_evidence_target_count']}. "
            "Counts describe emitted artifacts, not semantic correctness."
        ),
        fontsize=8.5,
        color="#526070",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.94), h_pad=2.0, w_pad=2.4)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)

    displayed_counts = {
        "target_count": counts["target_count"],
        "total_nodes": counts["total_nodes"],
        "total_edges": counts["total_edges"],
        "total_mappings": counts["total_mappings"],
        "validation_score_count": counts["validation_score_count"],
        "role_kind_count": counts["role_kind_count"],
        "role_total_count": counts["role_total_count"],
        "roundtrip_status_kind_count": counts["roundtrip_status_kind_count"],
        "visual_artifact_total_count": counts["visual_artifact_total_count"],
        "complete_evidence_target_count": counts["complete_evidence_target_count"],
    }
    sidecar = {
        "schema_version": FIGURE_SIDECAR_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "key": "batch_evidence_summary",
        "figure": output.name,
        "renderer": "tools.manuscript_figures.render_publication_batch_evidence_summary",
        "source_artifact": str(metrics_path.relative_to(root)),
        "source_artifact_digest": _sha256_file(metrics_path),
        "layout_method": "2x2 small-multiple horizontal bar summary",
        "layout_seed": None,
        "displayed_counts": displayed_counts,
        "panel_metadata": {
            "panels": [
                "semantic_roles",
                "validation_scores",
                "roundtrip_status",
                "visual_workbench_completeness",
            ],
            "reading_order": "top-left roles, top-right validation, bottom-left roundtrip, bottom-right visuals",
        },
        "panels": [
            {
                "key": "semantic_roles",
                "displayed_counts": {
                    "role_kind_count": counts["role_kind_count"],
                    "role_total_count": counts["role_total_count"],
                },
                "reading_order": "largest semantic-role bar to smallest",
            },
            {
                "key": "validation_scores",
                "displayed_counts": {"validation_score_count": counts["validation_score_count"]},
                "reading_order": "validation score buckets by label",
            },
            {
                "key": "roundtrip_status",
                "displayed_counts": {
                    "roundtrip_status_kind_count": counts["roundtrip_status_kind_count"]
                },
                "reading_order": "roundtrip status buckets by target count",
            },
            {
                "key": "visual_workbench_completeness",
                "displayed_counts": {
                    "visual_artifact_total_count": counts["visual_artifact_total_count"],
                    "complete_evidence_target_count": counts["complete_evidence_target_count"],
                },
                "reading_order": "visual completeness bucket counts",
            },
        ],
        "known_limitations": (
            "Aggregate counts describe emitted batch artifacts for this run; "
            "they do not prove semantic correctness or benchmark performance."
        ),
    }
    output.with_suffix(".figure.json").write_text(
        json.dumps(sidecar, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def _prepare_source_figures(root: Path, figures: Iterable[ManuscriptFigure]) -> None:
    keys = {figure.key for figure in figures}
    if "roundtrip_batch_gantt" in keys:
        _render_publication_batch_timeline(root)
    if "batch_evidence_summary" in keys:
        _render_publication_batch_evidence_summary(root)
    if {"confidence_calibration", "rule_evidence_trace", "inference_trace", "roundtrip_visual_diff"} & keys:
        run_dir = root / "cogant" / "output" / "calculator"
        if not run_dir.is_dir():
            return
        try:
            from cogant.viz.inspection_dashboard import render_interpretability_detail_pngs

            render_interpretability_detail_pngs(run_dir)
        except Exception:
            if not (root / "cogant" / "pyproject.toml").is_file():
                return
            script = (
                "from pathlib import Path\n"
                "from cogant.viz.inspection_dashboard import render_interpretability_detail_pngs\n"
                "render_interpretability_detail_pngs(Path('output/calculator'))\n"
            )
            subprocess.run(
                ["uv", "run", "python", "-c", script],
                cwd=root / "cogant",
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


def _artifact_summary(path: Path | None, root: Path) -> dict[str, object] | None:
    if path is None or not path.is_file():
        return None
    summary: dict[str, object] = {
        "path": str(path.relative_to(root)),
        "sha256": _sha256_file(path),
    }
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            summary["kind"] = "json"
            if isinstance(data, dict):
                summary["top_level_keys"] = sorted(data.keys())[:40]
                fixture_summary = _fixture_metrics_summary(data)
                if fixture_summary:
                    summary.update(fixture_summary)
                for key in (
                    "nodes",
                    "edges",
                    "semantic_mappings",
                    "mappings",
                    "matrices",
                    "variables",
                    "observations",
                    "actions",
                    "transitions",
                    "likelihoods",
                    "preferences",
                    "targets",
                ):
                    value = data.get(key)
                    if isinstance(value, (list, dict)):
                        summary[f"{key}_count"] = len(value)
                if isinstance(data.get("targets"), list):
                    targets = [row for row in data["targets"] if isinstance(row, dict)]
                    role_totals: dict[str, int] = {}
                    parser_statuses: set[str] = set()
                    roundtrip_statuses: set[str] = set()
                    visual_artifacts = 0
                    total_nodes = 0
                    total_edges = 0
                    total_mappings = 0
                    validation_score_count = 0
                    complete_evidence_target_count = 0
                    for target in targets:
                        node_count = _as_int(target.get("node_count"))
                        edge_count = _as_int(target.get("edge_count"))
                        mapping_count = _as_int(target.get("mapping_count"))
                        total_nodes += node_count
                        total_edges += edge_count
                        total_mappings += mapping_count
                        score = target.get("score")
                        has_score = isinstance(score, int | float) and not isinstance(score, bool)
                        if has_score:
                            validation_score_count += 1
                        target_roles = _int_dict(target.get("role_distribution"))
                        for role, count in target_roles.items():
                            role_totals[role] = role_totals.get(role, 0) + count
                        parser_statuses.add(str(target.get("parser_status") or "unknown"))
                        roundtrip_status = str(target.get("roundtrip_status") or "not_present")
                        roundtrip_statuses.add(roundtrip_status)
                        raw_visual = target.get("visual_artifact_count")
                        visual_count = 0
                        if isinstance(raw_visual, int | float) and not isinstance(raw_visual, bool):
                            visual_count = int(raw_visual)
                            visual_artifacts += visual_count
                        if (
                            node_count > 0
                            and edge_count > 0
                            and mapping_count > 0
                            and target_roles
                            and has_score
                            and bool(roundtrip_status)
                            and visual_count > 0
                        ):
                            complete_evidence_target_count += 1
                    summary["target_count"] = len(targets)
                    summary["total_nodes"] = total_nodes
                    summary["total_edges"] = total_edges
                    summary["total_mappings"] = total_mappings
                    summary["validation_score_count"] = validation_score_count
                    summary["role_kind_count"] = len(role_totals)
                    summary["role_total_count"] = sum(role_totals.values())
                    summary["parser_status_kind_count"] = len(parser_statuses)
                    summary["roundtrip_status_kind_count"] = len(roundtrip_statuses)
                    summary["visual_artifact_total_count"] = visual_artifacts
                    summary["complete_evidence_target_count"] = complete_evidence_target_count
            elif isinstance(data, list):
                summary["kind"] = "json-list"
                summary["top_level_list_count"] = len(data)
            return summary
        text = path.read_text(encoding="utf-8")
        summary.update(
            {
                "kind": "text",
                "line_count": text.count("\n") + 1,
                "byte_count": path.stat().st_size,
            }
        )
    except (OSError, UnicodeDecodeError, ValueError):
        summary["kind"] = "binary"
        summary["byte_count"] = path.stat().st_size
    return summary


def _int_dict(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, int] = {}
    for key, raw in value.items():
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int | float):
            out[str(key)] = int(raw)
    return out


def _package_version(root: Path) -> str:
    pyproject = root / "cogant" / "pyproject.toml"
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    for line in text.splitlines():
        if line.strip().startswith("version"):
            _, _, value = line.partition("=")
            return value.strip().strip('"').strip("'") or "unknown"
    return "unknown"


def _source_metadata(record: dict[str, object]) -> dict[str, object]:
    value = record.get("source_figure_metadata")
    return value if isinstance(value, dict) else {}


def _displayed_counts(record: dict[str, object]) -> dict[str, object]:
    figure_key = str(record.get("key") or "")
    source_metadata = _source_metadata(record)
    for key in ("displayed_counts", "counts"):
        value = source_metadata.get(key)
        if isinstance(value, dict) and value:
            counts = dict(value)
            summary = record.get("source_artifact_summary")
            if (
                figure_key == "rule_evidence_trace"
                and isinstance(summary, dict)
                and isinstance(summary.get("mappings_count"), int)
            ):
                counts["mappings"] = max(int(counts.get("mappings") or 0), summary["mappings_count"])
            return counts

    summary = record.get("source_artifact_summary")
    counts: dict[str, object] = {}
    if isinstance(summary, dict):
        if figure_key in {"forward_state_space_factor", "forward_abcd_matrices"}:
            for key in (
                "variables_count",
                "observations_count",
                "actions_count",
                "transitions_count",
                "likelihoods_count",
                "preferences_count",
            ):
                if key in summary:
                    counts[key] = summary[key]
            if figure_key == "forward_abcd_matrices":
                counts["matrices"] = 4
        elif figure_key == "batch_role_distribution":
            for key in (
                "target_count",
                "role_kind_count",
                "role_total_count",
                "parser_status_kind_count",
                "roundtrip_status_kind_count",
                "visual_artifact_total_count",
            ):
                if key in summary:
                    counts[key] = summary[key]
        for key, value in summary.items():
            if (
                key.endswith("_count")
                or key.startswith("total_")
                or key in {"top_level_list_count", "line_count"}
            ):
                counts[key] = value
    if counts:
        return counts

    return {"panels": 1}


def _panel_metadata(figure: ManuscriptFigure, record: dict[str, object]) -> dict[str, object]:
    source_metadata = _source_metadata(record)
    value = source_metadata.get("panel_metadata")
    if isinstance(value, dict) and value:
        return dict(value)
    return {
        "panels": [
            {
                "key": figure.key,
                "role": figure.role,
                "displayed_counts": record.get("displayed_counts") or {"panels": 1},
            }
        ]
    }


def _panels(record: dict[str, object]) -> list[dict[str, object]]:
    source_metadata = _source_metadata(record)
    value = source_metadata.get("panels")
    if isinstance(value, list) and value:
        return [dict(item) for item in value if isinstance(item, dict)]
    panel_metadata = record.get("panel_metadata")
    if isinstance(panel_metadata, dict):
        nested = panel_metadata.get("panels")
        if isinstance(nested, list) and nested:
            return [dict(item) for item in nested if isinstance(item, dict)]
        panel = panel_metadata.get("panel")
        if panel:
            return [
                {
                    "key": str(panel),
                    "displayed_counts": record.get("displayed_counts") or {"panels": 1},
                    "reading_order": panel_metadata.get("reading_order"),
                }
            ]
    return [
        {
            "key": str(record.get("key") or record.get("role") or "figure"),
            "displayed_counts": record.get("displayed_counts") or {"panels": 1},
        }
    ]


def _layout_method(record: dict[str, object]) -> str:
    source_metadata = _source_metadata(record)
    value = source_metadata.get("layout_method") or source_metadata.get("layout")
    if value:
        return str(value)
    renderer = str(record.get("renderer") or "")
    if "dashboard" in renderer or "inspection_dashboard" in renderer:
        return "dashboard evidence panel"
    if "batch_dashboard" in renderer:
        return "batch dashboard chart layout"
    if "upstream" in renderer.lower():
        return "upstream renderer layout"
    return "registered package renderer layout"


def _layout_seed(record: dict[str, object]) -> int | None:
    source_metadata = _source_metadata(record)
    value = source_metadata.get("layout_seed")
    return value if isinstance(value, int) else None


def _caption_reference_findings(caption: str) -> list[str]:
    findings: list[str] = []
    if re.search(r"@(sec|tbl|eq|fig):[A-Za-z0-9_-]+", caption):
        findings.append("caption.unresolved_crossref")
    if re.search(
        r"\b(Table|Figure)\s+\d+[A-Za-z]?(?:\.\d+)?\s*[:—-]\s*\1\s+\d+",
        caption,
        re.IGNORECASE,
    ):
        findings.append("caption.duplicate_number")
    if re.search(r"\\(?:eq)?ref\{[^}]+\}", caption):
        findings.append("caption.raw_latex_ref")
    return findings


def _publication_dimension_findings(record: dict[str, object]) -> list[str]:
    dims = record.get("dimensions_px")
    if not isinstance(dims, dict):
        return ["dimensions_px"]
    width = _as_int(dims.get("width"))
    height = _as_int(dims.get("height"))
    min_width = _as_int(record.get("min_width_px"), 1000)
    min_height = _as_int(record.get("min_height_px"), 500)
    findings: list[str] = []
    if width < min_width:
        findings.append(f"visual_qa.width_lt_{min_width}")
    if height < min_height:
        findings.append(f"visual_qa.height_lt_{min_height}")
    return findings


def _evidence_requirement_findings(record: dict[str, object]) -> list[str]:
    counts = record.get("displayed_counts")
    if not isinstance(counts, dict):
        return ["displayed_counts"]
    requirements = record.get("evidence_requirements")
    if not isinstance(requirements, (list, tuple)):
        return []
    findings: list[str] = []
    for key in requirements:
        text_key = str(key)
        if text_key not in counts:
            findings.append(f"displayed_counts.{text_key}")
            continue
        value = counts.get(text_key)
        if not text_key.startswith("reviewed_") and _as_int(value) <= 0:
            findings.append(f"displayed_counts.{text_key}_nonzero")
    if record.get("key") == "confidence_calibration":
        role = str(record.get("role") or "")
        caption = str(record.get("caption") or "").lower()
        if "calibration" in role or (
            "calibration" in caption and "not" not in caption and "review-readiness" not in caption
        ):
            findings.append("caption_role.overclaims_calibration")
        if "reviewed_mapping_rows" not in counts or "reviewed_rule_rows" not in counts:
            findings.append("displayed_counts.reviewed_rows")
    return findings


def _metadata_missing(record: dict[str, object]) -> list[str]:
    required = (
        "caption",
        "role",
        "source_artifact",
        "renderer",
        "method_note",
        "reading_guide",
        "limitations",
        "known_limitations",
        "alt_text",
        "sha256",
        "data_digest_sha256",
        "source_artifact_digest",
        "renderer_version",
        "layout_method",
        "displayed_counts",
        "panel_metadata",
        "panels",
    )
    missing = [key for key in required if not record.get(key)]
    if not record.get("source_artifact_exists"):
        missing.append("source_artifact_exists")
    dims = record.get("dimensions_px")
    if not isinstance(dims, dict) or not dims.get("width") or not dims.get("height"):
        missing.append("dimensions_px")
    qa = record.get("visual_qa")
    if not isinstance(qa, dict):
        missing.append("visual_qa")
    else:
        if qa.get("nonblank") is False:
            missing.append("visual_qa.nonblank")
        if qa.get("min_dimension_ok") is False:
            missing.append("visual_qa.min_dimension_ok")
        if qa.get("color_diversity_ok") is False:
            missing.append("visual_qa.color_diversity_ok")
    missing.extend(_publication_dimension_findings(record))
    missing.extend(_evidence_requirement_findings(record))
    missing.extend(_caption_reference_findings(str(record.get("caption") or "")))
    return missing


_MANUSCRIPT_FIGURE_RE = re.compile(r"\]\(\.\./figures/([^)#\s]+\.png)(?:#[^)]+)?\)")


def _active_manuscript_figure_refs(root: Path) -> set[str]:
    manuscript_dir = root / "manuscript"
    if not manuscript_dir.is_dir():
        return set()
    refs: set[str] = set()
    skipped = {"README.md", "SYNTAX.md", "AGENTS.md"}
    for path in sorted(manuscript_dir.glob("*.md")):
        if path.name in skipped:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        refs.update(_MANUSCRIPT_FIGURE_RE.findall(text))
    return refs


def _reference_failures(root: Path, figures: Iterable[ManuscriptFigure]) -> list[str]:
    manuscript_dir = root / "manuscript"
    if not manuscript_dir.is_dir():
        return []
    refs = _active_manuscript_figure_refs(root)
    registered = {
        Path(figure.destination).name: figure
        for figure in figures
        if figure.require_manuscript_reference
    }
    failures: list[str] = []
    inserted_unregistered = sorted(refs - set(registered))
    if inserted_unregistered:
        failures.append(
            "inserted-but-unregistered figures: " + ", ".join(inserted_unregistered)
        )
    uncited = sorted(name for name in registered if name not in refs)
    if uncited:
        failures.append("registered-but-uncited figures: " + ", ".join(uncited))
    return failures


def copy_manuscript_figures(
    staging_root: Path | None = None,
    *,
    figures: Iterable[ManuscriptFigure] = MANUSCRIPT_FIGURES,
    strict: bool = False,
) -> Path:
    """Copy curated package output figures and write a manifest.

    Missing figures are recorded in the manifest so fresh checkouts can still
    regenerate the injected manuscript before running the optional visual
    pipeline. Pass ``strict=True`` when rendering a publication artifact.
    """

    root = (staging_root or COGANT_STAGING_ROOT).resolve()
    figures = tuple(figures)
    _prepare_source_figures(root, figures)
    output_dir = root / "output" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    copied: list[dict[str, object]] = []
    missing: list[dict[str, object]] = []
    strict_failures: list[str] = []
    generated_at = datetime.now(timezone.utc).isoformat()
    renderer_version = _package_version(root)

    for figure in figures:
        src = root / figure.source
        dest = output_dir / figure.destination
        record = asdict(figure)
        record["source"] = str(src.relative_to(root))
        record["destination"] = str(dest.relative_to(root))
        if src.is_file():
            shutil.copy2(src, dest)
            record["copied"] = True
            record["bytes"] = dest.stat().st_size
            record["sha256"] = _sha256_file(dest)
            record["dimensions_px"] = _png_dimensions(dest)
            source_artifact = root / figure.source_artifact if figure.source_artifact else None
            record["source_artifact_exists"] = bool(source_artifact and source_artifact.is_file())
            source_artifact_sha256 = (
                _sha256_file(source_artifact) if source_artifact and source_artifact.is_file() else None
            )
            record["source_artifact_sha256"] = source_artifact_sha256
            record["source_artifact_digest"] = source_artifact_sha256
            record["data_digest_sha256"] = source_artifact_sha256
            record["source_artifact_summary"] = _artifact_summary(source_artifact, root)
            record["visual_qa"] = _png_visual_metrics(dest)
            source_sidecar = src.with_suffix(".figure.json")
            if source_sidecar.is_file():
                record["source_figure_sidecar"] = str(source_sidecar.relative_to(root))
                try:
                    record["source_figure_metadata"] = json.loads(
                        source_sidecar.read_text(encoding="utf-8")
                    )
                except ValueError:
                    record["source_figure_metadata"] = None
            record["renderer_version"] = renderer_version
            record["known_limitations"] = figure.limitations
            record["displayed_counts"] = _displayed_counts(record)
            record["layout_method"] = _layout_method(record)
            record["layout_seed"] = _layout_seed(record)
            record["panel_metadata"] = _panel_metadata(figure, record)
            record["panels"] = _panels(record)
            metadata_missing = _metadata_missing(record)
            record["metadata_complete"] = not metadata_missing
            record["metadata_missing"] = metadata_missing
            destination_sidecar = dest.with_suffix(".figure.json")
            record["destination_figure_sidecar"] = str(destination_sidecar.relative_to(root))
            figure_metadata = {
                "schema_version": FIGURE_SIDECAR_SCHEMA_VERSION,
                "generated_at": generated_at,
                "key": figure.key,
                "role": figure.role,
                "caption": figure.caption,
                "source": record["source"],
                "destination": record["destination"],
                "source_artifact": figure.source_artifact,
                "source_artifact_sha256": source_artifact_sha256,
                "source_artifact_digest": source_artifact_sha256,
                "data_digest_sha256": source_artifact_sha256,
                "renderer_version": renderer_version,
                "renderer": figure.renderer,
                "layout_method": record["layout_method"],
                "layout_seed": record["layout_seed"],
                "method_note": figure.method_note,
                "reading_guide": figure.reading_guide,
                "limitations": figure.limitations,
                "known_limitations": figure.limitations,
                "alt_text": figure.alt_text,
                "displayed_counts": record["displayed_counts"],
                "panel_metadata": record["panel_metadata"],
                "panels": record["panels"],
                "dimensions_px": record["dimensions_px"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
                "visual_qa": record["visual_qa"],
                "source_artifact_summary": record["source_artifact_summary"],
                "source_figure_metadata": record.get("source_figure_metadata"),
            }
            destination_sidecar.write_text(
                json.dumps(figure_metadata, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            record["destination_figure_sidecar_exists"] = destination_sidecar.is_file()
            record["figure_metadata"] = figure_metadata
            if metadata_missing:
                strict_failures.append(
                    f"{figure.key}: missing/failed {', '.join(str(item) for item in metadata_missing)}"
                )
            copied.append(record)
        else:
            record["copied"] = False
            missing.append(record)

    strict_failures.extend(_reference_failures(root, figures))
    missing_sidecars = [
        str(item.get("destination_figure_sidecar") or item.get("destination"))
        for item in copied
        if not Path(root / str(item.get("destination_figure_sidecar") or "")).is_file()
    ]
    if missing_sidecars:
        strict_failures.append("missing generated figure sidecars: " + ", ".join(missing_sidecars))

    manifest = {
        "schema_version": FIGURE_MANIFEST_SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_root": "registered COGANT run and evaluation artifacts",
        "output_dir": str(output_dir.relative_to(root)),
        "copied_count": len(copied),
        "missing_count": len(missing),
        "strict_metadata_failure_count": len(strict_failures),
        "strict_metadata_failures": strict_failures,
        "figures": copied,
        "missing": missing,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if strict and missing:
        missing_sources = ", ".join(str(item["source"]) for item in missing)
        raise FileNotFoundError(f"Missing manuscript figures: {missing_sources}")
    if strict and strict_failures:
        raise ValueError("Incomplete manuscript figure metadata: " + "; ".join(strict_failures))

    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy curated COGANT output figures into output/figures/."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any registered figure source is missing.",
    )
    args = parser.parse_args(argv)
    manifest = copy_manuscript_figures(strict=args.strict)
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
