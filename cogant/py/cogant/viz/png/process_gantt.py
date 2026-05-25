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
def render_process_gantt_png(
    process_model: Any,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: int | None = None,
    source_label: str | None = None,
) -> bool:
    """Render a ProcessModel as a rich Gantt timeline PNG.

    Includes stage names, predecessor/successor edges, duration bars colored
    by stage type, banner with stage/policy counts, and legend.
    """
    cfg = cfg or DEFAULT_CONFIG
    figsize = figsize or cfg.figsize
    dpi = dpi or cfg.dpi

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    if process_model is None:
        return False

    try:
        stages = getattr(process_model, "stages", None)
        if stages is None:
            return False
        if isinstance(stages, dict):
            stage_list = list(stages.values())
        else:
            stage_list = list(stages)
        if not stage_list:
            return False

        # Cap at a legible number of rows. Beyond ~80 bars the Gantt becomes
        # an illegible stripe pattern, and for very large process models the
        # figure height (0.55 * N + 3.5 inches) exceeds matplotlib's usable
        # canvas. Keep the first ``gantt_cap`` stages in insertion order so
        # sequencing stays meaningful.
        gantt_cap = max(10, min(cfg.max_render_nodes // 5, 80))
        original_stage_n = len(stage_list)
        stage_list = stage_list[:gantt_cap]

        names, starts, durations, types = [], [], [], []
        for i, st in enumerate(stage_list):
            name = getattr(st, "name", None) or getattr(st, "id", f"stage_{i}")
            stype = getattr(st, "type", None) or getattr(st, "kind", None) or "stage"
            names.append(truncate(str(name), 36))
            starts.append(getattr(st, "start", None) or i)
            durations.append(getattr(st, "duration", None) or 1)
            types.append(str(stype))

        type_colors_palette = [
            "#4A76D8",
            "#16a085",
            "#f39c12",
            "#9b59b6",
            "#e74c3c",
            "#1abc9c",
            "#e67e22",
        ]
        unique_types = list(dict.fromkeys(types))
        type_colors = {
            t: type_colors_palette[i % len(type_colors_palette)] for i, t in enumerate(unique_types)
        }

        # Clamp the figure height so matplotlib never blows past its canvas
        # limit (roughly 200 inches at default dpi). 0.55 in/bar * 80 bars
        # + 3.5 in banner = ~47.5 in which is already large but renderable.
        height = max(cfg.figsize[1], min(0.55 * len(stage_list) + 3.5, 50.0))
        fig, ax = plt.subplots(figsize=(figsize[0], height))
        for i, (start, dur, t) in enumerate(zip(starts, durations, types, strict=False)):
            ax.barh(
                i,
                max(dur, 1),
                left=start,
                height=0.6,
                color=type_colors[t],
                edgecolor="#222222",
                linewidth=0.9,
            )
            ax.text(
                start + max(dur, 1) / 2,
                i,
                names[i],
                ha="center",
                va="center",
                fontsize=cfg.edge_fontsize + 1,
                color="white",
                fontweight="bold",
            )

        ax.set_yticks(range(len(stage_list)))
        ax.set_yticklabels(names, fontsize=cfg.edge_fontsize + 1)
        ax.invert_yaxis()
        ax.set_xlabel("Step / time", fontsize=cfg.banner_fontsize + 1)
        ax.grid(axis="x", color="#dddddd", linestyle="--", linewidth=0.6, alpha=0.7)

        policies = getattr(process_model, "policies", None) or []
        n_policies = len(policies) if hasattr(policies, "__len__") else 0

        stage_stat = (
            f"{len(stage_list)}"
            if len(stage_list) == original_stage_n
            else f"{len(stage_list)}/{original_stage_n}"
        )
        draw_metadata_banner(
            ax,
            title="Process Timeline",
            subtitle=source_label,
            stats={
                "stages": stage_stat,
                "types": len(unique_types),
                "policies": n_policies,
            },
            cfg=cfg,
        )
        draw_color_legend(ax, type_colors, title="Stage types", cfg=cfg)
        draw_footer(fig, source=source_label or "process_model", cfg=cfg)

        plt.tight_layout(rect=(0, 0.02, 1, 0.95))
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Process Gantt PNG failed: %s", e)
        return False


