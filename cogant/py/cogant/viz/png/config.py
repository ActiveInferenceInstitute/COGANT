from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
FIGURE_SIDECAR_SCHEMA_VERSION = "1.2"


@dataclass
class RenderConfig:
    """Configurable rendering parameters shared across renderers.

    Every renderer honours these unless explicitly overridden. Users can pass a
    custom ``RenderConfig`` to :func:`render_all_pngs` to tune the look globally.
    """

    dpi: int = 150
    figsize: tuple[float, float] = (16.0, 12.0)
    title_fontsize: int = 18
    subtitle_fontsize: int = 12
    node_fontsize: int = 11
    edge_fontsize: int = 9
    banner_fontsize: int = 10
    footer_fontsize: int = 8
    node_size: int = 1800
    edge_label_bg: str = "#ffffffcc"
    cogant_version: str = "0.1.0"
    max_label_len: int = 32
    show_legend: bool = True
    show_footer: bool = True
    write_sidecar: bool = True
    max_edge_labels: int = 80
    # Safety caps for very large graphs. When a renderer receives more nodes
    # than ``max_render_nodes`` / edges than ``max_render_edges``, it downsamples
    # to the highest-degree subset and annotates the image with the fact.
    # These caps keep native matplotlib layout times bounded on huge repos
    # (e.g. a 6800-node GNN self-analysis) while still producing an informative
    # visualization rather than failing or hanging.
    max_render_nodes: int = 400
    max_render_edges: int = 1200
    max_sequence_participants: int = 120
    extra_metadata: dict[str, str] = field(default_factory=dict)


DEFAULT_CONFIG = RenderConfig()


def truncate(text: str, n: int) -> str:
    text = str(text)
    if len(text) <= n:
        return text
    return text[: max(n - 1, 1)] + "…"


def timestamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _png_dimensions(path: Path) -> dict[str, int] | None:
    """Read PNG dimensions without requiring Pillow."""
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


def write_figure_sidecar(output_png: Path, metadata: dict[str, Any], cfg: RenderConfig) -> None:
    """Write a small evidence sidecar next to a rendered PNG."""
    if not cfg.write_sidecar:
        return
    sidecar = output_png.with_suffix(".figure.json")
    source_artifact_digest = (
        metadata.get("source_artifact_digest")
        or metadata.get("source_sha256")
        or metadata.get("source_artifact_sha256")
        or metadata.get("data_digest_sha256")
    )
    known_limitations = metadata.get("known_limitations") or metadata.get("limitations")
    panel_metadata = (
        metadata.get("panel_metadata") if isinstance(metadata.get("panel_metadata"), dict) else {}
    )
    panels = metadata.get("panels")
    if not isinstance(panels, list):
        nested_panels = panel_metadata.get("panels") if isinstance(panel_metadata, dict) else None
        panels = nested_panels if isinstance(nested_panels, list) else []
    payload = {
        "schema_version": FIGURE_SIDECAR_SCHEMA_VERSION,
        "generated_at": _dt.datetime.now(_dt.UTC).isoformat(),
        "figure": output_png.name,
        "renderer_version": cfg.cogant_version,
        "layout_method": metadata.get("layout_method") or metadata.get("layout"),
        "layout_seed": metadata.get("layout_seed"),
        "source_artifact_digest": source_artifact_digest,
        "known_limitations": known_limitations,
        **metadata,
        "panel_metadata": panel_metadata,
        "panels": panels,
        "image": {
            "path": output_png.name,
            "bytes": output_png.stat().st_size if output_png.exists() else None,
            "sha256": sha256_file(output_png),
            "dimensions_px": _png_dimensions(output_png),
        },
    }
    try:
        sidecar.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not write figure sidecar %s: %s", sidecar, exc)


