from __future__ import annotations

import json
import logging
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from cogant.viz.png.config import (
    DEFAULT_CONFIG,
    RenderConfig,
    draw_footer,
    draw_metadata_banner,
    sha256_file,
    truncate,
    write_figure_sidecar,
)

logger = logging.getLogger(__name__)
def program_graph_dict_to_networkx(graph: dict[str, Any]) -> Any:
    """Build a NetworkX MultiDiGraph from exported ``program_graph.json`` structure.

    Program graphs may contain parallel edges between the same source and
    target with different edge kinds. A ``DiGraph`` would collapse those edges
    and under-report displayed counts in publication sidecars.
    """
    import networkx as nx

    g = nx.MultiDiGraph()
    nodes = graph.get("nodes") or {}
    if isinstance(nodes, list):
        for n in nodes:
            nid = n.get("id")
            if nid:
                g.add_node(
                    nid,
                    label=n.get("qualified_name") or n.get("name", nid),
                    name=n.get("name", nid),
                    kind=str(n.get("kind", "")),
                    path=n.get("path"),
                    metadata=n.get("metadata") or {},
                )
    elif isinstance(nodes, dict):
        for nid, n in nodes.items():
            if isinstance(n, dict):
                g.add_node(
                    nid,
                    label=n.get("qualified_name") or n.get("name", nid),
                    name=n.get("name", nid),
                    kind=str(n.get("kind", "")),
                    path=n.get("path"),
                    metadata=n.get("metadata") or {},
                )

    edges = graph.get("edges") or {}
    if isinstance(edges, list):
        for e in edges:
            s = e.get("source") or e.get("source_id")
            t = e.get("target") or e.get("target_id")
            if s and t:
                g.add_edge(s, t, kind=str(e.get("kind", "")), id=e.get("id"))
    elif isinstance(edges, dict):
        for e in edges.values():
            if isinstance(e, dict):
                s = e.get("source") or e.get("source_id")
                t = e.get("target") or e.get("target_id")
                if s and t:
                    g.add_edge(s, t, kind=str(e.get("kind", "")), id=e.get("id"))
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

_EDGE_COLORS = {
    "contains": "#496A9D",
    "inherits": "#6D5BA6",
    "calls": "#B85042",
    "imports": "#576574",
    "reads": "#2E8B57",
    "writes": "#B7791F",
    "data_flow": "#087E8B",
    "control_flow": "#C8553D",
    "": "#7A869A",
}

_ROLE_OUTLINES = {
    "hidden_state": "#6F42C1",
    "state": "#6F42C1",
    "observation": "#198754",
    "sensory_state": "#198754",
    "action": "#D95F02",
    "policy": "#C83E4D",
    "preference": "#0077B6",
    "parameter": "#5F6F52",
    "constraint": "#7C2D12",
    "likelihood": "#0E7490",
    "prior": "#4338CA",
}


def _edge_color(kind: str) -> str:
    kind = (kind or "").lower()
    if kind in _EDGE_COLORS:
        return _EDGE_COLORS[kind]
    for key, color in _EDGE_COLORS.items():
        if key and key in kind:
            return color
    return _EDGE_COLORS[""]


def _edge_style(kind: str) -> str:
    kind = (kind or "").lower()
    if "read" in kind:
        return "dashed"
    if "write" in kind:
        return "dashdot"
    if "import" in kind:
        return "dotted"
    return "solid"


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


def _build_edge_legend(g: Any) -> dict[str, str]:
    kinds: dict[str, str] = {}
    for _, _, data in g.edges(data=True):
        kind = (data.get("kind") or "").lower()
        display = kind or "edge"
        if display not in kinds:
            kinds[display] = _edge_color(kind)
    return kinds


def _build_role_legend(g: Any) -> dict[str, str]:
    roles: dict[str, str] = {}
    for _, data in g.nodes(data=True):
        role = (data.get("semantic_role") or "").lower()
        if role:
            roles[role] = _ROLE_OUTLINES.get(role, "#111111")
    return roles


