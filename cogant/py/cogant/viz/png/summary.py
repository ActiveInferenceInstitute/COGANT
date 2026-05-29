from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cogant.viz.png.config import (
    DEFAULT_CONFIG,
    RenderConfig,
    draw_footer,
    timestamp,
)
from cogant.viz.png.discovery import discover_state_space_json, read_json

logger = logging.getLogger(__name__)


def render_summary_cover_png(
    run_dir: Path,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
) -> bool:
    """Render a single-page cover PNG summarising key COGANT run metrics.

    Reads ``validation_report.json``, ``metrics_report.json``,
    ``program_graph.json``, and ``semantic_mappings.json`` when present and
    lays them out as a dashboard-style cover image.
    """
    cfg = cfg or DEFAULT_CONFIG
    run_dir = Path(run_dir)
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    try:
        program = read_json(run_dir / "program_graph.json") or {}
        mappings = read_json(run_dir / "semantic_mappings.json") or {}
        validation = read_json(run_dir / "validation_report.json") or {}
        metrics = read_json(run_dir / "metrics_report.json") or {}

        n_nodes = 0
        n_edges = 0
        nodes = program.get("nodes", [])
        edges = program.get("edges", [])
        n_nodes = len(nodes) if isinstance(nodes, list | dict) else 0
        n_edges = len(edges) if isinstance(edges, list | dict) else 0

        n_mappings = 0
        if isinstance(mappings, dict):
            if "mappings" in mappings and isinstance(mappings["mappings"], list | dict):
                n_mappings = len(mappings["mappings"])
            else:
                n_mappings = len(mappings)
        elif isinstance(mappings, list):
            n_mappings = len(mappings)

        score = validation.get("score") or validation.get("gnn_score")
        is_valid = validation.get("valid")
        n_checks = (
            len(validation.get("checks", [])) if isinstance(validation.get("checks"), list) else 0
        )

        run_name = run_dir.name
        generated_at = timestamp()

        fig = plt.figure(figsize=(cfg.figsize[0], 10.0))
        gs = fig.add_gridspec(4, 4, hspace=0.6, wspace=0.5)

        title_ax = fig.add_subplot(gs[0, :])
        title_ax.set_axis_off()
        title_ax.text(
            0.5,
            0.65,
            "COGANT Translation Summary",
            transform=title_ax.transAxes,
            ha="center",
            va="center",
            fontsize=cfg.title_fontsize + 6,
            fontweight="bold",
            color="#1a1a1a",
        )
        title_ax.text(
            0.5,
            0.2,
            f"Run: {run_name}   ·   Generated: {generated_at}",
            transform=title_ax.transAxes,
            ha="center",
            va="center",
            fontsize=cfg.subtitle_fontsize + 1,
            color="#555555",
        )

        kpi_specs = [
            ("Nodes", n_nodes, "#4A76D8"),
            ("Edges", n_edges, "#16a085"),
            ("Mappings", n_mappings, "#e67e22"),
            (
                "Validation",
                f"{score}" if score is not None else ("VALID" if is_valid else "N/A"),
                "#8e44ad",
            ),
        ]
        for col, (label, value, color) in enumerate(kpi_specs):
            kpi_ax = fig.add_subplot(gs[1, col])
            kpi_ax.set_axis_off()
            kpi_ax.text(
                0.5,
                0.65,
                str(value),
                transform=kpi_ax.transAxes,
                ha="center",
                va="center",
                fontsize=cfg.title_fontsize + 8,
                fontweight="bold",
                color=color,
            )
            kpi_ax.text(
                0.5,
                0.18,
                label,
                transform=kpi_ax.transAxes,
                ha="center",
                va="center",
                fontsize=cfg.banner_fontsize + 2,
                color="#444444",
            )
            kpi_ax.set_facecolor("#f7f8fb")

        info_ax = fig.add_subplot(gs[2:, :])
        info_ax.set_axis_off()
        lines = [
            f"Program graph: {n_nodes} nodes · {n_edges} edges",
            f"Semantic mappings: {n_mappings}",
            f"Validation checks: {n_checks}  ·  valid={is_valid}  ·  score={score}",
        ]
        coverage = metrics.get("provenance_coverage") if isinstance(metrics, dict) else None
        if coverage is not None:
            lines.append(f"Provenance coverage: {coverage}")
        confidence = metrics.get("confidence_mean") if isinstance(metrics, dict) else None
        if confidence is not None:
            lines.append(f"Mean mapping confidence: {confidence}")
        if isinstance(metrics, dict) and metrics.get("markov_blanket"):
            lines.append(f"Markov blanket: {metrics['markov_blanket']}")

        info_ax.text(
            0.02,
            0.95,
            "Run metrics",
            transform=info_ax.transAxes,
            ha="left",
            va="top",
            fontsize=cfg.subtitle_fontsize + 2,
            fontweight="bold",
            color="#222222",
        )
        for i, line in enumerate(lines):
            info_ax.text(
                0.02,
                0.85 - i * 0.13,
                f"• {line}",
                transform=info_ax.transAxes,
                ha="left",
                va="top",
                fontsize=cfg.node_fontsize,
                color="#333333",
            )

        draw_footer(fig, source=run_name, cfg=cfg)
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Summary cover PNG failed: %s", e)
        return False


