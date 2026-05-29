from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from cogant.viz.png.config import (
    DEFAULT_CONFIG,
    RenderConfig,
    downsample_graph,
    draw_color_legend,
    draw_footer,
    draw_metadata_banner,
    truncate,
)

logger = logging.getLogger(__name__)


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
    allow_native_renderer: bool = True,
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
    cfg = cfg or DEFAULT_CONFIG
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
                "mmdc failed for %s: %s; trying native renderer",
                mermaid_file.name,
                str(err)[:300],
            )

    if not allow_native_renderer:
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
    cfg = cfg or DEFAULT_CONFIG
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
        if (
            ln.startswith("note ")
            or ln.lower().startswith("note right of")
            or ln.lower().startswith("note left of")
        ):
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
    lines = [
        line.strip().lower()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("%%")
    ]
    head = (lines or [""])[0]
    if head.startswith(("classdiagram",)):
        return "class"
    if head.startswith(("statediagram", "state-diagram", "statediagram-v2")):
        return "state"
    if head.startswith(("sequencediagram",)):
        return "sequence"
    if head.startswith(("gantt",)):
        return "gantt"
    if head.startswith(("pie",)):
        return "pie"
    if head.startswith(("xychart",)):
        return "xychart"
    if head.startswith(("erdiagram",)):
        return "er"
    return "graph"


def _parse_mermaid_pie(text: str) -> tuple[str | None, list[tuple[str, float]]]:
    """Parse the compact Mermaid pie syntax used by batch dashboards."""

    title: str | None = None
    rows: list[tuple[str, float]] = []
    row_re = re.compile(r'^\s*"([^"]+)"\s*:\s*(-?\d+(?:\.\d+)?)\s*$')
    for raw in text.splitlines():
        ln = raw.strip()
        low = ln.lower()
        if not ln or ln.startswith("%%"):
            continue
        if low.startswith("pie title"):
            title = ln[len("pie title") :].strip() or None
            continue
        if low == "pie":
            continue
        match = row_re.match(ln)
        if match:
            rows.append((match.group(1), max(float(match.group(2)), 0.0)))
    return title, rows


def _parse_mermaid_xychart(text: str) -> tuple[str | None, list[str], list[float]]:
    """Parse the compact Mermaid xychart-beta syntax used by batch dashboards."""

    title: str | None = None
    labels: list[str] = []
    values: list[float] = []
    for raw in text.splitlines():
        ln = raw.strip()
        low = ln.lower()
        if not ln or ln.startswith("%%"):
            continue
        if low.startswith("title "):
            title = ln[len("title ") :].strip().strip('"') or None
            continue
        if low.startswith("x-axis"):
            labels = re.findall(r'"([^"]+)"', ln)
            continue
        if low.startswith("bar"):
            match = re.search(r"\[([^\]]*)\]", ln)
            if match:
                values = [float(part.strip()) for part in match.group(1).split(",") if part.strip()]
    return title, labels, values


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


def _render_pie_png(
    rows: list[tuple[str, float]],
    output_png: Path,
    title: str | None,
    *,
    cfg: RenderConfig,
    source_label: str | None = None,
) -> bool:
    """Render a Mermaid pie chart without requiring browser-backed mmdc."""

    if not rows:
        return False
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    labels = [label for label, _ in rows]
    values = [value for _, value in rows]
    if sum(values) <= 0:
        values = [1.0 for _ in rows]
    fig, ax = plt.subplots(figsize=(9, 7), dpi=cfg.dpi)
    colors = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0f766e", "#c2410c"]
    ax.pie(
        values,
        labels=labels,
        autopct=lambda pct: f"{pct:.0f}%" if pct >= 5 else "",
        startangle=90,
        colors=[colors[i % len(colors)] for i in range(len(values))],
        textprops={"fontsize": 11, "color": "#1f2937"},
    )
    ax.axis("equal")
    draw_metadata_banner(
        ax,
        title=title or "Mermaid Pie Chart",
        stats={"total": int(sum(value for _, value in rows)), "slices": len(rows)},
        cfg=cfg,
    )
    draw_footer(fig, source=source_label, cfg=cfg)
    fig.tight_layout(rect=(0.02, 0.04, 0.98, 0.92))
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_png.exists()


