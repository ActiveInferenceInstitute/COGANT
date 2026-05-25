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

from cogant.viz.png.discovery import (
    discover_process_model_json,
    discover_state_space_json,
    first_existing,
    load_process_model_from_json,
    load_state_space_from_json,
)
from cogant.viz.png.dot import render_all_dot_in_run
from cogant.viz.png.gnn_markdown import render_gnn_markdown_png
from cogant.viz.png.markov_blanket import render_markov_blanket_png
from cogant.viz.png.mermaid import render_all_mermaid_in_run
from cogant.viz.png.process_gantt import render_process_gantt_png
from cogant.viz.png.program_graph import render_program_graph_png
from cogant.viz.png.state_space import (
    render_connections_matrix_png,
    render_state_space_factor_png,
)
from cogant.viz.png.summary import (
    render_interpretability_overview_png,
    render_summary_cover_png,
)
from cogant.viz.png.svg import render_all_svg_in_run

def render_all_pngs(
    run_dir: Path,
    *,
    state_space: Any = None,
    process_model: Any = None,
    cfg: RenderConfig | None = None,
) -> dict[str, list[Path]]:
    """Render review artifacts for every visualization artifact under ``run_dir``.

    Single entry point the orchestrator/CLI should call to guarantee that
    every Mermaid diagram, SVG, Graphviz ``.dot``, and structural artifact
    (state space, connections matrices, process, Markov blanket, GNN
    markdown, summary cover) has a matching PNG sibling. It also writes the
    inspection-dashboard HTML and graphical-abstract SVG/PNG companions so
    a completed run has a single human-facing review surface.

    ``state_space`` and ``process_model`` may be passed explicitly; if
    omitted, the orchestrator auto-discovers ``state_space.json`` and
    ``process_model.json`` under ``run_dir`` (including common
    ``gnn_package/``, ``gnn_pipeline/``, ``statespace/``, ``process/``
    subdirectories).

    Returns a mapping of category → list of paths written. Most categories are
    PNGs; ``inspection_dashboard`` and ``graphical_abstract`` may include HTML
    or SVG companions.
    """
    run_dir = Path(run_dir)
    cfg = cfg or DEFAULT_CONFIG
    out: dict[str, list[Path]] = {
        "program_graph": [],
        "mermaid": [],
        "svg": [],
        "dot": [],
        "state_space": [],
        "connections": [],
        "process": [],
        "markov_blanket": [],
        "gnn_markdown": [],
        "summary_cover": [],
        "interpretability_overview": [],
        "graphical_abstract": [],
        "inspection_details": [],
        "inspection_dashboard": [],
    }

    # Auto-discover from on-disk JSON when not explicitly passed.
    if state_space is None:
        ss_json = discover_state_space_json(run_dir)
        if ss_json is not None:
            state_space = load_state_space_from_json(ss_json)
    else:
        ss_json = None
    if process_model is None:
        pm_json = discover_process_model_json(run_dir)
        if pm_json is not None:
            process_model = load_process_model_from_json(pm_json)

    pg_candidates = [
        run_dir / "data" / "program_graph.json",
        run_dir / "program_graph.json",
        run_dir / "gnn_package" / "program_graph.json",
        run_dir / "gnn_pipeline" / "program_graph.json",
        run_dir / "graph" / "program_graph.json",
    ]
    for pg_json in pg_candidates:
        if pg_json.is_file():
            pg_png = pg_json.with_suffix(".png")
            try:
                if render_program_graph_png(pg_json, pg_png, cfg=cfg):
                    out["program_graph"].append(pg_png)
                root_png = run_dir / "program_graph.png"
                if not root_png.exists() and render_program_graph_png(pg_json, root_png, cfg=cfg):
                    out["program_graph"].append(root_png)
            except Exception as e:  # noqa: BLE001
                logger.warning("program_graph PNG failed: %s", e)
            break

    try:
        out["mermaid"] = render_all_mermaid_in_run(run_dir, cfg=cfg)
    except Exception as e:  # noqa: BLE001
        logger.warning("render_all_mermaid_in_run failed: %s", e)

    try:
        out["svg"] = render_all_svg_in_run(run_dir)
    except Exception as e:  # noqa: BLE001
        logger.warning("render_all_svg_in_run failed: %s", e)

    try:
        out["dot"] = render_all_dot_in_run(run_dir)
    except Exception as e:  # noqa: BLE001
        logger.warning("render_all_dot_in_run failed: %s", e)

    if state_space is not None:
        try:
            png = run_dir / "state_space_factor.png"
            ss_label = str(ss_json.relative_to(run_dir)) if ss_json else "state_space"
            if render_state_space_factor_png(state_space, png, cfg=cfg, source_label=ss_label):
                out["state_space"].append(png)
        except Exception as e:  # noqa: BLE001
            logger.warning("state-space factor PNG failed: %s", e)

        try:
            cx_png = run_dir / "connections_matrix.png"
            matrix_json = first_existing(
                run_dir,
                (
                    "gnn_package/model.gnn.json",
                    "model.gnn.json",
                    "data/model.gnn.json",
                ),
            )
            if render_connections_matrix_png(
                state_space,
                cx_png,
                cfg=cfg,
                source_label=ss_label,
                matrix_source_json=matrix_json,
            ):
                out["connections"].append(cx_png)
        except Exception as e:  # noqa: BLE001
            logger.warning("connections matrix PNG failed: %s", e)

    if process_model is not None:
        try:
            png = run_dir / "process_gantt.png"
            if render_process_gantt_png(process_model, png, cfg=cfg):
                out["process"].append(png)
        except Exception as e:  # noqa: BLE001
            logger.warning("process Gantt PNG failed: %s", e)

    # Markov blanket role-colored graph — check run root + gnn package subdirs.
    mb_candidates = [
        run_dir / "markov_blanket.json",
        run_dir / "gnn_package" / "markov_blanket.json",
        run_dir / "gnn_pipeline" / "markov_blanket.json",
    ]
    for mb_json in mb_candidates:
        if mb_json.is_file():
            try:
                # Emit next to the JSON (so nested runs get nested PNGs) AND
                # at the run root for discoverability.
                mb_png = mb_json.with_suffix(".png")
                if render_markov_blanket_png(mb_json, mb_png, cfg=cfg):
                    out["markov_blanket"].append(mb_png)
                root_png = run_dir / "markov_blanket.png"
                if not root_png.exists() and render_markov_blanket_png(mb_json, root_png, cfg=cfg):
                    out["markov_blanket"].append(root_png)
            except Exception as e:  # noqa: BLE001
                logger.warning("markov blanket PNG failed for %s: %s", mb_json, e)
            break  # stop at first found

    # Full GNN markdown → PNG pages — check run root + gnn_package subdir.
    gnn_md_candidates = [
        run_dir / "model.gnn.md",
        run_dir / "gnn_package" / "model.gnn.md",
        run_dir / "gnn_pipeline" / "model.gnn.md",
    ]
    for gnn_md in gnn_md_candidates:
        if gnn_md.is_file():
            try:
                # Emit next to the source MD and at run root for discoverability.
                gnn_png = gnn_md.parent / "model_gnn.png"
                pages = render_gnn_markdown_png(gnn_md, gnn_png, cfg=cfg)
                if pages:
                    out["gnn_markdown"].extend(pages)
                root_png = run_dir / "model_gnn.png"
                if not root_png.exists():
                    root_pages = render_gnn_markdown_png(gnn_md, root_png, cfg=cfg)
                    if root_pages:
                        out["gnn_markdown"].extend(root_pages)
            except Exception as e:  # noqa: BLE001
                logger.warning("GNN markdown PNG failed: %s", e)
            break

    # Summary cover dashboard
    try:
        cover_png = run_dir / "summary_cover.png"
        if render_summary_cover_png(run_dir, cover_png, cfg=cfg):
            out["summary_cover"].append(cover_png)
    except Exception as e:  # noqa: BLE001
        logger.warning("summary cover PNG failed: %s", e)

    try:
        overview_png = run_dir / "interpretability_overview.png"
        if render_interpretability_overview_png(run_dir, overview_png, cfg=cfg):
            out["interpretability_overview"].append(overview_png)
    except Exception as e:  # noqa: BLE001
        logger.warning("interpretability overview PNG failed: %s", e)

    try:
        from cogant.viz.inspection_dashboard import write_inspection_artifacts

        inspection = write_inspection_artifacts(run_dir)
        for key in ("graphical_abstract_svg", "graphical_abstract_png"):
            path = inspection.get(key)
            if path is not None:
                out["graphical_abstract"].append(path)
        for key, path in inspection.items():
            if key.endswith("_png") and key not in {"graphical_abstract_png"}:
                out["inspection_details"].append(path)
        dashboard = inspection.get("inspection_dashboard_html")
        if dashboard is not None:
            out["inspection_dashboard"].append(dashboard)
    except Exception as e:  # noqa: BLE001
        logger.warning("inspection dashboard generation failed: %s", e)

    total = sum(len(v) for v in out.values())
    logger.info("render_all_pngs wrote %d visualization files under %s", total, run_dir)
    return out