def _collection_len(value: Any) -> int:
    """Return a stable count for dict/list-like JSON collections."""
    if isinstance(value, dict | list | tuple | set):
        return len(value)
    return 0


def _node_kind_counts(program: dict[str, Any]) -> dict[str, int]:
    nodes = program.get("nodes") or {}
    if isinstance(nodes, dict):
        iterable = list(nodes.values())
    elif isinstance(nodes, list | tuple):
        iterable = list(nodes)
    else:
        iterable = []
    counts: dict[str, int] = {}
    for node in iterable:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or node.get("type") or "unknown")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _mapping_kind_counts(mappings: Any) -> dict[str, int]:
    if isinstance(mappings, dict):
        summary = mappings.get("summary")
        if isinstance(summary, dict) and isinstance(summary.get("mapping_kinds"), dict):
            return {str(k): int(v) for k, v in summary["mapping_kinds"].items()}
    if isinstance(mappings, dict) and "mappings" in mappings:
        mappings = mappings["mappings"]
    if isinstance(mappings, dict):
        iterable = list(mappings.values())
    elif isinstance(mappings, list | tuple):
        iterable = list(mappings)
    else:
        iterable = []
    counts: dict[str, int] = {}
    for mapping in iterable:
        if not isinstance(mapping, dict):
            continue
        kind = str(mapping.get("kind") or mapping.get("mapping_kind") or "unknown")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _blanket_role_counts(blanket: dict[str, Any]) -> dict[str, int]:
    roles = blanket.get("roles") or {}
    counts: dict[str, int] = {}
    if isinstance(roles, dict):
        if roles and all(isinstance(v, list) for v in roles.values()):
            for role, members in roles.items():
                counts[str(role)] = len(members)
        else:
            for role in roles.values():
                role_name = str(role)
                counts[role_name] = counts.get(role_name, 0) + 1
    for role in ("internal", "sensory", "active", "external"):
        ids = blanket.get(f"{role}_ids")
        if isinstance(ids, list):
            counts[role] = len(ids)
    return counts