def downsample_graph(
    nodes: list[tuple[str, str]],
    edges: list[tuple[str, str, str]],
    max_nodes: int,
    max_edges: int,
) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]], dict[str, int]]:
    """Downsample ``(nodes, edges)`` to the highest-degree subset.

    Native matplotlib layout algorithms become prohibitively slow beyond a
    few hundred nodes. For repos with thousands of symbols we keep the most
    connected nodes (and the edges between them) so the resulting PNG still
    communicates the repo's high-level topology.

    Returns ``(sampled_nodes, sampled_edges, stats)`` where ``stats`` has
    ``original_nodes``, ``original_edges``, ``kept_nodes``, ``kept_edges``
    fields so callers can surface the truncation in the metadata banner.
    """
    original_nodes = len(nodes)
    original_edges = len(edges)
    if original_nodes <= max_nodes and original_edges <= max_edges:
        return (
            nodes,
            edges,
            {
                "original_nodes": original_nodes,
                "original_edges": original_edges,
                "kept_nodes": original_nodes,
                "kept_edges": original_edges,
            },
        )

    # Degree-based ranking across the full edge list.
    degree: dict[str, int] = {}
    for s, t, _ in edges:
        degree[s] = degree.get(s, 0) + 1
        degree[t] = degree.get(t, 0) + 1
    for nid, _ in nodes:
        degree.setdefault(nid, 0)

    ranked = sorted(degree.items(), key=lambda kv: (-kv[1], kv[0]))
    keep_ids = {nid for nid, _ in ranked[:max_nodes]}
    label_by_id = dict(nodes)
    sampled_nodes = [(nid, label_by_id.get(nid, nid)) for nid in keep_ids]
    sampled_edges = [(s, t, el) for (s, t, el) in edges if s in keep_ids and t in keep_ids]
    if len(sampled_edges) > max_edges:
        # Keep edges touching the top nodes first.
        rank_of = {nid: i for i, (nid, _) in enumerate(ranked)}
        sampled_edges.sort(key=lambda e: rank_of.get(e[0], 1e9) + rank_of.get(e[1], 1e9))
        sampled_edges = sampled_edges[:max_edges]

    return (
        sampled_nodes,
        sampled_edges,
        {
            "original_nodes": original_nodes,
            "original_edges": original_edges,
            "kept_nodes": len(sampled_nodes),
            "kept_edges": len(sampled_edges),
        },
    )


def draw_metadata_banner(
    ax: Any,
    *,
    title: str,
    subtitle: str | None = None,
    stats: dict[str, Any] | None = None,
    cfg: RenderConfig = DEFAULT_CONFIG,
) -> None:
    """Draw a title + subtitle + stats banner at the top of an axes."""

    ax.get_xlim()
    ax.get_ylim()
    ax.set_title(
        title,
        fontsize=cfg.title_fontsize,
        fontweight="bold",
        color="#1a1a1a",
        pad=18,
        loc="center",
    )
    if subtitle:
        # Matplotlib supports text above the title via figtext; use a second
        # line via suptitle on the figure for consistency.
        ax.figure.suptitle("")  # no-op reset
        ax.text(
            0.5,
            1.04,
            subtitle,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=cfg.subtitle_fontsize,
            color="#555555",
        )
    if stats:
        stats_line = "  •  ".join(f"{k}: {v}" for k, v in stats.items() if v is not None)
        if stats_line:
            ax.text(
                0.5,
                -0.02,
                stats_line,
                transform=ax.transAxes,
                ha="center",
                va="top",
                fontsize=cfg.banner_fontsize,
                color="#333333",
                bbox={"boxstyle": "round,pad=0.4", "facecolor": "#f0f2f5", "edgecolor": "#cccccc"},
            )


def draw_footer(
    fig: Any,
    *,
    source: str | None = None,
    cfg: RenderConfig = DEFAULT_CONFIG,
) -> None:
    """Draw a small footer with source, timestamp, and COGANT version."""
    if not cfg.show_footer:
        return
    parts = [f"COGANT v{cfg.cogant_version}", timestamp()]
    if source:
        parts.append(source)
    if cfg.extra_metadata:
        for k, v in cfg.extra_metadata.items():
            parts.append(f"{k}={v}")
    text = "  ·  ".join(parts)
    fig.text(
        0.5,
        0.005,
        text,
        ha="center",
        va="bottom",
        fontsize=cfg.footer_fontsize,
        color="#888888",
        style="italic",
    )


def draw_color_legend(
    ax: Any,
    color_map: dict[str, str],
    *,
    title: str = "Legend",
    cfg: RenderConfig = DEFAULT_CONFIG,
) -> None:
    """Draw a color legend in the lower-right of an axes."""
    import matplotlib.patches as mpatches

    if not color_map or not cfg.show_legend:
        return
    handles = [mpatches.Patch(color=c, label=str(k)) for k, c in color_map.items()]
    ax.legend(
        handles=handles,
        title=title,
        loc="lower right",
        fontsize=cfg.banner_fontsize,
        title_fontsize=cfg.banner_fontsize,
        framealpha=0.92,
    )
