from __future__ import annotations

import logging
import math
from pathlib import Path

from cogant.viz.png.config import (
    DEFAULT_CONFIG,
    RenderConfig,
    draw_footer,
    sha256_file,
    write_figure_sidecar,
)

logger = logging.getLogger(__name__)


def _split_gnn_markdown(text: str) -> list[tuple[str, str]]:
    """Split a GNN markdown file into (section_title, body) pairs.

    Section breaks occur on lines starting with ``## ``. The preamble (if any)
    is returned as an initial ``("Preamble", body)`` pair when present.
    """
    sections: list[tuple[str, str]] = []
    current_title = "Preamble"
    current_body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current_body:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = line[3:].strip() or "Section"
            current_body = []
        else:
            current_body.append(line)
    if current_body:
        sections.append((current_title, "\n".join(current_body).strip()))
    return [(t, b) for t, b in sections if b or t != "Preamble"]


def render_gnn_markdown_png(
    md_file: Path,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
    max_sections_per_page: int = 4,
    source_label: str | None = None,
) -> list[Path]:
    """Render a GNN markdown file as one or more PNG "pages".

    The file is split by ``## Section`` headers and laid out across multiple
    pages of up to ``max_sections_per_page`` sections each. Section bodies are
    wrapped and truncated to fit. Returns the list of PNGs produced; the first
    entry matches ``output_png``, subsequent entries are suffixed ``_p2``, etc.

    This is the canonical "render the entire GNN file" entry point.
    """
    cfg = cfg or DEFAULT_CONFIG
    if not md_file.is_file():
        return []
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    try:
        text = md_file.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.warning("Could not read %s: %s", md_file, e)
        return []

    sections = _split_gnn_markdown(text)
    if not sections:
        return []

    pages: list[Path] = []
    total = len(sections)
    n_pages = max(1, (total + max_sections_per_page - 1) // max_sections_per_page)

    for page_idx in range(n_pages):
        chunk = sections[page_idx * max_sections_per_page : (page_idx + 1) * max_sections_per_page]
        if page_idx == 0:
            out = output_png
        else:
            out = output_png.with_name(f"{output_png.stem}_p{page_idx + 1}.png")

        height = max(cfg.figsize[1], 3.0 + 2.6 * len(chunk))
        fig, ax = plt.subplots(figsize=(cfg.figsize[0], height))
        ax.set_axis_off()

        ax.text(
            0.5,
            0.98,
            f"{md_file.name} — page {page_idx + 1}/{n_pages}",
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=cfg.title_fontsize,
            fontweight="bold",
            color="#1a1a1a",
        )
        if source_label:
            ax.text(
                0.5,
                0.955,
                source_label,
                transform=ax.transAxes,
                ha="center",
                va="top",
                fontsize=cfg.subtitle_fontsize,
                color="#555555",
            )

        y = 0.90
        for title, body in chunk:
            ax.text(
                0.02,
                y,
                f"## {title}",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=cfg.subtitle_fontsize + 2,
                fontweight="bold",
                color="#1f3a75",
            )
            y -= 0.03
            max_lines = 18
            body_lines = body.splitlines()
            if len(body_lines) > max_lines:
                body_lines = body_lines[:max_lines] + [
                    f"… ({len(body.splitlines()) - max_lines} more lines)"
                ]
            wrapped = []
            for raw in body_lines:
                if len(raw) > 110:
                    wrapped.append(raw[:107] + "…")
                else:
                    wrapped.append(raw)
            body_text = "\n".join(wrapped)
            ax.text(
                0.03,
                y,
                body_text or "(empty)",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=cfg.edge_fontsize + 1,
                family="monospace",
                color="#222222",
                bbox={
                    "boxstyle": "round,pad=0.5",
                    "facecolor": "#f7f8fb",
                    "edgecolor": "#dfe2e8",
                },
            )
            y -= 0.04 + 0.028 * min(len(body_lines), max_lines)
            y = max(y, 0.05)
            if y < 0.08:
                break

        draw_footer(fig, source=md_file.name, cfg=cfg)
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        if out.is_file():
            pages.append(out)

    return pages


def _default_mosaic_grid(page_count: int) -> tuple[int, int]:
    if page_count <= 0:
        return 0, 0
    columns = min(4, max(1, math.ceil(math.sqrt(page_count * 2))))
    rows = math.ceil(page_count / columns)
    return rows, columns


def render_gnn_markdown_mosaic_png(
    md_file: Path,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
    page_pngs: list[Path] | None = None,
    max_sections_per_page: int = 4,
    source_label: str | None = None,
) -> Path | None:
    """Render every GNN markdown page as a single publication mosaic PNG.

    This helper preserves :func:`render_gnn_markdown_png` as the page renderer
    for dashboard/inspection workflows, then composes those page images into a
    bounded small-multiple publication figure.
    """
    cfg = cfg or DEFAULT_CONFIG
    if not md_file.is_file():
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.image as mpimg
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    try:
        text = md_file.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.warning("Could not read %s for GNN mosaic: %s", md_file, e)
        return None

    sections = _split_gnn_markdown(text)
    if not sections:
        return None

    pages = list(page_pngs or [])
    if not pages:
        page_out = output_png.with_name("model_gnn.png")
        pages = render_gnn_markdown_png(
            md_file,
            page_out,
            cfg=cfg,
            max_sections_per_page=max_sections_per_page,
            source_label=source_label,
        )
    pages = [page for page in pages if page.is_file()]
    if not pages:
        return None

    rows, columns = _default_mosaic_grid(len(pages))
    fig_width = max(cfg.figsize[0], columns * 4.6)
    fig_height = max(8.8, rows * 3.8 + 1.6)
    fig, axes = plt.subplots(rows, columns, figsize=(fig_width, fig_height))
    axes_list = list(axes.flat) if hasattr(axes, "flat") else [axes]

    for idx, ax in enumerate(axes_list):
        ax.set_axis_off()
        if idx >= len(pages):
            continue
        image = mpimg.imread(pages[idx])
        ax.imshow(image)
        ax.set_title(
            f"Page {idx + 1}",
            fontsize=max(cfg.subtitle_fontsize - 1, 8),
            fontweight="bold",
            color="#1a1a1a",
            pad=5,
        )

    fig.suptitle(
        f"{md_file.name} — all rendered pages",
        fontsize=cfg.title_fontsize,
        fontweight="bold",
        color="#1a1a1a",
        y=0.985,
    )
    if source_label:
        fig.text(
            0.5,
            0.952,
            source_label,
            ha="center",
            va="top",
            fontsize=cfg.subtitle_fontsize,
            color="#555555",
        )
    draw_footer(fig, source=md_file.name, cfg=cfg)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0.01, 0.04, 0.99, 0.94), h_pad=1.2, w_pad=0.8)
    plt.savefig(output_png, dpi=cfg.dpi, facecolor="white")
    plt.close(fig)
    if not output_png.is_file():
        return None

    write_figure_sidecar(
        output_png,
        {
            "renderer": "cogant.viz.png.render_gnn_markdown_mosaic_png",
            "render_backend": "matplotlib_native",
            "degraded_renderer": False,
            "degraded_rasterization": False,
            "method": (
                "Native matplotlib mosaic composed from every rendered "
                "model.gnn.md page produced by render_gnn_markdown_png."
            ),
            "source_artifact": str(md_file),
            "source_artifact_digest": sha256_file(md_file),
            "layout_method": f"{rows}x{columns} small-multiple page mosaic",
            "layout_seed": None,
            "displayed_counts": {
                "pages": len(pages),
                "sections": len(sections),
                "rows": rows,
                "columns": columns,
            },
            "displayed_count_checks": {
                "all_pages_displayed": True,
                "rendered_page_count": len(pages),
                "source_section_count": len(sections),
            },
            "page_artifacts": [
                {"path": page.name, "sha256": sha256_file(page)} for page in pages
            ],
            "panel_metadata": {
                "panels": [
                    {
                        "key": f"page_{idx + 1}",
                        "source": page.name,
                        "reading_order": "left-to-right, top-to-bottom",
                    }
                    for idx, page in enumerate(pages)
                ]
            },
            "panels": [
                {
                    "key": f"page_{idx + 1}",
                    "source": page.name,
                    "displayed_counts": {"page_index": idx + 1},
                }
                for idx, page in enumerate(pages)
            ],
            "limitations": (
                "Mosaic panels are a readability preview of the emitted markdown; "
                "machine validation still comes from structured GNN artifacts."
            ),
            "known_limitations": (
                "Mosaic panels are a readability preview of the emitted markdown; "
                "machine validation still comes from structured GNN artifacts."
            ),
        },
        cfg,
    )
    return output_png