def render_interpretability_overview_png(
    run_dir: Path,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
) -> bool:
    """Render a human-oriented overview of code → GNN interpretability artifacts.

    The page distills four interfaces that users inspect during a COGANT run:
    program graph structure, semantic role mappings, state-space/GNN shape, and
    Markov-blanket partitioning. Missing artifacts are shown as zero-count
    sections rather than failing the render.
    """
    cfg = cfg or DEFAULT_CONFIG
    run_dir = Path(run_dir)
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    try:
        program = (
            read_json(run_dir / "program_graph.json")
            or read_json(run_dir / "gnn_package" / "program_graph.json")
            or {}
        )
        model_gnn_json = (
            read_json(run_dir / "model.gnn.json")
            or read_json(run_dir / "gnn_package" / "model.gnn.json")
            or {}
        )
        mappings = (
            read_json(run_dir / "semantic_mappings.json")
            or read_json(run_dir / "gnn_package" / "semantic_mappings.json")
            or (model_gnn_json.get("mappings") if isinstance(model_gnn_json, dict) else {})
            or {}
        )
        ss_path = discover_state_space_json(run_dir)
        state_space_raw = read_json(ss_path) if ss_path else {}
        state_space: dict[str, Any] = state_space_raw if isinstance(state_space_raw, dict) else {}
        blanket = (
            read_json(run_dir / "markov_blanket.json")
            or read_json(run_dir / "gnn_package" / "markov_blanket.json")
            or {}
        )

        nodes = program.get("nodes") or {}
        edges = program.get("edges") or {}
        kind_counts = _node_kind_counts(program)
        mapping_counts = _mapping_kind_counts(mappings)
        role_counts = _blanket_role_counts(blanket)

        ss_counts = {
            "variables": _collection_len(
                state_space.get("variables") or state_space.get("state_variables")
            ),
            "observations": _collection_len(
                state_space.get("observations") or state_space.get("observation_modalities")
            ),
            "actions": _collection_len(state_space.get("actions")),
            "transitions": _collection_len(state_space.get("transitions")),
        }

        panels = [
            (
                "Program Graph",
                {
                    "nodes": _collection_len(nodes),
                    "edges": _collection_len(edges),
                    **dict(sorted(kind_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:4]),
                },
                "#4A76D8",
            ),
            (
                "Semantic Roles",
                dict(sorted(mapping_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:6]),
                "#e67e22",
            ),
            ("Generative Model", ss_counts, "#16a085"),
            (
                "Markov Blanket",
                dict(sorted(role_counts.items(), key=lambda kv: kv[0])),
                "#8e44ad",
            ),
        ]

        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(3, 4, height_ratios=[0.55, 2.6, 1.4], hspace=0.55, wspace=0.45)

        title_ax = fig.add_subplot(gs[0, :])
        title_ax.set_axis_off()
        title_ax.text(
            0.5,
            0.68,
            "COGANT Interpretability Overview",
            ha="center",
            va="center",
            fontsize=cfg.title_fontsize + 5,
            fontweight="bold",
            color="#1a1a1a",
        )
        title_ax.text(
            0.5,
            0.22,
            f"Run: {run_dir.name} · code graph, semantic roles, GNN state space, and blanket partition",
            ha="center",
            va="center",
            fontsize=cfg.subtitle_fontsize,
            color="#555555",
        )

        for idx, (title, data, color) in enumerate(panels):
            ax = fig.add_subplot(gs[1, idx])
            ax.set_title(title, fontsize=cfg.subtitle_fontsize + 2, fontweight="bold")
            if data:
                labels = list(data.keys())
                values = [float(v) for v in data.values()]
                ax.barh(labels, values, color=color, alpha=0.82)
                ax.invert_yaxis()
                ax.grid(axis="x", alpha=0.25)
                for y, value in enumerate(values):
                    ax.text(value, y, f" {int(value)}", va="center", fontsize=cfg.edge_fontsize)
            else:
                ax.text(0.5, 0.5, "artifact not present", ha="center", va="center", color="#777777")
                ax.set_axis_off()

        route_ax = fig.add_subplot(gs[2, :])
        route_ax.set_axis_off()
        route = [
            "Read left to right: code entities become typed graph nodes, rules assign semantic roles, "
            "state-space compilation creates the GNN variables/observations/actions, and the blanket "
            "view exposes the internal/sensory/active/external interface.",
            "This overview is intentionally compact; detailed PNGs such as program_graph.png, "
            "connections_matrix.png, markov_blanket.png, model_gnn.png, and dashboard.md remain the "
            "drill-down views for inspection.",
        ]
        route_ax.text(
            0.02,
            0.82,
            "\n".join(route),
            ha="left",
            va="top",
            fontsize=cfg.node_fontsize,
            color="#222222",
            bbox={"boxstyle": "round,pad=0.6", "facecolor": "#f7f8fb", "edgecolor": "#dfe2e8"},
        )

        draw_footer(fig, source=run_dir.name, cfg=cfg)
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Interpretability overview PNG failed: %s", e)
        return False
