from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from cogant.viz.png.config import (
    DEFAULT_CONFIG,
    RenderConfig,
    draw_color_legend,
    draw_footer,
    draw_metadata_banner,
    downsample_graph,
    sha256_file,
    truncate,
    timestamp,
    write_figure_sidecar,
)

logger = logging.getLogger(__name__)
_BLANKET_ROLE_COLOR = {
    "internal": "#8e44ad",
    "sensory": "#27ae60",
    "active": "#e67e22",
    "external": "#95a5a6",
    "boundary": "#c0392b",
}


def render_markov_blanket_png(
    blanket_json: Path,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
    source_label: str | None = None,
) -> bool:
    """Render a Markov blanket artifact (``markov_blanket.json``) as a role-colored PNG.

    Expected schema: ``{"roles": {"nid": "internal|sensory|active|external", ...},
    "edges": [[src, tgt], ...], "seeds": [...], "stats": {...}}`` — tolerant
    of alternative field names (``node_roles``, ``links``).
    """
    cfg = cfg or DEFAULT_CONFIG
    if not blanket_json.is_file():
        return False
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        return False

    try:
        data = json.loads(blanket_json.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.warning("Could not read %s: %s", blanket_json, e)
        return False

    try:
        raw_roles = data.get("roles") or data.get("node_roles") or {}
        # Normalize roles into {node_id: (role_name, display_label)}.
        id_to_role: dict[str, tuple[str, str]] = {}

        if isinstance(raw_roles, dict):
            # Two valid shapes:
            #   A) {"node_id": "role_name"}        (flat mapping)
            #   B) {"role_name": [{"id": ..., "name": ...}, ...]}  (grouped)
            if raw_roles and all(isinstance(v, list) for v in raw_roles.values()):
                for role_name, members in raw_roles.items():
                    for m in members or []:
                        if isinstance(m, dict):
                            nid = m.get("id") or m.get("node") or m.get("symbol_id")
                            label = m.get("name") or nid
                        elif isinstance(m, str):
                            nid, label = m, m
                        else:
                            continue
                        if nid:
                            id_to_role[str(nid)] = (
                                str(role_name).lower(),
                                str(label or nid),
                            )
            else:
                for nid, role_name in raw_roles.items():
                    id_to_role[str(nid)] = (str(role_name).lower(), str(nid))

        if not id_to_role:
            # Synthesize from partition lists (internal_ids/sensory_ids/...).
            for role in ("internal", "sensory", "active", "external"):
                for nid in data.get(f"{role}_ids", []) or []:
                    id_to_role[str(nid)] = (role, str(nid))

        edges_in = data.get("edges") or data.get("links") or data.get("connections") or []

        # Downsample very large blankets before building the graph. We keep
        # every internal/sensory/active node (they're usually few) plus a
        # capped external subset ranked by edge connectivity.
        original_total = len(id_to_role)
        if original_total > cfg.max_render_nodes:
            incidence: dict[str, int] = dict.fromkeys(id_to_role, 0)
            for edge_spec in edges_in:
                if isinstance(edge_spec, list | tuple) and len(edge_spec) >= 2:
                    s, t = str(edge_spec[0]), str(edge_spec[1])
                elif isinstance(edge_spec, dict):
                    s, t = str(edge_spec.get("source") or ""), str(edge_spec.get("target") or "")
                else:
                    continue
                if s in incidence:
                    incidence[s] += 1
                if t in incidence:
                    incidence[t] += 1
            non_external = {nid for nid, (role, _) in id_to_role.items() if role != "external"}
            budget = max(cfg.max_render_nodes - len(non_external), 40)
            externals = sorted(
                (
                    (nid, incidence.get(nid, 0))
                    for nid, (role, _) in id_to_role.items()
                    if role == "external"
                ),
                key=lambda kv: (-kv[1], kv[0]),
            )[:budget]
            keep = non_external | {nid for nid, _ in externals}
            id_to_role = {k: v for k, v in id_to_role.items() if k in keep}

        g = nx.DiGraph()
        for nid, (role, label) in id_to_role.items():
            g.add_node(
                nid,
                role=role,
                label=truncate(label, cfg.max_label_len),
            )
        for edge_spec in edges_in:
            if isinstance(edge_spec, list | tuple) and len(edge_spec) >= 2:
                s_any, t_any = edge_spec[0], edge_spec[1]
            elif isinstance(edge_spec, dict):
                s_any, t_any = edge_spec.get("source"), edge_spec.get("target")
            else:
                continue
            if s_any and t_any and s_any in id_to_role and t_any in id_to_role:
                g.add_edge(s_any, t_any)

        if g.number_of_nodes() == 0:
            return False

        counts = {
            role: sum(1 for _, d in g.nodes(data=True) if d.get("role") == role)
            for role in _BLANKET_ROLE_COLOR
        }
        stats: dict[str, Any] = {k: v for k, v in counts.items() if v}
        stats["edges"] = g.number_of_edges()
        if g.number_of_nodes() < original_total:
            stats["sampled"] = f"{g.number_of_nodes()}/{original_total} nodes"

        if g.number_of_edges() == 0:
            sparse_figsize = (cfg.figsize[0], max(8.0, cfg.figsize[1] * 0.72))
            fig, ax = plt.subplots(figsize=sparse_figsize)
            ax.set_axis_off()
            ax.set_xlim(0.0, 1.0)
            ax.set_ylim(0.0, 1.0)

            role_order = ("internal", "sensory", "active", "external")
            top = 0.82
            row_gap = 0.17
            label_x = 0.06
            cell_left = 0.27
            cell_right = 0.95
            max_cols = 5

            for row_idx, role in enumerate(role_order):
                y_center = top - row_idx * row_gap
                color = _BLANKET_ROLE_COLOR[role]
                members = sorted(
                    (
                        str(node_data.get("label") or node_id)
                        for node_id, node_data in g.nodes(data=True)
                        if node_data.get("role") == role
                    ),
                    key=str.lower,
                )
                ax.text(
                    label_x,
                    y_center,
                    f"{role} ({len(members)})",
                    ha="left",
                    va="center",
                    fontsize=cfg.subtitle_fontsize,
                    fontweight="bold",
                    color="#222222",
                    transform=ax.transAxes,
                )
                ax.plot(
                    [0.18, 0.97],
                    [y_center - 0.055, y_center - 0.055],
                    color="#d7dce2",
                    linewidth=1.0,
                    transform=ax.transAxes,
                    clip_on=False,
                )
                if not members:
                    ax.text(
                        cell_left,
                        y_center,
                        "none",
                        ha="left",
                        va="center",
                        fontsize=cfg.banner_fontsize,
                        color="#737373",
                        style="italic",
                        transform=ax.transAxes,
                    )
                    continue

                cols = min(max_cols, max(1, len(members)))
                rows = (len(members) + cols - 1) // cols
                for idx, label in enumerate(members):
                    col = idx % cols
                    member_row = idx // cols
                    x = (
                        cell_left
                        if cols == 1
                        else cell_left + (cell_right - cell_left) * col / (cols - 1)
                    )
                    y = y_center + (rows - 1) * 0.034 - member_row * 0.068
                    text_color = "#111111" if role == "external" else "#ffffff"
                    ax.text(
                        x,
                        y,
                        truncate(label, 18),
                        ha="center",
                        va="center",
                        fontsize=cfg.banner_fontsize,
                        fontweight="bold",
                        color=text_color,
                        transform=ax.transAxes,
                        bbox={
                            "boxstyle": "round,pad=0.34",
                            "facecolor": color,
                            "edgecolor": "#222222",
                            "linewidth": 1.0,
                            "alpha": 0.96,
                        },
                    )

            present_legend = {
                f"{role} ({counts[role]})": color
                for role, color in _BLANKET_ROLE_COLOR.items()
                if counts.get(role)
            }
            draw_metadata_banner(
                ax,
                title="Structural Markov-Blanket Partition",
                subtitle=None,
                stats=stats,
                cfg=cfg,
            )
            draw_color_legend(ax, present_legend, title="Roles", cfg=cfg)
            draw_footer(fig, source=blanket_json.name, cfg=cfg)

            output_png.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            write_figure_sidecar(
                output_png,
                {
                    "source_artifact": str(blanket_json),
                    "source_artifact_sha256": sha256_file(blanket_json),
                    "source_artifact_digest": sha256_file(blanket_json),
                    "renderer": "cogant.viz.png_export.render_markov_blanket_png",
                    "layout_method": "deterministic sparse role partition lanes",
                    "displayed_counts": {
                        **counts,
                        "edges": g.number_of_edges(),
                        "nodes": g.number_of_nodes(),
                    },
                    "known_limitations": (
                        "Sparse role-partition view only; it displays structural "
                        "node roles and does not assert probabilistic conditional "
                        "independence."
                    ),
                    "panel_metadata": {
                        "panels": [
                            {
                                "key": "markov_blanket",
                                "role": "structural-markov-blanket-partition",
                                "displayed_counts": {
                                    **counts,
                                    "edges": g.number_of_edges(),
                                    "nodes": g.number_of_nodes(),
                                },
                            }
                        ]
                    },
                },
                cfg,
            )
            return True

        n = g.number_of_nodes()
        network_layout_method = "kamada-kawai role graph" if n <= 80 else "seeded spring role graph"
        try:
            if n <= 80:
                pos = nx.kamada_kawai_layout(g)
            else:
                pos = nx.spring_layout(g, seed=23, k=2.2 / n**0.5, iterations=60)
        except Exception:
            network_layout_method = "seeded spring role graph fallback"
            pos = nx.spring_layout(g, seed=23, k=2.0 / n**0.5, iterations=40)

        fig, ax = plt.subplots(figsize=cfg.figsize)
        for role, color in _BLANKET_ROLE_COLOR.items():
            ids = [n_ for n_, d in g.nodes(data=True) if d.get("role") == role]
            if ids:
                nx.draw_networkx_nodes(
                    g,
                    pos,
                    nodelist=ids,
                    node_color=color,
                    node_size=cfg.node_size,
                    alpha=0.95,
                    edgecolors="#222222",
                    linewidths=1.4,
                    ax=ax,
                )
        nx.draw_networkx_edges(
            g,
            pos,
            edge_color="#2c3e50",
            arrows=True,
            arrowsize=16,
            width=1.2,
            alpha=0.7,
            connectionstyle="arc3,rad=0.08",
            ax=ax,
        )
        nx.draw_networkx_labels(
            g,
            pos,
            labels={n_: g.nodes[n_].get("label", n_) for n_ in g.nodes()},
            font_size=cfg.node_fontsize,
            font_color="white",
            font_weight="bold",
            ax=ax,
        )

        present_legend = {
            f"{role} ({counts[role]})": color
            for role, color in _BLANKET_ROLE_COLOR.items()
            if counts.get(role)
        }

        ax.set_axis_off()
        draw_metadata_banner(
            ax,
            title="Structural Markov-Blanket Partition",
            subtitle=None,
            stats=stats,
            cfg=cfg,
        )
        draw_color_legend(ax, present_legend, title="Roles", cfg=cfg)
        draw_footer(fig, source=blanket_json.name, cfg=cfg)

        plt.tight_layout(rect=(0, 0.02, 1, 0.97))
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        write_figure_sidecar(
            output_png,
            {
                "source_artifact": str(blanket_json),
                "source_artifact_sha256": sha256_file(blanket_json),
                "source_artifact_digest": sha256_file(blanket_json),
                "renderer": "cogant.viz.png_export.render_markov_blanket_png",
                "layout_method": network_layout_method,
                "layout_seed": 23 if n > 80 else None,
                "displayed_counts": {
                    **counts,
                    "edges": g.number_of_edges(),
                    "nodes": g.number_of_nodes(),
                },
                "known_limitations": (
                    "Structural role graph only; it displays extracted program-node "
                    "roles and does not assert probabilistic conditional independence."
                ),
                "panel_metadata": {
                    "panels": [
                        {
                            "key": "markov_blanket",
                            "role": "structural-markov-blanket-partition",
                            "displayed_counts": {
                                **counts,
                                "edges": g.number_of_edges(),
                                "nodes": g.number_of_nodes(),
                            },
                        }
                    ]
                },
            },
            cfg,
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Markov blanket PNG failed: %s", e)
        return False


