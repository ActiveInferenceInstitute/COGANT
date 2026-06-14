"""Publication figure renderers and source-artifact preparation."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from manuscript_figure_registry import ManuscriptFigure

from figures.common import _as_float, _as_int, _int_dict, _load_json_object
from figures.constants import FIGURE_SIDECAR_SCHEMA_VERSION
from figures.png import _sha256_file


def _stage_base(step: object) -> str:
    text = str(step or "stage")
    return text.split(":", 1)[0].replace("_", " ")


def _render_publication_batch_timeline(
    root: Path,
    *,
    allow_subprocess: bool = True,
) -> Path | None:
    """Render a manuscript-grade calculator timeline from run_all's manifest."""

    manifest_path = root / "cogant" / "output" / "run_manifest.json"
    if not manifest_path.is_file():
        return None

    manifest = _load_json_object(manifest_path)
    targets = [item for item in manifest.get("targets", []) if isinstance(item, dict)]
    selected_target_id = "calculator"
    selected_target = next(
        (
            target
            for target in targets
            if str(target.get("id") or target.get("target_id") or "") == selected_target_id
        ),
        None,
    )
    if selected_target is None:
        return None

    batch_command_count = sum(
        len([item for item in target.get("commands", []) if isinstance(item, dict)])
        for target in targets
    )
    rows: list[dict[str, object]] = []
    elapsed = 0.0
    commands = [item for item in selected_target.get("commands", []) if isinstance(item, dict)]
    for order, command in enumerate(commands):
        duration = max(_as_float(command.get("wall_time_s")), 0.0)
        step = str(command.get("step") or command.get("name") or f"stage_{order + 1}")
        returncode = command.get("returncode")
        failed = returncode not in (None, 0, "0")
        rows.append(
            {
                "target_id": selected_target_id,
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
        "inspection artifacts": "#8a6d3b",
    }
    display_names = {
        "export gnn": "export GNN",
        "analyze graph": "analyze graph",
        "analyze static": "analyze static",
        "export multi": "export multi",
        "inspection artifacts": "inspection artifacts",
    }
    fig, ax = plt.subplots(figsize=(13.4, 6.0), dpi=150)
    ax.set_facecolor("#f7f8fb")
    fig.patch.set_facecolor("#f7f8fb")

    y_positions = list(range(len(rows)))
    y_labels: list[str] = []
    total_duration = max(_as_float(row["end"]) for row in rows)
    gate_stages = {"validate", "roundtrip"}
    qa_gate_markers = 0
    for idx, row in enumerate(rows):
        y = len(rows) - idx - 1
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
        y_labels.append(display_names.get(stage, stage))

    ax.set_yticks(y_positions, labels=list(reversed(y_labels)))
    ax.tick_params(axis="y", labelsize=9)
    ax.tick_params(axis="x", labelsize=9)
    ax.set_xlabel("Elapsed time within recorded run (seconds)", fontsize=10, color="#243142")
    ax.set_title(
        "Calculator run timeline from COGANT batch manifest",
        fontsize=15,
        fontweight="bold",
        color="#172033",
        pad=14,
    )
    ax.text(
        0,
        len(rows) + 0.25,
        (
            f"Selected target: {selected_target_id}; "
            f"{len(rows)} displayed commands from {len(targets)} manifest targets."
        ),
        fontsize=9.5,
        color="#526070",
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
            f"Source: cogant/output/run_manifest.json; selected_target={selected_target_id}, "
            f"displayed_commands={len(rows)}, batch_targets={len(targets)}, "
            f"batch_commands={batch_command_count}, failed_steps={failed_count}. "
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
        "generated_at": datetime.now(UTC).isoformat(),
        "key": "roundtrip_batch_gantt",
        "figure": output.name,
        "renderer": "tools.manuscript_figures.render_publication_batch_timeline",
        "source_artifact": str(manifest_path.relative_to(root)),
        "source_artifact_digest": _sha256_file(manifest_path),
        "layout_method": "calculator-focused horizontal elapsed-time timeline with batch context",
        "layout_seed": None,
        "selected_target_id": selected_target_id,
        "selected_target_command_count": len(rows),
        "batch_target_count": len(targets),
        "batch_command_count": batch_command_count,
        "publication_dimension_policy": "wide bounded-height timeline; no one-row-per-batch-command layout",
        "displayed_counts": {
            "targets_count": len(targets),
            "stages": len(rows),
            "selected_target_command_count": len(rows),
            "batch_command_count": batch_command_count,
            "qa_gate_markers": qa_gate_markers,
            "failed_steps": failed_count,
            "total_wall_time_s": round(total_duration, 3),
        },
        "panel_metadata": {
            "panel": "roundtrip_batch_gantt",
            "reading_order": "calculator command labels, elapsed timeline, duration annotations, batch-context footer",
        },
        "panels": [
            {
                "key": "roundtrip_batch_gantt",
                "displayed_counts": {
                    "targets_count": len(targets),
                    "stages": len(rows),
                    "selected_target_command_count": len(rows),
                    "batch_command_count": batch_command_count,
                    "qa_gate_markers": qa_gate_markers,
                    "failed_steps": failed_count,
                    "total_wall_time_s": round(total_duration, 3),
                },
                "reading_order": (
                    "top-to-bottom manifest command order for the calculator target; "
                    "diamond markers identify validation or roundtrip gates"
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
        "visual_buckets": dict(
            sorted(visual_buckets.items(), key=lambda item: (-item[1], item[0]))
        ),
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
        "generated_at": datetime.now(UTC).isoformat(),
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
    figures = tuple(figures)
    keys = {figure.key for figure in figures}
    if "graphical_abstract" in keys:
        run_dir = root / "cogant" / "output" / "calculator"
        if run_dir.is_dir():
            try:
                from cogant.viz.inspection_dashboard import render_graphical_abstract_png

                render_graphical_abstract_png(run_dir)
            except Exception:
                if (root / "cogant" / "pyproject.toml").is_file():
                    script = (
                        "from pathlib import Path\n"
                        "from cogant.viz.inspection_dashboard import render_graphical_abstract_png\n"
                        "raise SystemExit(0 if render_graphical_abstract_png(Path('output/calculator')) else 1)\n"
                    )
                    subprocess.run(
                        ["uv", "run", "python", "-c", script],
                        cwd=root / "cogant",
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
    if "roundtrip_batch_gantt" in keys:
        _render_publication_batch_timeline(root)
    if "batch_evidence_summary" in keys:
        _render_publication_batch_evidence_summary(root)
    if "gnn_markdown_render" in keys:
        run_dir = root / "cogant" / "output" / "calculator"
        gnn_md = run_dir / "gnn_package" / "model.gnn.md"
        output = run_dir / "figures" / "model_gnn_mosaic.png"
        if gnn_md.is_file():
            try:
                from cogant.viz.png.gnn_markdown import render_gnn_markdown_mosaic_png

                render_gnn_markdown_mosaic_png(gnn_md, output)
            except Exception:
                if (root / "cogant" / "pyproject.toml").is_file():
                    script = (
                        "from pathlib import Path\n"
                        "from cogant.viz.png.gnn_markdown import render_gnn_markdown_mosaic_png\n"
                        "raise SystemExit(0 if render_gnn_markdown_mosaic_png("
                        "Path('output/calculator/gnn_package/model.gnn.md'), "
                        "Path('output/calculator/figures/model_gnn_mosaic.png')) else 1)\n"
                    )
                    subprocess.run(
                        ["uv", "run", "python", "-c", script],
                        cwd=root / "cogant",
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
    for figure in figures:
        if figure.key != "forward_abcd_matrices":
            continue
        run_dir = root / Path(figure.source).parent
        if not run_dir.is_dir():
            continue
        rendered = False
        try:
            from cogant.viz.png.orchestrator import render_all_pngs

            result = render_all_pngs(run_dir, strict_real_matrices=True)
            if result.get("connections"):
                rendered = True
        except Exception:
            rendered = False
        if rendered or not (root / "cogant" / "pyproject.toml").is_file():
            continue
        try:
            rel_run_dir = Path(figure.source).parent.relative_to("cogant")
        except ValueError:
            continue
        script = (
            "from pathlib import Path\n"
            "from cogant.viz.png.orchestrator import render_all_pngs\n"
            f"result = render_all_pngs(Path({str(rel_run_dir)!r}), strict_real_matrices=True)\n"
            "raise SystemExit(0 if result.get('connections') else 1)\n"
        )
        subprocess.run(
            ["uv", "run", "python", "-c", script],
            cwd=root / "cogant",
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if {
        "confidence_calibration",
        "rule_evidence_trace",
        "inference_trace",
        "roundtrip_visual_diff",
    } & keys:
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