def _discover_mapping_artifact(
    program_graph_json: Path, explicit: Path | None = None
) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_file() else None
    candidates = [
        program_graph_json.parent / "rule_evidence_trace.json",
        program_graph_json.parent / "semantic_mappings.json",
        program_graph_json.parent.parent / "data" / "rule_evidence_trace.json",
        program_graph_json.parent.parent / "data" / "semantic_mappings.json",
        program_graph_json.parent.parent / "rule_evidence_trace.json",
        program_graph_json.parent.parent / "semantic_mappings.json",
        program_graph_json.parent.parent / "roundtrip" / "rule_evidence_trace.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _iter_mapping_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("mappings", "semantic_mappings", "rows", "evidence", "trace"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if "original" in payload and isinstance(payload["original"], dict):
        return _iter_mapping_records(payload["original"])
    return []


def _load_semantic_roles(mapping_artifact: Path | None) -> tuple[dict[str, str], dict[str, int]]:
    if mapping_artifact is None:
        return {}, {}
    try:
        payload = json.loads(mapping_artifact.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, {}
    roles: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for record in _iter_mapping_records(payload):
        role = str(record.get("kind") or record.get("mapping_kind") or "").lower()
        if not role:
            continue
        node_ids = record.get("matched_node_ids") or record.get("graph_fragment_node_ids") or []
        match = record.get("match")
        if isinstance(match, dict) and match.get("node_id"):
            node_ids = [*node_ids, match["node_id"]]
        for node_id in node_ids:
            if node_id and node_id not in roles:
                roles[str(node_id)] = role
        counts[role] += 1
    return roles, dict(counts)


def _program_graph_layout(g: Any) -> dict[str, tuple[float, float]]:
    """Deterministic hierarchy-first layout for code graphs."""
    contains_parents: dict[str, list[str]] = {node: [] for node in g.nodes()}
    for source, target, data in g.edges(data=True):
        if "contain" in str(data.get("kind", "")).lower():
            contains_parents.setdefault(target, []).append(source)
            contains_parents.setdefault(source, contains_parents.get(source, []))

    roots = sorted(
        [node for node, parents in contains_parents.items() if not parents],
        key=lambda n: (str(g.nodes[n].get("kind", "")), str(g.nodes[n].get("label", n)), str(n)),
    )
    if not roots:
        roots = sorted(g.nodes(), key=str)

    depth: dict[str, int] = {}
    queue: list[tuple[str, int]] = [(node, 0) for node in roots]
    while queue:
        node, level = queue.pop(0)
        if node in depth and depth[node] <= level:
            continue
        depth[node] = level
        children = sorted(
            [
                target
                for _, target, data in g.out_edges(node, data=True)
                if "contain" in str(data.get("kind", "")).lower()
            ],
            key=lambda n: (
                str(g.nodes[n].get("kind", "")),
                str(g.nodes[n].get("label", n)),
                str(n),
            ),
        )
        queue.extend((child, level + 1) for child in children)

    fallback_depth = (max(depth.values()) + 1) if depth else 0
    for node in g.nodes():
        depth.setdefault(node, fallback_depth)

    layers: dict[int, list[str]] = {}
    for node, level in depth.items():
        layers.setdefault(level, []).append(node)
    for nodes in layers.values():
        nodes.sort(
            key=lambda n: (str(g.nodes[n].get("kind", "")), str(g.nodes[n].get("label", n)), str(n))
        )

    positions: dict[str, tuple[float, float]] = {}
    for level in sorted(layers):
        nodes = layers[level]
        width = max(len(nodes) - 1, 1)
        for index, node in enumerate(nodes):
            x = (index - width / 2) * 2.2
            y = -level * 2.0
            positions[node] = (x, y)
    return positions


def _graphviz_program_graph_layout(g: Any) -> dict[str, tuple[float, float]] | None:
    """Return a DOT layered layout when Graphviz and pydot are available."""

    if not shutil.which("dot"):
        return None
    try:
        import networkx as nx

        positions = nx.nx_pydot.graphviz_layout(g, prog="dot")
    except Exception as exc:
        logger.debug("Graphviz DOT layout unavailable for program graph: %s", exc)
        return None
    if not positions:
        return None
    return {str(node): (float(x), float(y)) for node, (x, y) in positions.items()}


def _program_graph_clutter_score(n_nodes: int, n_edges: int, figsize: tuple[float, float]) -> float:
    """Lightweight clutter proxy for manuscript visual QA sidecars."""

    canvas_area = max(figsize[0] * figsize[1], 1.0)
    edge_pressure = n_edges / max(n_nodes, 1) / 8.0
    label_pressure = n_nodes / canvas_area / 4.0
    density_pressure = n_edges / max(n_nodes * max(n_nodes - 1, 1), 1) * 2.0
    return round(min(1.0, edge_pressure + label_pressure + density_pressure), 4)


def _draw_program_graph_legends(ax: Any, g: Any, cfg: RenderConfig) -> None:
    if not cfg.show_legend:
        return
    import matplotlib.lines as mlines
    import matplotlib.patches as mpatches

    kind_counts = Counter((data.get("kind") or "other").lower() for _, data in g.nodes(data=True))
    edge_counts = Counter((data.get("kind") or "edge").lower() for _, _, data in g.edges(data=True))
    role_counts = Counter(
        (data.get("semantic_role") or "").lower()
        for _, data in g.nodes(data=True)
        if data.get("semantic_role")
    )

    kind_handles = [
        mpatches.Patch(color=_kind_color(kind), label=f"{kind} ({count})")
        for kind, count in kind_counts.most_common(7)
    ]
    if kind_handles:
        legend = ax.legend(
            handles=kind_handles,
            title="Node kind",
            loc="upper left",
            fontsize=cfg.banner_fontsize,
            title_fontsize=cfg.banner_fontsize,
            framealpha=0.94,
        )
        ax.add_artist(legend)

    edge_handles = [
        mlines.Line2D(
            [],
            [],
            color=_edge_color(kind),
            linestyle=_edge_style(kind),
            linewidth=2.2,
            label=f"{kind} ({count})",
        )
        for kind, count in edge_counts.most_common(7)
    ]
    if edge_handles:
        legend = ax.legend(
            handles=edge_handles,
            title="Edge kind",
            loc="upper right",
            fontsize=cfg.banner_fontsize,
            title_fontsize=cfg.banner_fontsize,
            framealpha=0.94,
        )
        ax.add_artist(legend)

    role_handles = [
        mlines.Line2D(
            [],
            [],
            color="white",
            marker="o",
            markeredgecolor=_ROLE_OUTLINES.get(role, "#111111"),
            markerfacecolor="white",
            markeredgewidth=2.4,
            markersize=9,
            linestyle="None",
            label=f"{role} ({count})",
        )
        for role, count in role_counts.most_common(6)
    ]
    if role_handles:
        legend = ax.legend(
            handles=role_handles,
            title="Semantic role outline",
            loc="lower left",
            fontsize=cfg.banner_fontsize,
            title_fontsize=cfg.banner_fontsize,
            framealpha=0.94,
        )
        ax.add_artist(legend)


def render_program_graph_png(
    program_graph_json: Path,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: int | None = None,
    source_label: str | None = None,
    semantic_mappings_json: Path | None = None,
) -> bool:
    """Render ``program_graph.json`` to an informative PNG.

    The rendering includes:

    * A deterministic hierarchy-first layout for containment-heavy code graphs.
    * Node-kind fill colors, edge-kind color/style encodings, and role outlines
      when a semantic mapping or rule-evidence trace is available.
    * A title banner with node/edge counts and kind diversity.
    * Figure sidecar metadata tying the PNG back to source artifacts.
    """
    cfg = cfg or DEFAULT_CONFIG
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

    mapping_artifact = _discover_mapping_artifact(program_graph_json, semantic_mappings_json)
    role_by_node, role_counts = _load_semantic_roles(mapping_artifact)
    for node_id, role in role_by_node.items():
        if node_id in g:
            g.nodes[node_id]["semantic_role"] = role

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
    layout_name = "graphviz dot layered layout"
    layout_seed: int | None = None
    pos = _graphviz_program_graph_layout(g)
    if pos is None:
        layout_name = "deterministic containment layout"
        try:
            pos = _program_graph_layout(g)
        except Exception:
            layout_name = "seeded spring fallback"
            layout_seed = 42
            pos = nx.spring_layout(
                g, seed=layout_seed, k=2.2 / max(n_nodes, 1) ** 0.5, iterations=80
            )

    labels = {
        n: truncate(g.nodes[n].get("name") or g.nodes[n].get("label", n) or n, cfg.max_label_len)
        for n in g.nodes()
    }
    edge_labels = {}
    if n_edges <= cfg.max_edge_labels:
        edge_labels = {
            (u, v): truncate(str(d.get("kind", "")), 14)
            for u, v, d in g.edges(data=True)
            if d.get("kind")
        }

    fig, ax = plt.subplots(figsize=figsize)
    for role in sorted({(g.nodes[n].get("semantic_role") or "") for n in g.nodes()}):
        group = [n for n in g.nodes() if (g.nodes[n].get("semantic_role") or "") == role]
        group_colors = [_kind_color(g.nodes[n].get("kind", "")) for n in group]
        outline = _ROLE_OUTLINES.get(str(role).lower(), "#222222") if role else "#222222"
        linewidth = 2.8 if role else 1.2
        nx.draw_networkx_nodes(
            g,
            pos,
            nodelist=group,
            node_size=cfg.node_size,
            node_color=group_colors,
            alpha=0.95,
            edgecolors=outline,
            linewidths=linewidth,
            ax=ax,
        )

    for edge_kind in sorted({(d.get("kind") or "") for _, _, d in g.edges(data=True)}):
        edge_list = [(u, v) for u, v, d in g.edges(data=True) if (d.get("kind") or "") == edge_kind]
        nx.draw_networkx_edges(
            g,
            pos,
            edgelist=edge_list,
            edge_color=_edge_color(str(edge_kind)),
            style=_edge_style(str(edge_kind)),
            arrows=True,
            arrowsize=16,
            width=1.5,
            alpha=0.76,
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
    kind_counts = Counter((d.get("kind") or "other").lower() for _, d in g.nodes(data=True))
    edge_kind_counts = Counter((d.get("kind") or "edge").lower() for _, _, d in g.edges(data=True))
    top_kinds = sorted(kind_counts.items(), key=lambda x: -x[1])[:5]
    kind_summary = ", ".join(f"{k}×{v}" for k, v in top_kinds)
    pg_stats: dict[str, Any] = {
        "nodes": n_nodes,
        "edges": n_edges,
        "kinds": kind_summary or "n/a",
        "roles": sum(1 for _, d in g.nodes(data=True) if d.get("semantic_role")),
    }
    if n_nodes < original_n_nodes:
        pg_stats["sampled"] = f"{n_nodes}/{original_n_nodes} nodes"
    draw_metadata_banner(
        ax,
        title="Program Graph",
        subtitle=f"{source_label or program_graph_json.parent.name}",
        stats=pg_stats,
        cfg=cfg,
    )
    _draw_program_graph_legends(ax, g, cfg)
    draw_footer(fig, source=str(program_graph_json.name), cfg=cfg)

    plt.tight_layout(rect=(0, 0.02, 1, 0.97))
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    write_figure_sidecar(
        output_png,
        {
            "renderer": "cogant.viz.png_export.render_program_graph_png",
            "method": (
                "Deterministic containment-first graph layout with node-kind fill colors, "
                "edge-kind line encodings, semantic-role outlines when rule evidence is present, "
                "and downsampling for large graphs."
            ),
            "source_artifact": str(program_graph_json),
            "source_sha256": sha256_file(program_graph_json),
            "semantic_evidence_artifact": str(mapping_artifact) if mapping_artifact else None,
            "semantic_evidence_sha256": sha256_file(mapping_artifact)
            if mapping_artifact
            else None,
            "layout": layout_name,
            "layout_method": layout_name,
            "layout_seed": layout_seed,
            "source_artifact_digest": sha256_file(program_graph_json),
            "displayed_counts": {
                "nodes": n_nodes,
                "edges": n_edges,
                "original_nodes": original_n_nodes,
                "original_edges": original_n_edges,
                "semantic_role_nodes": sum(
                    1 for _, d in g.nodes(data=True) if d.get("semantic_role")
                ),
            },
            "displayed_count_checks": {
                "source_nodes": original_n_nodes,
                "source_edges": original_n_edges,
                "displayed_nodes": n_nodes,
                "displayed_edges": n_edges,
                "nodes_match_source": n_nodes == original_n_nodes,
                "edges_match_source": n_edges == original_n_edges,
                "downsampled": n_nodes != original_n_nodes or n_edges != original_n_edges,
            },
            "node_kind_counts": dict(sorted(kind_counts.items())),
            "edge_kind_counts": dict(sorted(edge_kind_counts.items())),
            "semantic_role_counts": dict(sorted(role_counts.items())),
            "legend_present": bool(cfg.show_legend),
            "visual_complexity": {
                "clutter_score": _program_graph_clutter_score(n_nodes, n_edges, figsize),
                "node_label_policy": f"labels truncated to {cfg.max_label_len} characters",
                "edge_label_policy": (
                    f"edge labels shown when displayed edge count <= {cfg.max_edge_labels}"
                ),
                "sampled": n_nodes != original_n_nodes or n_edges != original_n_edges,
            },
            "panel_metadata": {
                "node_kind_legend": sorted(kind_counts.keys()),
                "edge_kind_legend": sorted(edge_kind_counts.keys()),
                "semantic_role_legend": sorted(role_counts.keys()),
            },
            "limitations": (
                "This figure audits extracted static graph structure. It does not prove that "
                "all runtime behavior, dynamic dispatch, or external effects were recovered."
            ),
            "known_limitations": (
                "This figure audits extracted static graph structure. It does not prove that "
                "all runtime behavior, dynamic dispatch, or external effects were recovered."
            ),
        },
        cfg,
    )
    return True


