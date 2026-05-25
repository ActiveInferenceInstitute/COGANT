"""
PDF export for COGANT models: program graphs, GNN bundles, matrices, and reports.

Generates publication-quality multi-page PDFs of:
- Program graph visualizations
- GNN bundle summaries
- Active Inference matrices (A/B/C/D)
- Markov blanket partitions
- Pipeline stage analysis and timing
- Roundtrip evaluation reports

All exports use matplotlib's PDF backend for vector output.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Node-kind → fill colour for graph scatter plots
_KIND_COLORS: dict[str, str] = {
    "module": "#4C72B0",
    "class": "#DD8452",
    "function": "#55A868",
    "method": "#C44E52",
    "variable": "#8172B2",
    "endpoint": "#937860",
    "event": "#DA8BC3",
    "parameter": "#8C8C8C",
    "return_value": "#CCB974",
    "data_structure": "#64B5CD",
    "configuration": "#B9B29F",
    "feature_flag": "#E8AF6E",
    "test": "#A2C8EC",
    "assertion": "#CFCFCF",
    "policy": "#7BC8A4",
    "action": "#F7910B",
    "repo": "#1A1A2E",
    "file": "#16213E",
}
_DEFAULT_COLOR = "#AAAAAA"


def _kind_color(kind: str) -> str:
    return _KIND_COLORS.get(str(kind), _DEFAULT_COLOR)


def _node_counts_by_kind(graph: Any) -> dict[str, int]:
    """Return {kind: count} from a ProgramGraph (or dict)."""
    counts: dict[str, int] = {}
    nodes: Any = getattr(graph, "nodes", None) or {}
    if isinstance(nodes, dict):
        for node in nodes.values():
            k = str(getattr(node, "kind", "unknown"))
            counts[k] = counts.get(k, 0) + 1
    return counts


def _role_counts_from_mappings(mappings: Any) -> dict[str, int]:
    """Return {role: count} from a SemanticMappings dict or list."""
    counts: dict[str, int] = {}
    if isinstance(mappings, dict):
        items: Any = mappings.values()
    elif isinstance(mappings, list):
        items = mappings
    else:
        return counts
    for m in items:
        role = str(
            getattr(m, "kind", None) or m.get("kind", "unknown")
            if isinstance(m, dict)
            else "unknown"
        )
        counts[role] = counts.get(role, 0) + 1
    return counts


class PDFExporter:
    """Export COGANT models and results to PDF."""

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Program graph
    # ------------------------------------------------------------------

    def export_program_graph(self, graph: Any, output_path: str) -> str:
        """
        Render a program graph as PDF.

        Generates a full graph visualization with nodes coloured by kind,
        directed edges, and a legend. Uses networkx spring layout.

        Args:
            graph: ProgramGraph (or any object with ``.nodes`` / ``.edges``
                dicts). Also accepts a plain dict with those keys.
            output_path: Path to write PDF file.

        Returns:
            Path to rendered file, or empty string if matplotlib unavailable.
        """
        try:
            import matplotlib.patches as mpatches
            import matplotlib.pyplot as plt
            import networkx as nx
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            logger.warning("matplotlib/networkx not available; skipping PDF export")
            return ""

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            nodes_dict: dict[str, Any] = getattr(graph, "nodes", None) or {}
            edges_dict: dict[str, Any] = getattr(graph, "edges", None) or {}

            # Build networkx DiGraph for layout
            G: Any = nx.DiGraph()
            for nid, node in nodes_dict.items():
                G.add_node(
                    nid,
                    kind=str(getattr(node, "kind", "unknown")),
                    name=str(getattr(node, "name", nid)),
                )
            for edge in edges_dict.values():
                src = getattr(edge, "source_id", None)
                tgt = getattr(edge, "target_id", None)
                if src and tgt:
                    G.add_edge(src, tgt, kind=str(getattr(edge, "kind", "")))

            pos = nx.spring_layout(G, seed=42, k=2.0 / max(len(G), 1) ** 0.5)

            node_colors = [_kind_color(G.nodes[n].get("kind", "")) for n in G.nodes()]
            node_labels = {n: G.nodes[n].get("name", n)[:20] for n in G.nodes()}

            with PdfPages(str(output_file)) as pdf:
                fig, ax = plt.subplots(figsize=(14, 10))

                if G.number_of_nodes() > 0:
                    nx.draw_networkx(
                        G,
                        pos=pos,
                        ax=ax,
                        node_color=node_colors,
                        labels=node_labels,
                        font_size=6,
                        node_size=300,
                        arrows=True,
                        arrowsize=12,
                        edge_color="#AAAAAA",
                        width=0.5,
                        with_labels=True,
                    )
                else:
                    ax.text(0.5, 0.5, "Empty graph", ha="center", va="center", fontsize=14)

                # Legend for top-8 kinds present
                present_kinds = sorted({G.nodes[n].get("kind", "") for n in G.nodes()})[:8]
                handles = [mpatches.Patch(color=_kind_color(k), label=k) for k in present_kinds]
                if handles:
                    ax.legend(handles=handles, loc="lower right", fontsize=7, title="Node kind")

                ax.set_title(
                    f"Program Graph — {G.number_of_nodes()} nodes, {G.number_of_edges()} edges",
                    fontsize=13,
                    weight="bold",
                )
                ax.axis("off")

                # Summary stats page
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

                # Second page: node-kind distribution bar chart
                kind_counts = _node_counts_by_kind(graph)
                if kind_counts:
                    fig2, ax2 = plt.subplots(figsize=(10, 6))
                    kinds = list(kind_counts.keys())
                    counts = [kind_counts[k] for k in kinds]
                    colors = [_kind_color(k) for k in kinds]
                    bars = ax2.barh(kinds, counts, color=colors, edgecolor="white")
                    for bar in bars:
                        w = bar.get_width()
                        ax2.text(
                            w,
                            bar.get_y() + bar.get_height() / 2,
                            f" {int(w)}",
                            va="center",
                            fontsize=9,
                        )
                    ax2.set_xlabel("Count")
                    ax2.set_title("Node Kind Distribution", fontsize=13, weight="bold")
                    ax2.grid(axis="x", alpha=0.3)
                    fig2.tight_layout()
                    pdf.savefig(fig2, bbox_inches="tight")
                    plt.close(fig2)

            logger.info("Exported program graph to %s", output_path)
            return output_path

        except Exception as e:
            logger.error("Error exporting program graph: %s", e)
            return ""

    # ------------------------------------------------------------------
    # GNN bundle
    # ------------------------------------------------------------------

    def export_gnn_bundle(self, bundle: Any, output_path: str) -> str:
        """
        Render a GNN bundle as multi-page PDF.

        Includes bundle metadata, semantic role distribution, and stage
        timing extracted from the bundle's artifact store.

        Args:
            bundle: Bundle object (with ``.artifacts``, ``.metadata``,
                ``.target``) or a plain dict with the same keys.
            output_path: Path to write PDF file.

        Returns:
            Path to rendered file, or empty string if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            logger.warning("matplotlib not available; skipping PDF export")
            return ""

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            meta: dict[str, Any] = getattr(bundle, "metadata", None) or {}
            target: str = str(getattr(bundle, "target", meta.get("target", "unknown")))
            artifacts: dict[str, Any] = getattr(bundle, "artifacts", None) or {}
            stage_results: dict[str, Any] = getattr(bundle, "stage_results", None) or {}

            # Pull semantic mappings for role distribution
            mappings = artifacts.get("_semantic_mappings") or artifacts.get("semantic_mappings")
            role_counts = _role_counts_from_mappings(mappings) if mappings is not None else {}

            # Stage timing from stage_results
            timing: dict[str, float] = {}
            for stage_name, result in stage_results.items():
                if isinstance(result, dict):
                    elapsed = result.get("elapsed_s") or result.get("elapsed") or result.get("time")
                    if elapsed is not None:
                        try:
                            timing[stage_name] = float(elapsed)
                        except (TypeError, ValueError):
                            pass

            with PdfPages(str(output_file)) as pdf:
                # PAGE 1 — Metadata summary
                fig, ax = plt.subplots(figsize=(8.5, 11))
                ax.text(
                    0.5,
                    0.88,
                    "GNN Bundle Report",
                    ha="center",
                    va="center",
                    fontsize=22,
                    weight="bold",
                )
                ax.text(0.5, 0.82, target, ha="center", va="center", fontsize=14, color="#555555")

                lines = []
                if meta.get("version"):
                    lines.append(f"cogant version: {meta['version']}")
                if meta.get("timestamp"):
                    lines.append(f"Generated: {meta['timestamp']}")
                lines.append(f"Stages completed: {len(stage_results)}")
                lines.append(f"Artifacts: {len(artifacts)}")
                if errors := getattr(bundle, "errors", []):
                    lines.append(f"Errors: {len(errors)}")

                ax.text(
                    0.5,
                    0.65,
                    "\n".join(lines),
                    ha="center",
                    va="top",
                    fontsize=11,
                    family="monospace",
                    bbox={
                        "boxstyle": "round,pad=0.5",
                        "facecolor": "#F0F4FF",
                        "edgecolor": "#CCCCCC",
                    },
                )
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis("off")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

                # PAGE 2 — Semantic role distribution pie
                if role_counts:
                    fig2, ax2 = plt.subplots(figsize=(9, 7))
                    roles = list(role_counts.keys())
                    counts = [role_counts[r] for r in roles]
                    colors = plt.cm.Set2(np.linspace(0, 1, len(roles)))
                    wedges, texts, autotexts = ax2.pie(
                        counts,
                        labels=roles,
                        autopct="%1.0f%%",
                        colors=colors,
                        startangle=90,
                        wedgeprops={"width": 0.6},
                    )
                    for t in autotexts:
                        t.set_fontsize(9)
                    ax2.set_title(
                        f"Semantic Role Distribution ({sum(counts)} mappings)",
                        fontsize=13,
                        weight="bold",
                    )
                    fig2.tight_layout()
                    pdf.savefig(fig2, bbox_inches="tight")
                    plt.close(fig2)

                # PAGE 3 — Stage timing
                if timing:
                    fig3, ax3 = plt.subplots(figsize=(10, 6))
                    stages = list(timing.keys())
                    times = list(timing.values())
                    sorted_pairs = sorted(
                        zip(stages, times, strict=False), key=lambda x: x[1], reverse=True
                    )
                    s_stages, s_times = zip(*sorted_pairs, strict=False)
                    ax3.barh(s_stages, s_times, color="steelblue", alpha=0.8)
                    for idx, t in enumerate(s_times):
                        ax3.text(t, idx, f"  {t:.3f}s", va="center", fontsize=9)
                    ax3.set_xlabel("Elapsed (seconds)")
                    ax3.set_title("Stage Timing", fontsize=13, weight="bold")
                    ax3.grid(axis="x", alpha=0.3)
                    fig3.tight_layout()
                    pdf.savefig(fig3, bbox_inches="tight")
                    plt.close(fig3)

            logger.info("Exported GNN bundle to %s", output_path)
            return output_path

        except Exception as e:
            logger.error("Error exporting GNN bundle: %s", e)
            return ""

    # ------------------------------------------------------------------
    # Matrices
    # ------------------------------------------------------------------

    def export_matrices(self, matrices: dict[str, Any], output_path: str) -> str:
        """
        Render A/B/C/D matrices as heatmaps in PDF.

        Creates a multi-page PDF: first page shows all four matrices as a
        2×2 grid; subsequent pages show each matrix individually for detail.

        Args:
            matrices: Dict with keys ``'A'``, ``'B'``, ``'C'``, ``'D'``
                and numeric arrays (or nested lists) as values.
            output_path: Path to write PDF file.

        Returns:
            Path to rendered file, or empty string if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            logger.warning("matplotlib not available; skipping PDF export")
            return ""

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            matrix_names = ["A", "B", "C", "D"]

            def _to_2d(data: Any, name: str) -> Any | None:
                """Coerce data to a 2-D numpy array suitable for imshow."""
                try:
                    arr = np.asarray(data, dtype=float)
                    if arr.ndim == 1:
                        arr = arr.reshape(1, -1)
                    elif arr.ndim == 3:
                        arr = arr[0]  # first action slice for B
                    elif arr.ndim > 3:
                        arr = arr.reshape(arr.shape[0], -1)
                    return arr
                except Exception:
                    return None

            with PdfPages(str(output_file)) as pdf:
                # PAGE 1: 2×2 overview
                fig, axes = plt.subplots(2, 2, figsize=(11, 9))
                for idx, mname in enumerate(matrix_names):
                    ax = axes[idx // 2, idx % 2]
                    data = matrices.get(mname)
                    arr = _to_2d(data, mname) if data is not None else None
                    if arr is not None:
                        im = ax.imshow(
                            arr,
                            cmap="YlOrRd",
                            aspect="auto",
                            origin="lower",
                            interpolation="nearest",
                        )
                        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                        ax.set_title(f"{mname} matrix  {arr.shape}", fontsize=10, weight="bold")
                        ax.set_xlabel("columns")
                        ax.set_ylabel("rows")
                    else:
                        ax.text(
                            0.5,
                            0.5,
                            f"{mname}\n(no data)",
                            ha="center",
                            va="center",
                            fontsize=11,
                            color="#888888",
                        )
                        ax.axis("off")
                fig.suptitle("Active Inference Matrices (A/B/C/D)", fontsize=14, weight="bold")
                fig.tight_layout()
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

                # Subsequent pages: one matrix per page (full-size)
                for mname in matrix_names:
                    data = matrices.get(mname)
                    arr = _to_2d(data, mname) if data is not None else None
                    if arr is None:
                        continue
                    fig2, ax2 = plt.subplots(figsize=(9, 7))
                    im2 = ax2.imshow(
                        arr, cmap="YlOrRd", aspect="auto", origin="lower", interpolation="nearest"
                    )
                    plt.colorbar(im2, ax=ax2)
                    ax2.set_title(
                        f"{mname} matrix — shape {arr.shape}  "
                        f"min={arr.min():.3f}  max={arr.max():.3f}",
                        fontsize=12,
                        weight="bold",
                    )
                    ax2.set_xlabel("Columns")
                    ax2.set_ylabel("Rows")
                    fig2.tight_layout()
                    pdf.savefig(fig2, bbox_inches="tight")
                    plt.close(fig2)

            logger.info("Exported matrices to %s", output_path)
            return output_path

        except Exception as e:
            logger.error("Error exporting matrices: %s", e)
            return ""

    # ------------------------------------------------------------------
    # Markov blanket
    # ------------------------------------------------------------------

    def export_markov_blanket(self, blanket: Any, output_path: str) -> str:
        """
        Render a Markov blanket partition as PDF.

        Shows internal (μ), sensory (s), active (a), and external (η) node
        counts as a colour-coded bar chart plus a partition-coverage pie.

        Args:
            blanket: :class:`~cogant.markov.blanket.MarkovBlanket` object,
                or a plain dict with keys
                ``internal_ids / sensory_ids / active_ids / external_ids``.
            output_path: Path to write PDF file.

        Returns:
            Path to rendered file, or empty string if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            logger.warning("matplotlib not available; skipping PDF export")
            return ""

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            def _ids(attr: str) -> set[str]:
                v = getattr(blanket, attr, None)
                if v is None and isinstance(blanket, dict):
                    v = blanket.get(attr, set())
                return set(v) if v else set()

            internal = _ids("internal_ids")
            sensory = _ids("sensory_ids")
            active = _ids("active_ids")
            external = _ids("external_ids")

            categories = ["Internal (μ)", "Sensory (s)", "Active (a)", "External (η)"]
            counts = [len(internal), len(sensory), len(active), len(external)]
            colors = ["#4CAF50", "#FFC107", "#FF5722", "#9E9E9E"]

            with PdfPages(str(output_file)) as pdf:
                # PAGE 1: bar chart
                fig, ax = plt.subplots(figsize=(9, 6))
                bars = ax.bar(categories, counts, color=colors, edgecolor="white", linewidth=1.5)
                for bar in bars:
                    h = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        h + 0.2,
                        str(int(h)),
                        ha="center",
                        va="bottom",
                        fontsize=11,
                        weight="bold",
                    )
                ax.set_ylabel("Node count")
                ax.set_title("Markov Blanket Partition", fontsize=14, weight="bold")
                ax.grid(axis="y", alpha=0.3)
                ax.set_ylim(0, max(counts, default=1) * 1.2)
                fig.tight_layout()
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

                # PAGE 2: pie chart for partition coverage
                nonzero_cats = [(c, n) for c, n in zip(categories, counts, strict=False) if n > 0]
                if nonzero_cats:
                    labels, vals = zip(*nonzero_cats, strict=False)
                    pie_colors = [colors[categories.index(c)] for c in labels]
                    fig2, ax2 = plt.subplots(figsize=(8, 7))
                    wedges, texts, autotexts = ax2.pie(
                        vals,
                        labels=labels,
                        autopct="%1.1f%%",
                        colors=pie_colors,
                        startangle=90,
                        wedgeprops={"width": 0.55},
                    )
                    for t in autotexts:
                        t.set_fontsize(10)
                    ax2.set_title(
                        f"Partition Coverage  ({sum(counts)} total nodes)",
                        fontsize=13,
                        weight="bold",
                    )
                    fig2.tight_layout()
                    pdf.savefig(fig2, bbox_inches="tight")
                    plt.close(fig2)

                # PAGE 3: stats table if available
                stats = getattr(blanket, "stats", None) or (
                    blanket.get("stats") if isinstance(blanket, dict) else None
                )
                if stats and isinstance(stats, dict):
                    fig3, ax3 = plt.subplots(figsize=(8, 5))
                    ax3.axis("off")
                    rows = [[k, str(v)] for k, v in stats.items()]
                    tbl = ax3.table(
                        cellText=rows,
                        colLabels=["Metric", "Value"],
                        cellLoc="left",
                        loc="center",
                    )
                    tbl.auto_set_font_size(False)
                    tbl.set_fontsize(10)
                    tbl.scale(1.2, 1.6)
                    ax3.set_title("Blanket Statistics", fontsize=13, weight="bold", pad=20)
                    fig3.tight_layout()
                    pdf.savefig(fig3, bbox_inches="tight")
                    plt.close(fig3)

            logger.info("Exported Markov blanket to %s", output_path)
            return output_path

        except Exception as e:
            logger.error("Error exporting Markov blanket: %s", e)
            return ""

    # ------------------------------------------------------------------
    # Pipeline report
    # ------------------------------------------------------------------

    def export_pipeline_report(self, pipeline_result: Any, output_path: str) -> str:
        """
        Render a multi-page pipeline report PDF.

        Includes: cover page, stage timing horizontal bar chart, and a
        per-stage metrics table extracted from ``pipeline_result``.

        Args:
            pipeline_result: dict or object with stage timing/metrics.
                Recognised keys: ``stage_timings`` / ``timing``,
                ``stage_metrics`` / ``metrics``, ``target``.
            output_path: Path to write PDF file.

        Returns:
            Path to rendered file, or empty string if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            logger.warning("matplotlib not available; skipping PDF export")
            return ""

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Normalise input to dict
            if isinstance(pipeline_result, dict):
                result_dict = pipeline_result
            else:
                result_dict = {
                    k: getattr(pipeline_result, k, None)
                    for k in (
                        "stage_timings",
                        "timing",
                        "stage_metrics",
                        "metrics",
                        "target",
                        "errors",
                        "stage_results",
                    )
                }

            timing: dict[str, float] = (
                result_dict.get("stage_timings") or result_dict.get("timing") or {}
            )
            metrics: dict[str, Any] = (
                result_dict.get("stage_metrics") or result_dict.get("metrics") or {}
            )
            target = str(result_dict.get("target", "unknown"))

            with PdfPages(str(output_file)) as pdf:
                # PAGE 1: Cover
                fig, ax = plt.subplots(figsize=(8.5, 11))
                ax.text(
                    0.5,
                    0.80,
                    "Pipeline Report",
                    ha="center",
                    va="center",
                    fontsize=26,
                    weight="bold",
                )
                ax.text(0.5, 0.73, target, ha="center", va="center", fontsize=14, color="#555555")
                ax.text(
                    0.5,
                    0.65,
                    f"Stages: {len(timing)}\nTotal time: {sum(timing.values()):.3f}s",
                    ha="center",
                    va="center",
                    fontsize=12,
                    bbox={
                        "boxstyle": "round,pad=0.4",
                        "facecolor": "#EEF4FF",
                        "edgecolor": "#AAAACC",
                    },
                )
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis("off")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

                # PAGE 2: Timing bar chart
                if timing:
                    fig2, ax2 = plt.subplots(figsize=(9, 6))
                    sorted_pairs = sorted(timing.items(), key=lambda x: x[1], reverse=True)
                    stages, times = zip(*sorted_pairs, strict=False)
                    ax2.barh(stages, times, color="steelblue", alpha=0.85)
                    for idx, t in enumerate(times):
                        ax2.text(t, idx, f"  {t:.3f}s", va="center", fontsize=9)
                    ax2.set_xlabel("Elapsed (seconds)")
                    ax2.set_title("Stage Timing Analysis", fontsize=13, weight="bold")
                    ax2.grid(axis="x", alpha=0.3)
                    fig2.tight_layout()
                    pdf.savefig(fig2, bbox_inches="tight")
                    plt.close(fig2)

                # PAGE 3: Metrics table
                if metrics:
                    rows = []
                    for stage_name, stage_data in metrics.items():
                        if isinstance(stage_data, dict):
                            for key, val in stage_data.items():
                                rows.append([stage_name, key, str(val)])
                        else:
                            rows.append([stage_name, "value", str(stage_data)])
                    if rows:
                        fig3, ax3 = plt.subplots(figsize=(8.5, 11))
                        ax3.axis("off")
                        tbl = ax3.table(
                            cellText=rows[:40],
                            colLabels=["Stage", "Metric", "Value"],
                            cellLoc="left",
                            loc="upper center",
                        )
                        tbl.auto_set_font_size(False)
                        tbl.set_fontsize(9)
                        tbl.scale(1.2, 1.5)
                        ax3.set_title("Stage Metrics", fontsize=13, weight="bold", pad=20)
                        fig3.tight_layout()
                        pdf.savefig(fig3, bbox_inches="tight")
                        plt.close(fig3)

            logger.info("Exported pipeline report to %s", output_path)
            return output_path

        except Exception as e:
            logger.error("Error exporting pipeline report: %s", e)
            return ""

    # ------------------------------------------------------------------
    # Roundtrip report
    # ------------------------------------------------------------------

    def export_roundtrip_report(self, roundtrip_result: Any, output_path: str) -> str:
        """
        Render a roundtrip evaluation analysis PDF.

        Shows: cover + score, grouped bar chart comparing forward vs
        synthesised role counts, and a role delta table.

        Args:
            roundtrip_result: :class:`~cogant.reverse.idempotency.RoundtripResult`
                or a plain dict with the same fields.
            output_path: Path to write PDF file.

        Returns:
            Path to rendered file, or empty string if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            logger.warning("matplotlib not available; skipping PDF export")
            return ""

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            def _get(attr: str, default: Any = None) -> Any:
                v = getattr(roundtrip_result, attr, None)
                if v is None and isinstance(roundtrip_result, dict):
                    v = roundtrip_result.get(attr, default)
                return v if v is not None else default

            score: float = float(_get("role_preservation_score", _get("role_match_score", 0.0)))
            tier: str = str(_get("tier", "UNKNOWN"))
            forward_roles: dict[str, int] = dict(_get("forward_roles", {}))
            reverse_roles: dict[str, int] = dict(_get("reverse_roles", {}))
            elapsed: float = float(_get("elapsed_s", 0.0))

            all_roles = sorted(set(forward_roles) | set(reverse_roles))

            with PdfPages(str(output_file)) as pdf:
                # PAGE 1: Cover + score
                fig, ax = plt.subplots(figsize=(8.5, 11))
                ax.text(
                    0.5,
                    0.82,
                    "Roundtrip Analysis",
                    ha="center",
                    va="center",
                    fontsize=26,
                    weight="bold",
                )
                ax.text(
                    0.5,
                    0.75,
                    "Forward-Reverse-Forward Evaluation",
                    ha="center",
                    va="center",
                    fontsize=13,
                    color="#555555",
                )

                score_pct = score * 100
                score_color = (
                    "#27AE60" if score >= 0.8 else "#F39C12" if score >= 0.5 else "#E74C3C"
                )
                ax.text(
                    0.5,
                    0.60,
                    f"Role-match score: {score_pct:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=22,
                    weight="bold",
                    color=score_color,
                )
                ax.text(
                    0.5,
                    0.52,
                    f"Tier: {tier}",
                    ha="center",
                    va="center",
                    fontsize=16,
                    bbox={
                        "boxstyle": "round,pad=0.3",
                        "facecolor": score_color + "33",
                        "edgecolor": score_color,
                    },
                )
                ax.text(
                    0.5,
                    0.44,
                    f"Elapsed: {elapsed:.3f}s",
                    ha="center",
                    va="center",
                    fontsize=11,
                    color="#777777",
                )
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis("off")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

                # PAGE 2: Grouped bar chart (forward vs synthesised roles)
                if all_roles:
                    x = np.arange(len(all_roles))
                    width = 0.35
                    fwd_vals = [forward_roles.get(r, 0) for r in all_roles]
                    rev_vals = [reverse_roles.get(r, 0) for r in all_roles]

                    fig2, ax2 = plt.subplots(figsize=(10, 6))
                    bars1 = ax2.bar(
                        x - width / 2,
                        fwd_vals,
                        width,
                        label="Forward (original)",
                        color="#3498DB",
                        alpha=0.85,
                    )
                    bars2 = ax2.bar(
                        x + width / 2,
                        rev_vals,
                        width,
                        label="Synthesised (re-forward)",
                        color="#E67E22",
                        alpha=0.85,
                    )

                    for bar in (*bars1, *bars2):
                        h = bar.get_height()
                        if h > 0:
                            ax2.text(
                                bar.get_x() + bar.get_width() / 2,
                                h + 0.05,
                                str(int(h)),
                                ha="center",
                                va="bottom",
                                fontsize=8,
                            )

                    ax2.set_xticks(x)
                    ax2.set_xticklabels(all_roles, rotation=30, ha="right", fontsize=9)
                    ax2.set_ylabel("Node count")
                    ax2.set_title(
                        "Role Distribution: Forward vs Synthesised", fontsize=13, weight="bold"
                    )
                    ax2.legend(fontsize=10)
                    ax2.grid(axis="y", alpha=0.3)
                    fig2.tight_layout()
                    pdf.savefig(fig2, bbox_inches="tight")
                    plt.close(fig2)

                # PAGE 3: Delta table
                rows = []
                for role in all_roles:
                    f = forward_roles.get(role, 0)
                    r = reverse_roles.get(role, 0)
                    delta = r - f
                    rows.append([role, str(f), str(r), f"{delta:+d}"])

                fig3, ax3 = plt.subplots(figsize=(8, max(3, len(rows) * 0.4 + 2)))
                ax3.axis("off")
                tbl = ax3.table(
                    cellText=rows,
                    colLabels=["Role", "Forward", "Synthesised", "Δ"],
                    cellLoc="center",
                    loc="center",
                )
                tbl.auto_set_font_size(False)
                tbl.set_fontsize(10)
                tbl.scale(1.3, 1.8)

                # Colour positive/negative deltas
                for (row_idx, col_idx), cell in tbl.get_celld().items():
                    if row_idx > 0 and col_idx == 3:
                        val_str = cell.get_text().get_text()
                        try:
                            delta_val = int(val_str)
                            if delta_val > 0:
                                cell.set_facecolor("#D5F5E3")
                            elif delta_val < 0:
                                cell.set_facecolor("#FADBD8")
                        except ValueError:
                            pass

                ax3.set_title("Role Count Delta", fontsize=13, weight="bold", pad=20)
                fig3.tight_layout()
                pdf.savefig(fig3, bbox_inches="tight")
                plt.close(fig3)

            logger.info("Exported roundtrip report to %s", output_path)
            return output_path

        except Exception as e:
            logger.error("Error exporting roundtrip report: %s", e)
            return ""

    # ------------------------------------------------------------------
    # Full analysis report (reference implementation — kept intact)
    # ------------------------------------------------------------------

    def export_full_analysis_report(self, analysis_bundle: dict[str, Any], output_path: str) -> str:
        """
        Create a comprehensive multi-page analysis report PDF.

        Generates an 8+ page PDF with:
        - Page 1: Cover page with project name, timestamp, cogant version, summary stats
        - Page 2: Pipeline timing chart (10 stages)
        - Page 3: Semantic role distribution (pie chart)
        - Page 4: Top-10 complexity hotspots (bar chart)
        - Page 5: Module coupling scatter plot (Abstractness vs Instability)
        - Page 6: A/B/C/D matrix heatmaps (4 panels)
        - Page 7: Markov blanket partition diagram
        - Page 8: GNN validator score breakdown

        Args:
            analysis_bundle: Dict with optional keys:
                - 'project_name': str
                - 'timestamp': str
                - 'version': str
                - 'summary_stats': dict
                - 'pipeline_timing': dict[str, float]
                - 'semantic_roles': dict[str, int]
                - 'complexity_hotspots': dict[str, float]
                - 'coupling_metrics': dict
                - 'matrices': dict[str, Any]
                - 'markov_blanket': dict
                - 'validator_score': float
                - 'validation_findings': list
            output_path: Path to write PDF file.

        Returns:
            Path to rendered file, or empty string if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping analysis report")
            return ""

        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with PdfPages(str(output_file)) as pdf:
                # PAGE 1: Cover page
                fig, ax = plt.subplots(figsize=(8.5, 11))

                project_name = analysis_bundle.get("project_name", "COGANT Analysis Report")
                timestamp = analysis_bundle.get("timestamp", "")
                version = analysis_bundle.get("version", "")
                summary_stats = analysis_bundle.get("summary_stats", {})

                ax.text(
                    0.5, 0.85, project_name, ha="center", va="center", fontsize=26, weight="bold"
                )
                ax.text(0.5, 0.78, "COGANT Analysis Report", ha="center", va="center", fontsize=16)

                stats_y = 0.70
                ax.text(0.5, stats_y, f"Generated: {timestamp}", ha="center", va="top", fontsize=10)
                ax.text(
                    0.5,
                    stats_y - 0.04,
                    f"COGANT Version: {version}",
                    ha="center",
                    va="top",
                    fontsize=10,
                )

                # Summary stats
                stats_text = "Summary Statistics:\n"
                if summary_stats:
                    for key, value in list(summary_stats.items())[:5]:
                        stats_text += f"  {key}: {value}\n"

                ax.text(
                    0.5, 0.50, stats_text, ha="center", va="center", fontsize=10, family="monospace"
                )

                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis("off")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

                # PAGE 2: Pipeline timing chart
                pipeline_timing = analysis_bundle.get("pipeline_timing", {})
                if pipeline_timing:
                    fig, ax = plt.subplots(figsize=(8.5, 11))

                    stages = list(pipeline_timing.keys())
                    times = list(pipeline_timing.values())

                    ax.barh(stages, times, color="steelblue", alpha=0.7)
                    ax.set_xlabel("Time (seconds)")
                    ax.set_title("Pipeline Stage Timing", fontsize=14, weight="bold")
                    ax.grid(axis="x", alpha=0.3)

                    for idx, (_, time) in enumerate(zip(stages, times, strict=False)):
                        ax.text(time, idx, f" {time:.2f}s", va="center", fontsize=9)

                    pdf.savefig(fig, bbox_inches="tight")
                    plt.close(fig)

                # PAGE 3: Semantic role distribution
                semantic_roles = analysis_bundle.get("semantic_roles", {})
                if semantic_roles:
                    fig, ax = plt.subplots(figsize=(8.5, 11))

                    roles = list(semantic_roles.keys())
                    counts = list(semantic_roles.values())

                    colors = plt.cm.Set3(np.linspace(0, 1, len(roles)))
                    ax.pie(counts, labels=roles, autopct="%1.1f%%", colors=colors, startangle=90)
                    ax.set_title("Semantic Role Distribution", fontsize=14, weight="bold")

                    pdf.savefig(fig, bbox_inches="tight")
                    plt.close(fig)

                # PAGE 4: Top-10 complexity hotspots
                complexity_hotspots = analysis_bundle.get("complexity_hotspots", {})
                if complexity_hotspots:
                    fig, ax = plt.subplots(figsize=(8.5, 11))

                    sorted_hotspots = sorted(
                        complexity_hotspots.items(), key=lambda x: x[1], reverse=True
                    )[:10]
                    names, scores = (
                        zip(*sorted_hotspots, strict=False) if sorted_hotspots else ([], [])
                    )

                    ax.barh(names, scores, color="coral", alpha=0.7)
                    ax.set_xlabel("Complexity Score")
                    ax.set_title("Top 10 Complexity Hotspots", fontsize=14, weight="bold")
                    ax.grid(axis="x", alpha=0.3)

                    for idx, (_, score) in enumerate(zip(names, scores, strict=False)):
                        ax.text(score, idx, f" {score:.2f}", va="center", fontsize=9)

                    pdf.savefig(fig, bbox_inches="tight")
                    plt.close(fig)

                # PAGE 5: Module coupling (Abstractness vs Instability)
                coupling_metrics = analysis_bundle.get("coupling_metrics", {})
                if coupling_metrics:
                    fig, ax = plt.subplots(figsize=(8.5, 11))

                    modules = coupling_metrics.get("modules", {})
                    abstractness = []
                    instability = []
                    names = []

                    for name, module_data in modules.items():
                        names.append(name)
                        abstractness.append(module_data.get("abstractness", 0.5))
                        instability.append(module_data.get("instability", 0.5))

                    if abstractness:
                        ax.scatter(abstractness, instability, s=100, alpha=0.6, color="steelblue")

                        for name, a, i in zip(names, abstractness, instability, strict=False):
                            ax.annotate(
                                name, (a, i), fontsize=7, xytext=(2, 2), textcoords="offset points"
                            )

                        # Main sequence line
                        x_line = np.linspace(0, 1, 100)
                        y_line = 1 - x_line
                        ax.plot(
                            x_line, y_line, "r--", linewidth=2, label="Main Sequence (I + A = 1)"
                        )

                        ax.set_xlabel("Abstractness (A)")
                        ax.set_ylabel("Instability (I)")
                        ax.set_title(
                            "Module Coupling: Abstractness vs Instability",
                            fontsize=14,
                            weight="bold",
                        )
                        ax.set_xlim(-0.05, 1.05)
                        ax.set_ylim(-0.05, 1.05)
                        ax.grid(alpha=0.3)
                        ax.legend(fontsize=9)

                        pdf.savefig(fig, bbox_inches="tight")
                        plt.close(fig)

                # PAGE 6: A/B/C/D matrices
                matrices = analysis_bundle.get("matrices", {})
                if matrices:
                    fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))

                    for idx, (matrix_name, matrix_data) in enumerate(
                        [
                            ("A", matrices.get("A")),
                            ("B", matrices.get("B")),
                            ("C", matrices.get("C")),
                            ("D", matrices.get("D")),
                        ]
                    ):
                        ax = axes[idx // 2, idx % 2]

                        if matrix_data is not None:
                            try:
                                matrix_array = np.asarray(matrix_data, dtype=float)
                                if matrix_array.ndim == 3 and matrix_name == "B":
                                    matrix_array = matrix_array[0]  # First action

                                im = ax.imshow(
                                    matrix_array, cmap="YlOrRd", aspect="auto", origin="lower"
                                )
                                ax.set_title(f"{matrix_name} Matrix", fontsize=11, weight="bold")
                                plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                            except Exception as e:
                                logger.debug("Could not visualize %s matrix: %s", matrix_name, e)
                                ax.text(
                                    0.5,
                                    0.5,
                                    f"{matrix_name} Matrix\n(unavailable)",
                                    ha="center",
                                    va="center",
                                )
                        else:
                            ax.text(
                                0.5,
                                0.5,
                                f"{matrix_name} Matrix\n(no data)",
                                ha="center",
                                va="center",
                            )

                        ax.set_xticks([])
                        ax.set_yticks([])

                    fig.suptitle("Active Inference Matrices", fontsize=14, weight="bold")
                    pdf.savefig(fig, bbox_inches="tight")
                    plt.close(fig)

                # PAGE 7: Markov blanket partition
                markov_blanket = analysis_bundle.get("markov_blanket", {})
                if markov_blanket:
                    fig, ax = plt.subplots(figsize=(8.5, 11))

                    internal_count = len(markov_blanket.get("internal", []))
                    boundary_count = len(markov_blanket.get("boundary", []))
                    external_count = len(markov_blanket.get("external", []))

                    categories = ["Internal", "Boundary", "External"]
                    counts = [internal_count, boundary_count, external_count]
                    colors = ["#90EE90", "#FFD700", "#FF6B6B"]

                    bars = ax.bar(categories, counts, color=colors, alpha=0.7, edgecolor="black")
                    ax.set_ylabel("Count")
                    ax.set_title("Markov Blanket Partition", fontsize=14, weight="bold")
                    ax.grid(axis="y", alpha=0.3)

                    for bar in bars:
                        height = bar.get_height()
                        ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            height,
                            f" {int(height)}",
                            ha="center",
                            va="bottom",
                            fontsize=10,
                        )

                    pdf.savefig(fig, bbox_inches="tight")
                    plt.close(fig)

                # PAGE 8: Validator score breakdown
                fig, ax = plt.subplots(figsize=(8.5, 11))

                validator_score = analysis_bundle.get("validator_score", 0)
                validation_findings = analysis_bundle.get("validation_findings", [])

                ax.text(
                    0.5,
                    0.85,
                    "GNN Validator Report",
                    ha="center",
                    va="center",
                    fontsize=14,
                    weight="bold",
                )

                # Score display
                score_color = (
                    "green"
                    if validator_score >= 75
                    else "orange"
                    if validator_score >= 50
                    else "red"
                )
                ax.text(
                    0.5,
                    0.72,
                    f"Validator Score: {validator_score}/100",
                    ha="center",
                    va="center",
                    fontsize=20,
                    weight="bold",
                    color=score_color,
                )

                # Findings
                findings_text = "Findings:\n"
                for finding in validation_findings[:10]:  # Show top 10
                    if isinstance(finding, dict):
                        findings_text += f"  • {finding.get('message', str(finding))}\n"
                    else:
                        findings_text += f"  • {finding}\n"

                ax.text(
                    0.05, 0.60, findings_text, ha="left", va="top", fontsize=9, family="monospace"
                )

                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis("off")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

            logger.info("Exported full analysis report to %s", output_path)
            return output_path

        except Exception as e:
            logger.error("Error exporting full analysis report: %s", e)
            return ""