def _render_xychart_png(
    labels: list[str],
    values: list[float],
    output_png: Path,
    title: str | None,
    *,
    cfg: RenderConfig,
    source_label: str | None = None,
) -> bool:
    """Render a Mermaid xychart-beta bar chart without browser-backed mmdc."""

    if not labels or not values:
        return False
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    n = min(len(labels), len(values))
    labels = labels[:n]
    values = values[:n]
    width = max(8.0, min(18.0, 1.2 * n + 4.0))
    fig, ax = plt.subplots(figsize=(width, 7), dpi=cfg.dpi)
    ax.bar(range(n), values, color="#2563eb")
    ax.set_xticks(range(n))
    ax.set_xticklabels([truncate(label, 28) for label in labels], rotation=30, ha="right")
    ax.set_ylabel("value")
    ax.grid(axis="y", alpha=0.25)
    for idx, value in enumerate(values):
        ax.text(idx, value, f"{value:g}", ha="center", va="bottom", fontsize=9)
    draw_metadata_banner(
        ax,
        title=title or "Mermaid Bar Chart",
        stats={"bars": n, "max": f"{max(values):g}"},
        cfg=cfg,
    )
    draw_footer(fig, source=source_label, cfg=cfg)
    fig.tight_layout(rect=(0.03, 0.07, 0.98, 0.92))
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_png.exists()


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
    cfg = cfg or DEFAULT_CONFIG
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
            return _render_gantt_png(tasks, output_png, title, cfg=cfg, source_label=source_label)

        if kind == "pie":
            pie_title, rows = _parse_mermaid_pie(text)
            if not rows:
                return False
            return _render_pie_png(
                rows,
                output_png,
                title or pie_title,
                cfg=cfg,
                source_label=source_label,
            )

        if kind == "xychart":
            chart_title, labels, values = _parse_mermaid_xychart(text)
            if not labels or not values:
                return False
            return _render_xychart_png(
                labels,
                values,
                output_png,
                title or chart_title,
                cfg=cfg,
                source_label=source_label,
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
        nodes, edges, sample_stats = downsample_graph(
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
            pos = (
                nx.kamada_kawai_layout(g)
                if n <= 80
                else nx.spring_layout(g, seed=17, k=2.4 / (n**0.5), iterations=200)
            )
        except Exception:
            pos = nx.spring_layout(g, seed=17, k=2.0 / (n**0.5), iterations=120)

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
        node_labels = {
            n_: truncate(g.nodes[n_].get("label", n_) or n_, cfg.max_label_len) for n_ in g.nodes()
        }
        nx.draw_networkx_labels(
            g,
            pos,
            labels=node_labels,
            font_size=cfg.node_fontsize,
            font_color="white",
            font_weight="bold",
            ax=ax,
        )
        edge_labels = {
            (u, v): truncate(d.get("label") or "", 14)
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
                bbox={
                    "boxstyle": "round,pad=0.2",
                    "facecolor": cfg.edge_label_bg,
                    "edgecolor": "none",
                },
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
        draw_metadata_banner(
            ax,
            title=ttl,
            subtitle=source_label or None,
            stats=stats,
            cfg=cfg,
        )
        if clusters:
            draw_color_legend(
                ax,
                dict.fromkeys(list(clusters.values())[:6], node_color),
                title="Clusters",
                cfg=cfg,
            )
        draw_footer(fig, source=source_label or title, cfg=cfg)

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
    cfg: RenderConfig = DEFAULT_CONFIG,
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
            truncate(p, cfg.max_label_len),
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
                arrowprops={
                    "arrowstyle": "->",
                    "color": "#8e44ad",
                    "lw": 1.6,
                    "connectionstyle": "arc3,rad=-0.5",
                },
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
                truncate(msg, 60),
                ha="center",
                va="bottom",
                fontsize=cfg.edge_fontsize,
                bbox={
                    "boxstyle": "round,pad=0.25",
                    "facecolor": cfg.edge_label_bg,
                    "edgecolor": "none",
                },
            )

    ax.set_xlim(-0.7, max(len(participants) - 0.3, 1.0))
    ax.set_ylim(-0.5, len(messages) + 2.6)
    ax.set_axis_off()
    seq_stats: dict[str, Any] = {
        "participants": len(participants),
        "messages": len(messages),
    }
    if original_participants > len(participants):
        seq_stats["sampled_participants"] = f"{len(participants)}/{original_participants}"
    if original_messages > len(messages):
        seq_stats["sampled_messages"] = f"{len(messages)}/{original_messages}"
    draw_metadata_banner(
        ax,
        title=title or "Sequence diagram",
        subtitle=source_label,
        stats=seq_stats,
        cfg=cfg,
    )
    draw_footer(fig, source=source_label or title, cfg=cfg)

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
    cfg: RenderConfig = DEFAULT_CONFIG,
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
            truncate(name, 40),
            ha="center",
            va="center",
            fontsize=cfg.edge_fontsize,
            color="white",
            fontweight="bold",
        )
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels([truncate(t[1], 28) for t in tasks], fontsize=cfg.edge_fontsize)
    ax.invert_yaxis()
    ax.set_xlabel("Step", fontsize=cfg.banner_fontsize + 1)
    ax.grid(axis="x", color="#dddddd", linestyle="--", linewidth=0.6, alpha=0.7)
    draw_metadata_banner(
        ax,
        title=title or "Gantt timeline",
        subtitle=source_label,
        stats={"tasks": len(tasks), "sections": len(sections)},
        cfg=cfg,
    )
    draw_color_legend(ax, sections, title="Sections", cfg=cfg)
    draw_footer(fig, source=source_label or title, cfg=cfg)

    plt.tight_layout(rect=(0, 0.02, 1, 0.95))
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_png.is_file()
