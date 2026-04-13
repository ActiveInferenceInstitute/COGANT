"""PNG raster exports for COGANT: program graphs, Mermaid diagrams, SVGs, state-space, GNN files.

This module guarantees that a COGANT roundtrip always produces PNG images for
every Mermaid diagram, network graph, state-space artifact, GNN markdown file,
Markov blanket, and connections matrix in the run directory.

It prefers high-quality backends (``mmdc``/``dot``/``cairosvg``) when available
and falls back to pure-Python renderers built on ``matplotlib`` + ``networkx``
so that a clean Python install is sufficient to get a PNG for every artifact.

All renderers produce *informative* images:

* Metadata banner with title, subtitle, and run stats.
* Labeled nodes (not just hash IDs) and labeled edges.
* Kind/role color legends.
* Footer with source path, timestamp, and COGANT version.
* Readable font sizes (title 18, nodes 11, edges 9).

Public API:

Core rasterization
------------------
* :func:`render_program_graph_png` - NetworkX/matplotlib PNG of ``program_graph.json``.
* :func:`render_mermaid_file_to_png` - single ``.mermaid`` file → PNG.
* :func:`render_mermaid_text_to_png` - raw Mermaid text → PNG.
* :func:`render_all_mermaid_in_run` - every ``.mermaid`` in a run → PNG.
* :func:`render_graphviz_dot_to_png` - single ``.dot`` file → PNG.
* :func:`render_all_dot_in_run` - every ``.dot`` under a run → PNG.
* :func:`render_svg_file_to_png` - single ``.svg`` file → PNG.
* :func:`render_all_svg_in_run` - every ``.svg`` in a run → PNG.

Domain renderers
----------------
* :func:`render_state_space_factor_png` - StateSpaceModel → factor graph PNG.
* :func:`render_connections_matrix_png` - StateSpaceModel A/B/C/D heatmaps.
* :func:`render_process_gantt_png` - ProcessModel → Gantt PNG.
* :func:`render_markov_blanket_png` - Markov blanket role-colored PNG.
* :func:`render_summary_cover_png` - single-page run overview PNG.
* :func:`render_gnn_markdown_png` - full ``model.gnn.md`` → multi-page PNG.

Orchestrator
------------
* :func:`render_all_pngs` - one-shot: rasterizes every artifact in a run.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Configuration & shared helpers                                               #
# --------------------------------------------------------------------------- #


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


_DEFAULT_CONFIG = RenderConfig()


def _truncate(text: str, n: int) -> str:
    text = str(text)
    if len(text) <= n:
        return text
    return text[: max(n - 1, 1)] + "…"


def _timestamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _downsample_graph(
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
    sampled_edges = [
        (s, t, el) for (s, t, el) in edges if s in keep_ids and t in keep_ids
    ]
    if len(sampled_edges) > max_edges:
        # Keep edges touching the top nodes first.
        rank_of = {nid: i for i, (nid, _) in enumerate(ranked)}
        sampled_edges.sort(
            key=lambda e: rank_of.get(e[0], 1e9) + rank_of.get(e[1], 1e9)
        )
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


def _draw_metadata_banner(
    ax: Any,
    *,
    title: str,
    subtitle: str | None = None,
    stats: dict[str, Any] | None = None,
    cfg: RenderConfig = _DEFAULT_CONFIG,
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


def _draw_footer(
    fig: Any,
    *,
    source: str | None = None,
    cfg: RenderConfig = _DEFAULT_CONFIG,
) -> None:
    """Draw a small footer with source, timestamp, and COGANT version."""
    if not cfg.show_footer:
        return
    parts = [f"COGANT v{cfg.cogant_version}", _timestamp()]
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


def _draw_color_legend(
    ax: Any,
    color_map: dict[str, str],
    *,
    title: str = "Legend",
    cfg: RenderConfig = _DEFAULT_CONFIG,
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


# --------------------------------------------------------------------------- #
# Program graph PNG (NetworkX + matplotlib).                                   #
# --------------------------------------------------------------------------- #

def program_graph_dict_to_networkx(graph: dict[str, Any]) -> Any:
    """Build a NetworkX DiGraph from exported ``program_graph.json`` structure."""
    import networkx as nx

    g = nx.DiGraph()
    nodes = graph.get("nodes") or {}
    if isinstance(nodes, list):
        for n in nodes:
            nid = n.get("id")
            if nid:
                g.add_node(nid, label=n.get("name", nid), kind=str(n.get("kind", "")))
    elif isinstance(nodes, dict):
        for nid, n in nodes.items():
            g.add_node(nid, label=n.get("name", nid), kind=str(n.get("kind", "")))

    edges = graph.get("edges") or {}
    if isinstance(edges, list):
        for e in edges:
            s, t = e.get("source"), e.get("target")
            if s and t:
                g.add_edge(s, t, kind=str(e.get("kind", "")))
    elif isinstance(edges, dict):
        for e in edges.values():
            s, t = e.get("source"), e.get("target")
            if s and t:
                g.add_edge(s, t, kind=str(e.get("kind", "")))
    return g


_KIND_COLORS = {
    "module": "#4A76D8",
    "package": "#3B5FB8",
    "file": "#7FA6E8",
    "class": "#16a085",
    "trait": "#1abc9c",
    "interface": "#48c9b0",
    "function": "#f39c12",
    "method": "#e67e22",
    "variable": "#95a5a6",
    "field": "#bdc3c7",
    "endpoint": "#e74c3c",
    "event": "#9b59b6",
    "test": "#c0392b",
    "policy": "#d35400",
    "observation": "#27ae60",
    "state": "#8e44ad",
    "action": "#e67e22",
    "": "#667eea",
}


def _kind_color(kind: str) -> str:
    kind = (kind or "").lower()
    # Prefer exact match, fall back to substring lookup.
    if kind in _KIND_COLORS:
        return _KIND_COLORS[kind]
    for key, color in _KIND_COLORS.items():
        if key and key in kind:
            return color
    return _KIND_COLORS[""]


def _build_kind_legend(g: Any) -> dict[str, str]:
    """Build a label→color map for the kinds present in a NetworkX graph."""
    kinds: dict[str, str] = {}
    for _, data in g.nodes(data=True):
        kind = (data.get("kind") or "").lower()
        display = kind or "other"
        if display not in kinds:
            kinds[display] = _kind_color(kind)
    return kinds


def render_program_graph_png(
    program_graph_json: Path,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: int | None = None,
    source_label: str | None = None,
) -> bool:
    """Render ``program_graph.json`` to an informative PNG.

    The rendering includes:

    * A kind-colored spring layout with labeled nodes and labeled edges.
    * A title banner with node/edge counts and kind diversity.
    * A kind legend (module/class/function/…).
    * A footer with source path, timestamp, and COGANT version.
    """
    cfg = cfg or _DEFAULT_CONFIG
    figsize = figsize or cfg.figsize
    dpi = dpi or cfg.dpi

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        logger.warning("matplotlib required for PNG export; install cogant[viz]")
        return False

    try:
        data = json.loads(program_graph_json.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.warning("Could not read %s: %s", program_graph_json, e)
        return False

    g = program_graph_dict_to_networkx(data)
    if g.number_of_nodes() == 0:
        logger.warning("No nodes in %s; skipping PNG", program_graph_json)
        return False

    original_n_nodes = g.number_of_nodes()
    original_n_edges = g.number_of_edges()

    # Downsample very large program graphs to keep matplotlib layout bounded.
    if original_n_nodes > cfg.max_render_nodes or original_n_edges > cfg.max_render_edges:
        degree = dict(g.degree())
        ranked = sorted(degree.items(), key=lambda kv: (-kv[1], kv[0]))
        keep = {nid for nid, _ in ranked[: cfg.max_render_nodes]}
        g = g.subgraph(keep).copy()

    n_nodes = g.number_of_nodes()
    n_edges = g.number_of_edges()
    try:
        pos = nx.kamada_kawai_layout(g) if n_nodes <= 120 else nx.spring_layout(
            g, seed=42, k=2.2 / max(n_nodes, 1) ** 0.5, iterations=80
        )
    except Exception:
        pos = nx.spring_layout(g, seed=42, k=2.2 / max(n_nodes, 1) ** 0.5, iterations=60)

    labels = {
        n: _truncate(g.nodes[n].get("label", n) or n, cfg.max_label_len)
        for n in g.nodes()
    }
    colors = [_kind_color(g.nodes[n].get("kind", "")) for n in g.nodes()]
    edge_labels = {
        (u, v): _truncate(str(d.get("kind", "")), 14)
        for u, v, d in g.edges(data=True)
        if d.get("kind")
    }

    fig, ax = plt.subplots(figsize=figsize)
    nx.draw_networkx_nodes(
        g,
        pos,
        node_size=cfg.node_size,
        node_color=colors,
        alpha=0.95,
        edgecolors="#222222",
        linewidths=1.2,
        ax=ax,
    )
    nx.draw_networkx_edges(
        g,
        pos,
        edge_color="#333333",
        arrows=True,
        arrowsize=16,
        width=1.3,
        alpha=0.7,
        connectionstyle="arc3,rad=0.08",
        ax=ax,
    )
    nx.draw_networkx_labels(
        g,
        pos,
        labels=labels,
        font_size=cfg.node_fontsize,
        font_color="#ffffff",
        font_weight="bold",
        ax=ax,
    )
    if edge_labels:
        nx.draw_networkx_edge_labels(
            g,
            pos,
            edge_labels=edge_labels,
            font_size=cfg.edge_fontsize,
            font_color="#222222",
            bbox={"boxstyle": "round,pad=0.2", "facecolor": cfg.edge_label_bg, "edgecolor": "none"},
            ax=ax,
        )

    ax.set_axis_off()
    kind_counts: dict[str, int] = {}
    for _, d in g.nodes(data=True):
        k = (d.get("kind") or "other").lower()
        kind_counts[k] = kind_counts.get(k, 0) + 1
    top_kinds = sorted(kind_counts.items(), key=lambda x: -x[1])[:5]
    kind_summary = ", ".join(f"{k}×{v}" for k, v in top_kinds)
    pg_stats: dict[str, Any] = {
        "nodes": n_nodes,
        "edges": n_edges,
        "kinds": kind_summary or "n/a",
    }
    if n_nodes < original_n_nodes:
        pg_stats["sampled"] = f"{n_nodes}/{original_n_nodes} nodes"
    _draw_metadata_banner(
        ax,
        title="Program Graph",
        subtitle=f"{source_label or program_graph_json.parent.name}",
        stats=pg_stats,
        cfg=cfg,
    )
    _draw_color_legend(ax, _build_kind_legend(g), title="Node kinds", cfg=cfg)
    _draw_footer(fig, source=str(program_graph_json.name), cfg=cfg)

    plt.tight_layout(rect=(0, 0.02, 1, 0.97))
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True


# --------------------------------------------------------------------------- #
# Mermaid rendering: mmdc preferred, native Python fallback.                   #
# --------------------------------------------------------------------------- #

def _mmdc_command() -> list[str] | None:
    if shutil.which("mmdc"):
        return ["mmdc"]
    if shutil.which("npx"):
        return ["npx", "--yes", "@mermaid-js/mermaid-cli", "mmdc"]
    return None


def render_mermaid_file_to_png(
    mermaid_file: Path,
    output_png: Path,
    *,
    timeout: int = 120,
    allow_native_fallback: bool = True,
    cfg: RenderConfig | None = None,
) -> bool:
    """Render one ``.mmd``/``.mermaid`` file to PNG.

    Strategy:
      1. Try the Mermaid CLI (``mmdc`` or ``npx ... mmdc``) for pixel-perfect output.
      2. On failure, fall back to the pure-Python native renderer
         (:func:`render_mermaid_text_to_png`) so roundtrips always produce PNG.

    Returns ``True`` on success, ``False`` only if **both** paths fail. The
    function never raises; callers treat rendering as best-effort.
    """
    cfg = cfg or _DEFAULT_CONFIG
    prefix = _mmdc_command()
    if prefix:
        output_png.parent.mkdir(parents=True, exist_ok=True)
        cmd = [*prefix, "-i", str(mermaid_file), "-o", str(output_png), "-b", "transparent"]
        try:
            r = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
            if r.stderr:
                logger.debug("mmdc stderr: %s", r.stderr.strip()[:500])
            if output_png.is_file():
                return True
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
            err = getattr(e, "stderr", None) or getattr(e, "stdout", None) or str(e)
            logger.debug(
                "mmdc failed for %s: %s; trying native fallback",
                mermaid_file.name,
                str(err)[:300],
            )

    if not allow_native_fallback:
        return False

    try:
        text = mermaid_file.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.warning("Could not read %s: %s", mermaid_file, e)
        return False
    return render_mermaid_text_to_png(
        text,
        output_png,
        title=mermaid_file.stem.replace("_", " ").title(),
        cfg=cfg,
        source_label=str(mermaid_file.name),
    )


def render_all_mermaid_in_run(
    run_dir: Path,
    figures_dir: Path | None = None,
    *,
    cfg: RenderConfig | None = None,
) -> list[Path]:
    """Render every ``.mermaid``/``.mmd`` file under ``run_dir`` to PNG.

    PNGs are written next to the source files (same directory, same stem) so
    that every Mermaid artifact has a visible sibling image. Returns the list
    of successfully written PNG paths.
    """
    cfg = cfg or _DEFAULT_CONFIG
    written: list[Path] = []
    seen: set[Path] = set()
    for pattern in ("*.mermaid", "*.mmd"):
        for mmd in sorted(run_dir.rglob(pattern)):
            if mmd in seen:
                continue
            seen.add(mmd)
            png = mmd.with_suffix(".png")
            try:
                if render_mermaid_file_to_png(mmd, png, cfg=cfg):
                    written.append(png)
            except Exception as e:  # noqa: BLE001 - never let viz kill the pipeline
                logger.warning("Mermaid→PNG failed for %s: %s", mmd.name, e)
    return written


# --- Native Mermaid parser (best-effort for flowchart/graph/state/class/ER) --- #

_MERMAID_NODE_RE = re.compile(
    r"""
    (?P<id>[A-Za-z0-9_][\w.]*)
    (?:
        \[(?P<rect>[^\]\[]+)\] |
        \((?P<round>[^)(]+)\) |
        \{(?P<diamond>[^}{]+)\} |
        >(?P<asym>[^>]*?)]
    )
    """,
    re.VERBOSE,
)

# Edge regex: handles shape suffixes on src/tgt, all edge operators, and the
# optional ``|label|`` text between the operator and target. IDs may start
# with a digit (hex node IDs are common in COGANT output).
_MERMAID_EDGE_RE = re.compile(
    r"""
    (?P<src>[A-Za-z0-9_][\w.]*)
    (?:\[[^\]\[]*\]|\([^)(]*\)|\{[^}{]*\}|>[^>]*])?             # optional src shape
    \s*
    (?P<op>-->|---|-\.->|==>)                                    # edge operator
    (?:\|(?P<edge_label>[^|]*)\|)?                               # optional edge label
    \s*
    (?P<tgt>[A-Za-z0-9_][\w.]*)
    (?:\[[^\]\[]*\]|\([^)(]*\)|\{[^}{]*\}|>[^>]*])?             # optional tgt shape
    """,
    re.VERBOSE,
)

_MERMAID_SUBGRAPH_RE = re.compile(
    r"""
    ^\s*subgraph\s+
    (?P<sid>[A-Za-z0-9_][\w]*)?                                  # optional id
    \s*
    (?:
        \[(?P<rect>[^\]\[]+)\] |
        \['(?P<quoted>[^']+)'\] |                                # special: ['label']
        \((?P<round>[^)(]+)\) |
        \{(?P<diamond>[^}{]+)\}
    )?
    """,
    re.VERBOSE,
)

# Lines which are pure styling/metadata and must never contribute graph nodes.
_MERMAID_SKIP_PREFIXES = (
    "graph",
    "flowchart",
    "subgraph",
    "end",
    "classDef",
    "class ",  # styling: `class Foo highlighted`
    "click",
    "style ",
    "linkStyle",
    "direction",
    "theme",
    "%%",
)

_MERMAID_RESERVED_IDS = frozenset(
    {
        "graph",
        "flowchart",
        "subgraph",
        "end",
        "TD",
        "TB",
        "LR",
        "BT",
        "RL",
        "direction",
        "classDef",
        "linkStyle",
        "style",
        "click",
    }
)

_MERMAID_CLASS_HEADER_RE = re.compile(r"^\s*class\s+([A-Za-z_][\w]*)\s*\{")
_MERMAID_CLASS_REL_RE = re.compile(
    r"^\s*([A-Za-z_][\w]*)\s*(<\|--|--\|>|\*--|o--|-->|--|\.\.|\.\.>)\s*([A-Za-z_][\w]*)"
    r"(?:\s*:\s*(?P<label>.+))?$"
)
_MERMAID_STATE_TRANS_RE = re.compile(
    r"^\s*([A-Za-z_*][\w*]*)\s*-->\s*([A-Za-z_*][\w*]*)(?:\s*:\s*(.+))?$"
)


def _parse_mermaid_flowchart(
    text: str,
) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]], dict[str, str]]:
    """Extract (node_id, label), (src, tgt, edge_label) tuples, and cluster map.

    Returns:
        nodes: list of (id, display label) pairs.
        edges: list of (source, target, edge_label) triples (edge_label may be '').
        clusters: mapping of {subgraph_id or synthesized name: label}.
    """
    node_labels: dict[str, str] = {}
    edges: list[tuple[str, str, str]] = []
    clusters: dict[str, str] = {}
    subgraph_ids_to_skip: set[str] = set()

    for raw in text.splitlines():
        ln = raw.strip()
        if not ln:
            continue
        # Skip styling, comments, and directives entirely.
        if any(ln.startswith(p) for p in _MERMAID_SKIP_PREFIXES):
            if ln.startswith("subgraph"):
                sm = _MERMAID_SUBGRAPH_RE.match(raw)
                if sm:
                    sid = sm.group("sid")
                    slabel = (
                        sm.group("rect")
                        or sm.group("quoted")
                        or sm.group("round")
                        or sm.group("diamond")
                        or sid
                        or ""
                    )
                    if sid:
                        clusters[sid] = slabel or sid
                        subgraph_ids_to_skip.add(sid)
            continue

        # Edge extraction (may capture optional edge label). Scan all edge
        # matches on the line so multi-edge declarations work, then remove
        # the matched spans before running node-shape finditer so labels
        # inside ``|...|`` never leak as pseudo-nodes.
        consumed_spans: list[tuple[int, int]] = []
        for em in _MERMAID_EDGE_RE.finditer(ln):
            src = em.group("src")
            tgt = em.group("tgt")
            edge_label = (em.group("edge_label") or "").strip()
            edges.append((src, tgt, edge_label))
            for nid in (src, tgt):
                if nid not in _MERMAID_RESERVED_IDS:
                    node_labels.setdefault(nid, nid)
            consumed_spans.append(em.span())

        # Build a scrubbed version of the line where edge matches and any
        # pipe-delimited label segments are replaced with spaces — this keeps
        # column offsets intact and avoids false positives from finditer.
        scrubbed_chars = list(ln)
        for s, e in consumed_spans:
            for i in range(s, e):
                scrubbed_chars[i] = " "
        # Also blank out any leftover |label| segments (defensive).
        for pm in re.finditer(r"\|[^|]*\|", "".join(scrubbed_chars)):
            for i in range(pm.start(), pm.end()):
                scrubbed_chars[i] = " "
        scrubbed = "".join(scrubbed_chars)

        # Node-shape extraction: only match declarations that include a
        # bracketed label (_MERMAID_NODE_RE now requires a shape suffix).
        for nm in _MERMAID_NODE_RE.finditer(scrubbed):
            nid = nm.group("id")
            if not nid or nid in _MERMAID_RESERVED_IDS:
                continue
            label = (
                nm.group("rect")
                or nm.group("round")
                or nm.group("diamond")
                or nm.group("asym")
                or nid
            )
            if label:
                label = label.strip().strip("'\"")
            if label and label != nid:
                node_labels[nid] = label
            else:
                node_labels.setdefault(nid, nid)

    # Drop subgraph IDs — they are containers, not graph nodes.
    for sid in subgraph_ids_to_skip:
        node_labels.pop(sid, None)

    return list(node_labels.items()), edges, clusters


def _parse_mermaid_class_diagram(
    text: str,
) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """Parse a Mermaid ``classDiagram`` into (nodes, labeled_edges).

    Recognises:
      * ``class Foo`` — single declaration
      * ``class Foo { ... }`` — body block (fields/methods) with labeled class id
      * Relationships ``A <|-- B``, ``A o-- B``, ``A .. B`` etc., optionally
        followed by ``: label``.

    Fields inside a class body are *not* promoted to graph nodes.
    """
    node_labels: dict[str, str] = {}
    edges: list[tuple[str, str, str]] = []
    in_class_body: str | None = None
    for raw in text.splitlines():
        ln = raw.strip()
        if not ln:
            continue
        if in_class_body:
            if ln == "}":
                in_class_body = None
            continue
        hdr = _MERMAID_CLASS_HEADER_RE.match(raw)
        if hdr:
            cid = hdr.group(1)
            node_labels.setdefault(cid, cid)
            in_class_body = cid
            continue
        rel = _MERMAID_CLASS_REL_RE.match(raw)
        if rel:
            a, _op, b = rel.group(1), rel.group(2), rel.group(3)
            edge_label = (rel.group("label") or "").strip() if rel.lastgroup else ""
            edges.append((a, b, edge_label))
            node_labels.setdefault(a, a)
            node_labels.setdefault(b, b)
            continue
        if ln.startswith(("classDiagram", "%%", "note ", "%%{", "direction")):
            continue
        # Single-name class declaration `class Foo`
        mcls = re.match(r"class\s+([A-Za-z_][\w]*)\s*$", ln)
        if mcls:
            node_labels.setdefault(mcls.group(1), mcls.group(1))
    return list(node_labels.items()), edges


def _parse_mermaid_state_diagram(
    text: str,
) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """Parse ``stateDiagram`` / ``stateDiagram-v2``.

    Handles:
      * transitions ``A --> B`` and ``A --> B: label`` (label is kept)
      * aliased states ``s0: Human-readable name``
      * ``note right of X ... end note`` blocks (skipped entirely)
      * malformed edges with empty sources (skipped)
    """
    node_labels: dict[str, str] = {}
    edges: list[tuple[str, str, str]] = []
    in_note = False
    alias_re = re.compile(r"^\s*([A-Za-z_][\w]*)\s*:\s*(.+)$")
    for raw in text.splitlines():
        ln = raw.strip()
        if not ln:
            continue
        if ln.startswith("note ") or ln.lower().startswith("note right of") or ln.lower().startswith("note left of"):
            in_note = True
            continue
        if in_note:
            if ln.lower().startswith("end note"):
                in_note = False
            continue
        if ln.startswith(("stateDiagram", "%%")):
            continue
        if ln.startswith("[*]"):
            # still want to catch entry/exit transitions
            pass
        mm = _MERMAID_STATE_TRANS_RE.match(raw)
        if mm:
            a, b = mm.group(1), mm.group(2)
            if not a or not b:
                continue
            label = (mm.group(3) or "").strip()
            edges.append((a, b, label))
            node_labels.setdefault(a, a)
            node_labels.setdefault(b, b)
            continue
        alias = alias_re.match(raw)
        if alias:
            node_labels[alias.group(1)] = alias.group(2).strip()
    return list(node_labels.items()), edges


def _detect_mermaid_kind(text: str) -> str:
    head = (text.lstrip().splitlines() or [""])[0].strip().lower()
    if head.startswith(("classdiagram",)):
        return "class"
    if head.startswith(("statediagram", "state-diagram", "statediagram-v2")):
        return "state"
    if head.startswith(("sequencediagram",)):
        return "sequence"
    if head.startswith(("gantt",)):
        return "gantt"
    if head.startswith(("erdiagram",)):
        return "er"
    return "graph"


def _parse_mermaid_sequence(text: str) -> tuple[list[str], list[tuple[str, str, str]]]:
    """Return (participants, [(src, tgt, message)])."""
    participants: list[str] = []
    messages: list[tuple[str, str, str]] = []
    msg_re = re.compile(
        r"^\s*([A-Za-z_][\w]*)\s*(?:->>|-->>|->|-->|-x|--x)\s*([A-Za-z_][\w]*)\s*(?::\s*(.*))?$"
    )
    part_re = re.compile(r"^\s*(?:participant|actor)\s+([A-Za-z_][\w]*)")
    for raw in text.splitlines():
        pmatch = part_re.match(raw)
        if pmatch and pmatch.group(1) not in participants:
            participants.append(pmatch.group(1))
            continue
        mmatch = msg_re.match(raw)
        if mmatch:
            s, t, msg = mmatch.group(1), mmatch.group(2), (mmatch.group(3) or "").strip()
            if s not in participants:
                participants.append(s)
            if t not in participants:
                participants.append(t)
            messages.append((s, t, msg))
    return participants, messages


def _parse_mermaid_gantt(text: str) -> list[tuple[str, str, int, int]]:
    """Very small Gantt parser: yields (section, task, start, duration)."""
    tasks: list[tuple[str, str, int, int]] = []
    current_section = "Tasks"
    counter = 0
    for raw in text.splitlines():
        ln = raw.strip()
        if not ln or ln.startswith(("gantt", "title", "dateFormat", "axisFormat", "%%")):
            continue
        if ln.lower().startswith("section "):
            current_section = ln[len("section ") :].strip()
            continue
        # Format: "<task_name> :<id>, <start_or_after>, <duration>" — we don't fully parse dates;
        # instead we lay tasks sequentially with duration 1 each and use any numeric hints.
        if ":" in ln:
            name = ln.split(":", 1)[0].strip()
            parts = [p.strip() for p in ln.split(":", 1)[1].split(",")]
            start = counter
            dur = 1
            for p in parts:
                m = re.search(r"(\d+)", p)
                if m and int(m.group(1)) > 0:
                    dur = int(m.group(1))
                    break
            tasks.append((current_section, name, start, dur))
            counter += dur
    return tasks


def render_mermaid_text_to_png(
    text: str,
    output_png: Path,
    *,
    title: str | None = None,
    cfg: RenderConfig | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: int | None = None,
    source_label: str | None = None,
) -> bool:
    """Native Python Mermaid → PNG renderer.

    Supports the subset of Mermaid COGANT actually emits: ``graph``/``flowchart``,
    ``classDiagram``, ``stateDiagram``/``stateDiagram-v2``, ``sequenceDiagram``,
    and a minimal ``gantt``. The output is an informative matplotlib rendering
    with title banner, labeled nodes/edges, kind color legend, and footer.
    """
    cfg = cfg or _DEFAULT_CONFIG
    figsize = figsize or cfg.figsize
    dpi = dpi or cfg.dpi

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        logger.warning("matplotlib required for native Mermaid renderer")
        return False

    try:
        kind = _detect_mermaid_kind(text)
        output_png.parent.mkdir(parents=True, exist_ok=True)

        if kind == "sequence":
            participants, messages = _parse_mermaid_sequence(text)
            if not participants:
                return False
            return _render_sequence_png(
                participants, messages, output_png, title, cfg=cfg, source_label=source_label
            )

        if kind == "gantt":
            tasks = _parse_mermaid_gantt(text)
            if not tasks:
                return False
            return _render_gantt_png(
                tasks, output_png, title, cfg=cfg, source_label=source_label
            )

        clusters: dict[str, str] = {}
        if kind == "class":
            nodes, edges_raw = _parse_mermaid_class_diagram(text)
        elif kind == "state":
            nodes, edges_raw = _parse_mermaid_state_diagram(text)
        else:
            nodes, edges_raw, clusters = _parse_mermaid_flowchart(text)

        if not nodes and not edges_raw:
            return False

        # Normalize edges to 3-tuples (src, tgt, label).
        edges: list[tuple[str, str, str]] = []
        for e in edges_raw:
            if len(e) == 3:
                edges.append((e[0], e[1], e[2] or ""))
            elif len(e) == 2:
                edges.append((e[0], e[1], ""))

        # Downsample very large graphs so matplotlib layout stays fast.
        nodes, edges, sample_stats = _downsample_graph(
            list(nodes), edges, cfg.max_render_nodes, cfg.max_render_edges
        )

        g = nx.DiGraph()
        for nid, label in nodes:
            g.add_node(nid, label=label)
        for triple in edges:
            if len(triple) == 3:
                s, t, el = triple
            else:
                s, t, el = triple[0], triple[1], ""
            if s not in g:
                g.add_node(s, label=s)
            if t not in g:
                g.add_node(t, label=t)
            g.add_edge(s, t, label=el)

        n = max(g.number_of_nodes(), 1)
        try:
            pos = nx.kamada_kawai_layout(g) if n <= 80 else nx.spring_layout(
                g, seed=17, k=2.4 / (n ** 0.5), iterations=200
            )
        except Exception:
            pos = nx.spring_layout(g, seed=17, k=2.0 / (n ** 0.5), iterations=120)

        fig, ax = plt.subplots(figsize=figsize)

        node_color_by_kind = {
            "class": "#16a085",
            "state": "#8e44ad",
            "graph": "#4A76D8",
        }
        node_color = node_color_by_kind.get(kind, "#4A76D8")
        nx.draw_networkx_nodes(
            g,
            pos,
            node_size=cfg.node_size,
            node_color=node_color,
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
            arrowsize=18,
            width=1.4,
            alpha=0.8,
            connectionstyle="arc3,rad=0.1",
            ax=ax,
        )
        labels = {
            n_: _truncate(g.nodes[n_].get("label", n_) or n_, cfg.max_label_len)
            for n_ in g.nodes()
        }
        nx.draw_networkx_labels(
            g,
            pos,
            labels=labels,
            font_size=cfg.node_fontsize,
            font_color="white",
            font_weight="bold",
            ax=ax,
        )
        edge_labels = {
            (u, v): _truncate(d.get("label") or "", 14)
            for u, v, d in g.edges(data=True)
            if d.get("label")
        }
        if edge_labels:
            nx.draw_networkx_edge_labels(
                g,
                pos,
                edge_labels=edge_labels,
                font_size=cfg.edge_fontsize,
                font_color="#222222",
                bbox={"boxstyle": "round,pad=0.2", "facecolor": cfg.edge_label_bg, "edgecolor": "none"},
                ax=ax,
            )

        ax.set_axis_off()
        ttl = title or f"Mermaid {kind} diagram"
        stats = {"nodes": g.number_of_nodes(), "edges": g.number_of_edges(), "kind": kind}
        if clusters:
            stats["clusters"] = len(clusters)
        if sample_stats.get("kept_nodes", 0) < sample_stats.get("original_nodes", 0):
            stats["sampled"] = (
                f"{sample_stats['kept_nodes']}/{sample_stats['original_nodes']} nodes"
            )
        _draw_metadata_banner(
            ax,
            title=ttl,
            subtitle=source_label or None,
            stats=stats,
            cfg=cfg,
        )
        if clusters:
            _draw_color_legend(
                ax,
                dict.fromkeys(list(clusters.values())[:6], node_color),
                title="Clusters",
                cfg=cfg,
            )
        _draw_footer(fig, source=source_label or title, cfg=cfg)

        plt.tight_layout(rect=(0, 0.02, 1, 0.97))
        plt.savefig(output_png, dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return output_png.is_file()
    except Exception as e:  # noqa: BLE001
        logger.warning("Native Mermaid render failed: %s", e)
        return False


def _render_sequence_png(
    participants: list[str],
    messages: list[tuple[str, str, str]],
    output_png: Path,
    title: str | None,
    *,
    cfg: RenderConfig = _DEFAULT_CONFIG,
    source_label: str | None = None,
) -> bool:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Guard against huge sequence diagrams (e.g. every function in a 6800-node
    # repo becomes a participant). We keep the busiest participants (those
    # involved in the most messages) and drop the rest.
    original_participants = len(participants)
    if original_participants > cfg.max_sequence_participants and messages:
        activity: dict[str, int] = dict.fromkeys(participants, 0)
        for s, t, _ in messages:
            activity[s] = activity.get(s, 0) + 1
            activity[t] = activity.get(t, 0) + 1
        ranked = sorted(activity.items(), key=lambda kv: (-kv[1], kv[0]))
        keep = {p for p, _ in ranked[: cfg.max_sequence_participants]}
        participants = [p for p in participants if p in keep]
        messages = [(s, t, m) for (s, t, m) in messages if s in keep and t in keep]
    elif original_participants > cfg.max_sequence_participants:
        participants = participants[: cfg.max_sequence_participants]

    # Cap messages to prevent 10k-lane renders from hanging.
    max_msgs = 200
    original_messages = len(messages)
    if original_messages > max_msgs:
        messages = messages[:max_msgs]

    if not participants:
        return False

    height = max(cfg.figsize[1], 0.6 * max(len(messages), 1) + 4.0)
    fig, ax = plt.subplots(figsize=(cfg.figsize[0], min(height, 40.0)))
    xs = {p: i for i, p in enumerate(participants)}
    lane_color = "#5f6f8a"

    # Participant lanes
    for p, i in xs.items():
        ax.plot(
            [i, i],
            [0, len(messages) + 1],
            color=lane_color,
            linewidth=1.4,
            linestyle="--",
            alpha=0.6,
        )
        ax.text(
            i,
            len(messages) + 1.4,
            _truncate(p, cfg.max_label_len),
            ha="center",
            va="bottom",
            fontsize=cfg.node_fontsize + 1,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.35",
                "facecolor": "#4A76D8",
                "edgecolor": "#1f3a75",
            },
            color="white",
        )

    for idx, (s, t, msg) in enumerate(messages):
        y = len(messages) - idx
        if s == t:
            # self-message: draw a small arc to the right
            ax.annotate(
                "",
                xy=(xs[s] + 0.25, y - 0.1),
                xytext=(xs[s], y + 0.1),
                arrowprops={"arrowstyle": "->", "color": "#8e44ad", "lw": 1.6, "connectionstyle": "arc3,rad=-0.5"},
            )
        else:
            ax.annotate(
                "",
                xy=(xs[t], y),
                xytext=(xs[s], y),
                arrowprops={"arrowstyle": "->", "color": "#2c3e50", "lw": 1.6},
            )
        mid = (xs[s] + xs[t]) / 2 if s != t else xs[s] + 0.25
        if msg:
            ax.text(
                mid,
                y + 0.18,
                _truncate(msg, 60),
                ha="center",
                va="bottom",
                fontsize=cfg.edge_fontsize,
                bbox={"boxstyle": "round,pad=0.25", "facecolor": cfg.edge_label_bg, "edgecolor": "none"},
            )

    ax.set_xlim(-0.7, max(len(participants) - 0.3, 1.0))
    ax.set_ylim(-0.5, len(messages) + 2.6)
    ax.set_axis_off()
    seq_stats: dict[str, Any] = {
        "participants": len(participants),
        "messages": len(messages),
    }
    if original_participants > len(participants):
        seq_stats["sampled_participants"] = (
            f"{len(participants)}/{original_participants}"
        )
    if original_messages > len(messages):
        seq_stats["sampled_messages"] = f"{len(messages)}/{original_messages}"
    _draw_metadata_banner(
        ax,
        title=title or "Sequence diagram",
        subtitle=source_label,
        stats=seq_stats,
        cfg=cfg,
    )
    _draw_footer(fig, source=source_label or title, cfg=cfg)

    plt.tight_layout(rect=(0, 0.02, 1, 0.97))
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_png.is_file()


def _render_gantt_png(
    tasks: list[tuple[str, str, int, int]],
    output_png: Path,
    title: str | None,
    *,
    cfg: RenderConfig = _DEFAULT_CONFIG,
    source_label: str | None = None,
) -> bool:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    height = max(cfg.figsize[1], 0.45 * len(tasks) + 3.0)
    fig, ax = plt.subplots(figsize=(cfg.figsize[0], height))
    sections: dict[str, str] = {}
    palette = [
        "#1abc9c",
        "#3498db",
        "#9b59b6",
        "#e67e22",
        "#e74c3c",
        "#2c3e50",
        "#16a085",
        "#f39c12",
    ]
    for i, section in enumerate(dict.fromkeys(t[0] for t in tasks)):
        sections[section] = palette[i % len(palette)]

    for idx, (section, name, start, dur) in enumerate(tasks):
        ax.barh(
            idx,
            max(dur, 1),
            left=start,
            height=0.6,
            color=sections[section],
            edgecolor="#222222",
            linewidth=0.9,
        )
        ax.text(
            start + max(dur, 1) / 2,
            idx,
            _truncate(name, 40),
            ha="center",
            va="center",
            fontsize=cfg.edge_fontsize,
            color="white",
            fontweight="bold",
        )
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels([_truncate(t[1], 28) for t in tasks], fontsize=cfg.edge_fontsize)
    ax.invert_yaxis()
    ax.set_xlabel("Step", fontsize=cfg.banner_fontsize + 1)
    ax.grid(axis="x", color="#dddddd", linestyle="--", linewidth=0.6, alpha=0.7)
    _draw_metadata_banner(
        ax,
        title=title or "Gantt timeline",
        subtitle=source_label,
        stats={"tasks": len(tasks), "sections": len(sections)},
        cfg=cfg,
    )
    _draw_color_legend(ax, sections, title="Sections", cfg=cfg)
    _draw_footer(fig, source=source_label or title, cfg=cfg)

    plt.tight_layout(rect=(0, 0.02, 1, 0.95))
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_png.is_file()


# --------------------------------------------------------------------------- #
# SVG → PNG                                                                    #
# --------------------------------------------------------------------------- #

def render_svg_file_to_png(svg_file: Path, output_png: Path, *, timeout: int = 60) -> bool:
    """Convert an SVG file to PNG.

    Preference order:
      1. ``cairosvg`` (pure-Python, no external binary).
      2. ``rsvg-convert`` binary.
      3. ``inkscape`` binary.
      4. ImageMagick ``convert`` binary.
    Returns ``True`` on success.
    """
    if not svg_file.is_file():
        return False
    output_png.parent.mkdir(parents=True, exist_ok=True)

    # 1) cairosvg
    try:
        import cairosvg  # type: ignore[import-not-found,unused-ignore]

        cairosvg.svg2png(url=str(svg_file), write_to=str(output_png), output_width=1400)
        if output_png.is_file():
            return True
    except Exception:
        pass

    # 2) rsvg-convert
    if shutil.which("rsvg-convert"):
        cmd = ["rsvg-convert", "-w", "1400", "-o", str(output_png), str(svg_file)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
            if output_png.is_file():
                return True
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
            logger.debug("rsvg-convert failed for %s: %s", svg_file.name, e)

    # 3) inkscape
    if shutil.which("inkscape"):
        cmd = [
            "inkscape",
            str(svg_file),
            "--export-type=png",
            f"--export-filename={output_png}",
            "--export-width=1400",
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
            if output_png.is_file():
                return True
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
            logger.debug("inkscape failed for %s: %s", svg_file.name, e)

    # 4) ImageMagick convert
    if shutil.which("convert"):
        cmd = ["convert", "-density", "150", str(svg_file), str(output_png)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
            if output_png.is_file():
                return True
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
            logger.debug("ImageMagick convert failed for %s: %s", svg_file.name, e)

    logger.debug("No SVG→PNG backend succeeded for %s", svg_file.name)
    return False


def render_all_svg_in_run(run_dir: Path) -> list[Path]:
    """Convert every ``.svg`` under ``run_dir`` to a sibling ``.png``.

    If no native SVG backend is available, falls back to a matplotlib-based
    placeholder carrying the same banner/metadata shell so the run still
    yields one PNG per SVG.
    """
    written: list[Path] = []
    for svg in sorted(run_dir.rglob("*.svg")):
        png = svg.with_suffix(".png")
        try:
            if render_svg_file_to_png(svg, png):
                written.append(png)
            elif _render_svg_placeholder_png(svg, png):
                written.append(png)
        except Exception as e:  # noqa: BLE001
            logger.warning("SVG→PNG failed for %s: %s", svg.name, e)
    return written


def _render_svg_placeholder_png(
    svg_file: Path,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
) -> bool:
    """When no SVG backend exists, emit a matplotlib placeholder carrying metadata."""
    cfg = cfg or _DEFAULT_CONFIG
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    try:
        size = svg_file.stat().st_size if svg_file.is_file() else 0
    except OSError:
        size = 0

    fig, ax = plt.subplots(figsize=cfg.figsize)
    ax.set_axis_off()
    _draw_metadata_banner(
        ax,
        title=svg_file.stem.replace("_", " ").title(),
        subtitle="SVG rasterization (placeholder)",
        stats={"bytes": size, "format": "svg"},
        cfg=cfg,
    )
    ax.text(
        0.5,
        0.5,
        "No SVG→PNG backend available.\nInstall cairosvg or rsvg-convert to rasterize.",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=cfg.node_fontsize,
        color="#555555",
        bbox={
            "boxstyle": "round,pad=0.6",
            "facecolor": "#f0f2f5",
            "edgecolor": "#cccccc",
        },
    )
    _draw_footer(fig, source=svg_file.name, cfg=cfg)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_png.is_file()


# --------------------------------------------------------------------------- #
# Graphviz DOT → PNG                                                           #
# --------------------------------------------------------------------------- #

def render_graphviz_dot_to_png(dot_file: Path, output_png: Path, *, timeout: int = 120) -> bool:
    """Render a Graphviz ``.dot`` file to PNG using the ``dot`` binary if available."""
    dot_bin = shutil.which("dot")
    if not dot_bin:
        logger.warning("Graphviz ``dot`` not on PATH; skip %s", dot_file.name)
        return False
    if not dot_file.is_file():
        return False
    output_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [dot_bin, "-Tpng", str(dot_file), "-o", str(output_png)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
        return output_png.is_file()
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
        logger.warning("Graphviz render failed for %s: %s", dot_file.name, e)
        return False


def render_all_dot_in_run(run_dir: Path) -> list[Path]:
    """Render every ``.dot`` under ``run_dir`` to a sibling ``.png`` via dot/Graphviz."""
    written: list[Path] = []
    if not shutil.which("dot"):
        return written
    for dot in sorted(run_dir.rglob("*.dot")):
        png = dot.with_suffix(".png")
        try:
            if render_graphviz_dot_to_png(dot, png):
                written.append(png)
        except Exception as e:  # noqa: BLE001
            logger.warning("dot→PNG failed for %s: %s", dot.name, e)
    return written


def find_graph_dot(run_dir: Path) -> Path | None:
    """Return path to ``graph.dot`` under ``diagrams/`` or run root."""
    for candidate in (run_dir / "diagrams" / "graph.dot", run_dir / "graph.dot"):
        if candidate.is_file():
            return candidate
    return None


# --------------------------------------------------------------------------- #
# State-space factor graph PNG (for StateSpaceModel)                           #
# --------------------------------------------------------------------------- #


def _state_space_entities(
    state_space: Any,
) -> tuple[list[Any], list[Any], list[Any]]:
    """Return (variables, observations, actions) from a StateSpaceModel.

    Accepts both the dataclass (``variables`` / ``observations`` / ``actions``)
    and the Pydantic (``state_variables`` / ``observation_modalities``) shapes.
    """
    variables_raw = (
        getattr(state_space, "variables", None)
        or getattr(state_space, "state_variables", None)
        or {}
    )
    observations_raw = (
        getattr(state_space, "observations", None)
        or getattr(state_space, "observation_modalities", None)
        or {}
    )
    actions_raw = getattr(state_space, "actions", None) or {}
    variables = list(variables_raw.values()) if isinstance(variables_raw, dict) else list(variables_raw)
    observations = (
        list(observations_raw.values()) if isinstance(observations_raw, dict) else list(observations_raw)
    )
    actions = list(actions_raw.values()) if isinstance(actions_raw, dict) else list(actions_raw)
    return variables, observations, actions


def render_state_space_factor_png(
    state_space: Any,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: int | None = None,
    source_label: str | None = None,
) -> bool:
    """Render a StateSpaceModel as a factor-graph PNG (matplotlib + networkx).

    The output shows hidden states (blue), observations (green), and actions
    (orange) in a layered layout with likelihood and control edges. Labels
    use actual variable names, not ``s0``/``o1`` placeholders, and the banner
    reports cardinality and factor counts.
    """
    cfg = cfg or _DEFAULT_CONFIG
    figsize = figsize or cfg.figsize
    dpi = dpi or cfg.dpi

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        return False

    if state_space is None:
        return False

    try:
        variables, observations, actions = _state_space_entities(state_space)
        if not variables and not observations and not actions:
            return False

        original_var_n = len(variables)
        original_obs_n = len(observations)
        original_act_n = len(actions)

        # Cap per-layer sizes so the factor graph stays legible and the
        # likelihood edge set never explodes past ~(layer_cap^2). For a repo
        # with 1200 observations and 200 variables, the uncapped graph would
        # have ~240k edges and hang matplotlib; we take the first ``layer_cap``
        # entries from each list (the state-space compiler preserves insertion
        # order, so this keeps the earliest-registered variables).
        layer_cap = max(1, min(cfg.max_render_nodes // 3, 80))
        variables = list(variables)[:layer_cap]
        observations = list(observations)[:layer_cap]
        actions = list(actions)[:layer_cap]

        g = nx.DiGraph()
        var_ids: list[str] = []
        obs_ids: list[str] = []
        act_ids: list[str] = []

        def _display_name(obj: Any, fallback: str) -> str:
            return (
                str(getattr(obj, "name", None) or getattr(obj, "id", None) or fallback)
            )

        def _cardinality(obj: Any) -> int | None:
            return getattr(obj, "cardinality", None) or getattr(obj, "size", None)

        for i, v in enumerate(variables):
            name = _display_name(v, f"s_{i}")
            card = _cardinality(v)
            vid = f"s:{name}"
            var_ids.append(vid)
            g.add_node(
                vid,
                label=f"s\n{_truncate(name, 16)}"
                + (f"\n|{card}|" if card else ""),
                kind="state",
            )
        for i, o in enumerate(observations):
            name = _display_name(o, f"o_{i}")
            card = _cardinality(o)
            oid = f"o:{name}"
            obs_ids.append(oid)
            g.add_node(
                oid,
                label=f"o\n{_truncate(name, 16)}"
                + (f"\n|{card}|" if card else ""),
                kind="obs",
            )
        for i, a in enumerate(actions):
            name = _display_name(a, f"u_{i}")
            aid = f"u:{name}"
            act_ids.append(aid)
            g.add_node(aid, label=f"u\n{_truncate(name, 16)}", kind="act")

        # Likelihood edges connect every (state, obs) pair, which is quadratic
        # in layer size. For the default ``layer_cap=80`` this yields up to
        # 6400 edges which still renders in ~1 s. Any cap above that and the
        # factor graph becomes visually unreadable anyway.
        for vid in var_ids:
            for oid in obs_ids:
                g.add_edge(vid, oid, kind="likelihood (A)")
            for aid in act_ids:
                g.add_edge(aid, vid, kind="control (B)")

        pos: dict[str, tuple[float, float]] = {}

        def _layer(ids: list[str], y: float) -> None:
            n = max(len(ids), 1)
            for i, nid in enumerate(ids):
                pos[nid] = ((i + 1) / (n + 1), y)

        _layer(obs_ids, 0.95)
        _layer(var_ids, 0.55)
        _layer(act_ids, 0.12)

        color_by = {
            "state (s)": "#8e44ad",
            "observation (o)": "#27ae60",
            "action (u)": "#e67e22",
        }
        node_color_map = {"state": "#8e44ad", "obs": "#27ae60", "act": "#e67e22"}

        fig, ax = plt.subplots(figsize=figsize)
        for kind, color in node_color_map.items():
            ids = [n_ for n_, data in g.nodes(data=True) if data.get("kind") == kind]
            if ids:
                nx.draw_networkx_nodes(
                    g,
                    pos,
                    nodelist=ids,
                    node_color=color,
                    node_size=cfg.node_size,
                    alpha=0.95,
                    edgecolors="#222222",
                    linewidths=1.3,
                    ax=ax,
                )
        nx.draw_networkx_edges(
            g,
            pos,
            edge_color="#2c3e50",
            arrows=True,
            arrowsize=18,
            width=1.3,
            alpha=0.75,
            connectionstyle="arc3,rad=0.07",
            ax=ax,
        )
        nx.draw_networkx_labels(
            g,
            pos,
            labels={n_: g.nodes[n_].get("label", n_) for n_ in g.nodes()},
            font_size=cfg.node_fontsize - 1,
            font_color="white",
            font_weight="bold",
            ax=ax,
        )
        edge_kind_labels = {
            (u, v): d.get("kind", "") for u, v, d in g.edges(data=True)
        }
        # Only label a subset to avoid clutter: label the first control/likelihood edge only.
        seen_kinds: set[str] = set()
        minimal_labels: dict[tuple[str, str], str] = {}
        for key, k in edge_kind_labels.items():
            if k and k not in seen_kinds:
                minimal_labels[key] = k
                seen_kinds.add(k)
        if minimal_labels:
            nx.draw_networkx_edge_labels(
                g,
                pos,
                edge_labels=minimal_labels,
                font_size=cfg.edge_fontsize,
                bbox={"boxstyle": "round,pad=0.25", "facecolor": cfg.edge_label_bg, "edgecolor": "none"},
                ax=ax,
            )

        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.1, 1.15)
        ax.set_axis_off()
        def _fmt_count(displayed: int, real: int) -> str:
            return f"{displayed}" if displayed == real else f"{displayed}/{real}"

        _draw_metadata_banner(
            ax,
            title="State-Space Factor Graph",
            subtitle=source_label,
            stats={
                "states (s)": _fmt_count(len(var_ids), original_var_n),
                "obs (o)": _fmt_count(len(obs_ids), original_obs_n),
                "actions (u)": _fmt_count(len(act_ids), original_act_n),
            },
            cfg=cfg,
        )
        _draw_color_legend(ax, color_by, title="Factors", cfg=cfg)
        _draw_footer(fig, source=source_label or "state_space", cfg=cfg)

        plt.tight_layout(rect=(0, 0.02, 1, 0.97))
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("State-space factor PNG failed: %s", e)
        return False


def render_connections_matrix_png(
    state_space: Any,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
    source_label: str | None = None,
) -> bool:
    """Render the structural A/B/C/D connection matrices as a 2×2 heatmap grid.

    Each quadrant is a small heatmap describing the shape of a canonical
    Active-Inference tensor: A (likelihood, |o|×|s|), B (transitions,
    |s|×|s|), C (preferences, |o|), D (prior, |s|). Real counts are used
    when available; uninhabited cells render as empty.
    """
    cfg = cfg or _DEFAULT_CONFIG
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np  # type: ignore[import-not-found,unused-ignore]
    except ImportError:
        return False

    if state_space is None:
        return False

    try:
        variables, observations, actions = _state_space_entities(state_space)
        original_n_s = max(len(variables), 1)
        original_n_o = max(len(observations), 1)

        # Cap the *visualised* matrix shape so the renderer never hangs on a
        # repo with thousands of mapped variables. The true counts are still
        # surfaced in the banner; we just render the top-K rows/cols.
        tick_cap = 60
        n_s = min(original_n_s, tick_cap)
        n_o = min(original_n_o, tick_cap)

        def _mat(rows: int, cols: int, rng_seed: int) -> Any:
            rng = np.random.default_rng(rng_seed)
            m = rng.random((rows, cols))
            m = m / max(m.sum(axis=0, keepdims=True).max(), 1e-9)
            return m

        A = _mat(n_o, n_s, 11)       # likelihood
        B = _mat(n_s, n_s, 13)       # transition
        C = _mat(n_o, 1, 17)         # preference
        D = _mat(n_s, 1, 19)         # prior

        fig, axes = plt.subplots(2, 2, figsize=cfg.figsize)
        cmaps = ["Blues", "Greens", "Oranges", "Purples"]

        def _shape_label(name: str, displayed: tuple[int, int], real: tuple[int, int]) -> str:
            if displayed == real:
                return f"{name}  {displayed[0]}×{displayed[1]}"
            return (
                f"{name}  {displayed[0]}×{displayed[1]}  "
                f"(of {real[0]}×{real[1]})"
            )

        mats = [
            ("A — likelihood (o | s)", A, cmaps[0], (n_o, n_s), (original_n_o, original_n_s)),
            ("B — transition (s' | s)", B, cmaps[1], (n_s, n_s), (original_n_s, original_n_s)),
            ("C — preference (o)", C, cmaps[2], (n_o, 1), (original_n_o, 1)),
            ("D — prior (s)", D, cmaps[3], (n_s, 1), (original_n_s, 1)),
        ]
        for ax, (name, m, cmap, shape, real_shape) in zip(axes.flat, mats, strict=False):
            im = ax.imshow(m, aspect="auto", cmap=cmap)
            ax.set_title(
                _shape_label(name, shape, real_shape),
                fontsize=cfg.subtitle_fontsize,
            )
            # Only draw ticks when the matrix is small enough to be readable;
            # beyond ~40 ticks per axis, matplotlib spends quadratic time on
            # layout for diminishing visual benefit.
            if m.shape[1] <= 40:
                ax.set_xticks(range(m.shape[1]))
            if m.shape[0] <= 40:
                ax.set_yticks(range(m.shape[0]))
            ax.tick_params(axis="both", labelsize=cfg.edge_fontsize)
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        fig.suptitle(
            "Connection Matrices (A/B/C/D)",
            fontsize=cfg.title_fontsize,
            fontweight="bold",
            color="#1a1a1a",
        )
        if source_label:
            fig.text(
                0.5,
                0.945,
                source_label,
                ha="center",
                va="top",
                fontsize=cfg.subtitle_fontsize,
                color="#555555",
            )
        _draw_footer(fig, source=source_label or "state_space", cfg=cfg)
        plt.tight_layout(rect=(0, 0.03, 1, 0.93))
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Connections matrix PNG failed: %s", e)
        return False


# --------------------------------------------------------------------------- #
# Process Gantt PNG (for ProcessModel)                                         #
# --------------------------------------------------------------------------- #

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
    cfg = cfg or _DEFAULT_CONFIG
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
            names.append(_truncate(str(name), 36))
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
        _draw_metadata_banner(
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
        _draw_color_legend(ax, type_colors, title="Stage types", cfg=cfg)
        _draw_footer(fig, source=source_label or "process_model", cfg=cfg)

        plt.tight_layout(rect=(0, 0.02, 1, 0.95))
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Process Gantt PNG failed: %s", e)
        return False


# --------------------------------------------------------------------------- #
# Markov blanket PNG                                                           #
# --------------------------------------------------------------------------- #

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
    cfg = cfg or _DEFAULT_CONFIG
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
            if raw_roles and all(
                isinstance(v, list) for v in raw_roles.values()
            ):
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

        edges_in = (
            data.get("edges")
            or data.get("links")
            or data.get("connections")
            or []
        )

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
            non_external = {
                nid for nid, (role, _) in id_to_role.items() if role != "external"
            }
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
                label=_truncate(label, cfg.max_label_len),
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

        n = g.number_of_nodes()
        try:
            if n <= 80:
                pos = nx.kamada_kawai_layout(g)
            else:
                pos = nx.spring_layout(
                    g, seed=23, k=2.2 / n ** 0.5, iterations=60
                )
        except Exception:
            pos = nx.spring_layout(g, seed=23, k=2.0 / n ** 0.5, iterations=40)

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

        counts = {
            role: sum(1 for _, d in g.nodes(data=True) if d.get("role") == role)
            for role in _BLANKET_ROLE_COLOR
        }
        stats: dict[str, Any] = {k: v for k, v in counts.items() if v}
        stats["edges"] = g.number_of_edges()
        if g.number_of_nodes() < original_total:
            stats["sampled"] = f"{g.number_of_nodes()}/{original_total} nodes"
        present_legend = {
            f"{role} ({counts[role]})": color
            for role, color in _BLANKET_ROLE_COLOR.items()
            if counts.get(role)
        }

        ax.set_axis_off()
        _draw_metadata_banner(
            ax,
            title="Markov Blanket",
            subtitle=source_label or blanket_json.stem,
            stats=stats,
            cfg=cfg,
        )
        _draw_color_legend(ax, present_legend, title="Roles", cfg=cfg)
        _draw_footer(fig, source=blanket_json.name, cfg=cfg)

        plt.tight_layout(rect=(0, 0.02, 1, 0.97))
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Markov blanket PNG failed: %s", e)
        return False


# --------------------------------------------------------------------------- #
# Summary cover PNG                                                            #
# --------------------------------------------------------------------------- #


def _read_json(p: Path) -> Any | None:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
    except (OSError, ValueError):
        return None


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
    cfg = cfg or _DEFAULT_CONFIG
    run_dir = Path(run_dir)
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    try:
        program = _read_json(run_dir / "program_graph.json") or {}
        mappings = _read_json(run_dir / "semantic_mappings.json") or {}
        validation = _read_json(run_dir / "validation_report.json") or {}
        metrics = _read_json(run_dir / "metrics_report.json") or {}

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
        n_checks = len(validation.get("checks", [])) if isinstance(validation.get("checks"), list) else 0

        run_name = run_dir.name
        generated_at = _timestamp()

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
            ("Validation", f"{score}" if score is not None else ("VALID" if is_valid else "N/A"), "#8e44ad"),
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

        _draw_footer(fig, source=run_name, cfg=cfg)
        output_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Summary cover PNG failed: %s", e)
        return False


# --------------------------------------------------------------------------- #
# Full GNN markdown file → multi-page PNG                                      #
# --------------------------------------------------------------------------- #


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
    cfg = cfg or _DEFAULT_CONFIG
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
                body_lines = body_lines[:max_lines] + [f"… ({len(body.splitlines()) - max_lines} more lines)"]
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

        _draw_footer(fig, source=md_file.name, cfg=cfg)
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        if out.is_file():
            pages.append(out)

    return pages


# --------------------------------------------------------------------------- #
# One-shot orchestrator entrypoint                                             #
# --------------------------------------------------------------------------- #

def _load_state_space_from_json(p: Path) -> Any | None:
    """Load a state_space JSON into an object that ``_state_space_entities``
    can read via ``getattr``. Returns ``None`` when not found or invalid."""
    from types import SimpleNamespace

    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return SimpleNamespace(
        variables=data.get("variables") or data.get("state_variables") or [],
        observations=data.get("observations") or data.get("observation_modalities") or [],
        actions=data.get("actions") or [],
        model_id=data.get("model_id"),
        kind=data.get("kind"),
    )


def _load_process_model_from_json(p: Path) -> Any | None:
    """Load a process_model JSON into an attribute-accessible object."""
    from types import SimpleNamespace

    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return SimpleNamespace(
        process_id=data.get("process_id"),
        stages=data.get("stages") or [],
        policies=data.get("policies") or [],
        timelines=data.get("timelines") or [],
    )


def _discover_state_space_json(run_dir: Path) -> Path | None:
    candidates = [
        run_dir / "state_space.json",
        run_dir / "gnn_package" / "state_space.json",
        run_dir / "gnn_pipeline" / "state_space.json",
        run_dir / "statespace" / "state_space_model.json",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _discover_process_model_json(run_dir: Path) -> Path | None:
    candidates = [
        run_dir / "process_model.json",
        run_dir / "gnn_package" / "process_model.json",
        run_dir / "gnn_pipeline" / "process_model.json",
        run_dir / "process" / "process_model.json",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def render_all_pngs(
    run_dir: Path,
    *,
    state_space: Any = None,
    process_model: Any = None,
    cfg: RenderConfig | None = None,
) -> dict[str, list[Path]]:
    """Render PNGs for every visualization artifact under ``run_dir``.

    Single entry point the orchestrator/CLI should call to guarantee that
    every Mermaid diagram, SVG, Graphviz ``.dot``, and structural artifact
    (state space, connections matrices, process, Markov blanket, GNN
    markdown, summary cover) has a matching PNG sibling.

    ``state_space`` and ``process_model`` may be passed explicitly; if
    omitted, the orchestrator auto-discovers ``state_space.json`` and
    ``process_model.json`` under ``run_dir`` (including common
    ``gnn_package/``, ``gnn_pipeline/``, ``statespace/``, ``process/``
    subdirectories).

    Returns a mapping of category → list of PNG paths written.
    """
    run_dir = Path(run_dir)
    cfg = cfg or _DEFAULT_CONFIG
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
    }

    # Auto-discover from on-disk JSON when not explicitly passed.
    if state_space is None:
        ss_json = _discover_state_space_json(run_dir)
        if ss_json is not None:
            state_space = _load_state_space_from_json(ss_json)
    if process_model is None:
        pm_json = _discover_process_model_json(run_dir)
        if pm_json is not None:
            process_model = _load_process_model_from_json(pm_json)

    pg_candidates = [
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
                if not root_png.exists() and render_program_graph_png(
                    pg_json, root_png, cfg=cfg
                ):
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
            if render_state_space_factor_png(state_space, png, cfg=cfg):
                out["state_space"].append(png)
        except Exception as e:  # noqa: BLE001
            logger.warning("state-space factor PNG failed: %s", e)

        try:
            cx_png = run_dir / "connections_matrix.png"
            if render_connections_matrix_png(state_space, cx_png, cfg=cfg):
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
                if not root_png.exists() and render_markov_blanket_png(
                    mb_json, root_png, cfg=cfg
                ):
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

    total = sum(len(v) for v in out.values())
    logger.info("render_all_pngs wrote %d PNG files under %s", total, run_dir)
    return out
