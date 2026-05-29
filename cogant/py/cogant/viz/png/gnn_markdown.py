from __future__ import annotations

import logging
from pathlib import Path

from cogant.viz.png.config import (
    DEFAULT_CONFIG,
    RenderConfig,
    draw_footer,
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


