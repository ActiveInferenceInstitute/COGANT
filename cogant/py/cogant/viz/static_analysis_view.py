"""
Visualizations for static analysis results.

Renders complexity metrics, coupling analysis, dead code detection, and
Halstead metrics as matplotlib figures and Mermaid diagrams.

Supports heatmaps, histograms, network graphs, scatter plots, radar charts,
and summary pie charts. All exports gracefully degrade if matplotlib is unavailable.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from cogant.static.complexity import ComplexityReport
    from cogant.static.coupling import CouplingReport
    from cogant.static.dead_code import DeadCodeReport
    from cogant.static.metrics import HalsteadMetrics

logger = logging.getLogger(__name__)


class StaticAnalysisView:
    """Visualizations for static analysis reports."""

    def __init__(self) -> None:
        """Initialize the StaticAnalysisView."""
        pass

    def plot_complexity_heatmap(
        self,
        report: ComplexityReport,
        threshold: int = 10,
    ) -> Figure | None:
        """
        Heatmap of cyclomatic complexity per function, colored by severity.

        Severity levels:
        - Green (0-5): Low complexity
        - Yellow (6-10): Moderate complexity
        - Orange (11-20): High complexity
        - Red (20+): Very high complexity

        Args:
            report: ComplexityReport with entries for each symbol.
            threshold: Highlight threshold (default 10).

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping complexity heatmap")
            return None

        try:
            entries = report.entries if hasattr(report, "entries") else []
            if not entries:
                logger.warning("No entries in complexity report")
                return None

            names = [entry.name if hasattr(entry, "name") else str(entry) for entry in entries]
            complexities = [
                entry.cyclomatic_complexity if hasattr(entry, "cyclomatic_complexity") else 0
                for entry in entries
            ]

            # Sort by complexity descending
            sorted_pairs = sorted(zip(names, complexities, strict=False), key=lambda x: x[1], reverse=True)
            names_sorted, complexities_sorted = (
                zip(*sorted_pairs, strict=False) if sorted_pairs else ([], [])
            )

            fig, ax = plt.subplots(figsize=(12, max(8, len(names_sorted) * 0.3)))

            # Color bars by severity
            colors = []
            for c in complexities_sorted:
                if c <= 5:
                    colors.append("green")
                elif c <= 10:
                    colors.append("yellow")
                elif c <= 20:
                    colors.append("orange")
                else:
                    colors.append("red")

            bars = ax.barh(names_sorted, complexities_sorted, color=colors, alpha=0.7)
            ax.axvline(x=threshold, color="red", linestyle="--", linewidth=2, label=f"Threshold ({threshold})")
            ax.set_xlabel("Cyclomatic Complexity")
            ax.set_title("Complexity Heatmap: Cyclomatic Complexity per Function")
            ax.legend()
            ax.grid(axis="x", alpha=0.3)

            # Add value labels
            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height() / 2, f" {int(width)}",
                        va="center", fontsize=9)

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting complexity heatmap: {e}")
            return None

    def plot_complexity_histogram(self, report: ComplexityReport) -> Figure | None:
        """
        Histogram of complexity score distribution.

        Shows the distribution of cyclomatic complexity across all functions,
        with annotated bins and statistics.

        Args:
            report: ComplexityReport with entries for each symbol.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping complexity histogram")
            return None

        try:
            entries = report.entries if hasattr(report, "entries") else []
            if not entries:
                logger.warning("No entries in complexity report")
                return None

            complexities = [
                entry.cyclomatic_complexity if hasattr(entry, "cyclomatic_complexity") else 0
                for entry in entries
            ]

            fig, ax = plt.subplots(figsize=(12, 6))

            counts, bins, patches = ax.hist(complexities, bins=15, color="steelblue", alpha=0.7, edgecolor="black")

            # Color bins by severity
            for i, patch in enumerate(patches):
                bin_center = (bins[i] + bins[i + 1]) / 2
                if bin_center <= 5:
                    patch.set_facecolor("green")
                elif bin_center <= 10:
                    patch.set_facecolor("yellow")
                elif bin_center <= 20:
                    patch.set_facecolor("orange")
                else:
                    patch.set_facecolor("red")

            ax.set_xlabel("Cyclomatic Complexity")
            ax.set_ylabel("Count")
            ax.set_title("Complexity Distribution: Histogram of Cyclomatic Complexity Scores")
            ax.grid(axis="y", alpha=0.3)

            # Add statistics
            mean_complexity = np.mean(complexities)
            median_complexity = np.median(complexities)
            ax.axvline(x=mean_complexity, color="red", linestyle="-", linewidth=2, label=f"Mean: {mean_complexity:.2f}")
            ax.axvline(
                x=median_complexity, color="blue", linestyle="--", linewidth=2, label=f"Median: {median_complexity:.2f}"
            )
            ax.legend()

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting complexity histogram: {e}")
            return None

    def plot_coupling_graph(self, report: CouplingReport) -> Figure | None:
        """
        Network graph of module coupling (node size = instability).

        Visualizes module dependencies as a directed graph where:
        - Node size represents instability (larger = more instable)
        - Edge width represents coupling strength
        - Color represents module type

        Args:
            report: CouplingReport with module coupling data.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
        except ImportError:
            logger.warning("matplotlib or networkx not available; skipping coupling graph")
            return None

        try:
            # Extract module coupling data
            modules = report.modules if hasattr(report, "modules") else {}
            if not modules:
                logger.warning("No modules in coupling report")
                return None

            fig, ax = plt.subplots(figsize=(14, 10))

            # Build directed graph
            G = nx.DiGraph()

            for module_name, _ in modules.items():
                G.add_node(module_name)

            # Add edges based on dependencies
            coupling_matrix = report.coupling_matrix if hasattr(report, "coupling_matrix") else {}
            for source, targets in coupling_matrix.items():
                for target, strength in targets.items():
                    G.add_edge(source, target, weight=strength)

            if not G.nodes():
                logger.warning("Empty coupling graph")
                return fig

            # Layout
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

            # Node sizes based on instability
            node_sizes = []
            for node in G.nodes():
                instability = modules.get(node, {}).get("instability", 0.5)
                node_sizes.append(3000 * max(0.1, instability))

            # Draw graph
            nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color="lightblue", alpha=0.9, ax=ax)
            nx.draw_networkx_labels(G, pos, font_size=8, ax=ax)

            # Draw edges with varying width
            edges = G.edges()
            weights = [G[u][v].get("weight", 1) for u, v in edges]
            max_weight = max(weights) if weights else 1
            widths = [3 * w / max_weight for w in weights]

            nx.draw_networkx_edges(G, pos, width=widths, edge_color="gray", alpha=0.6,
                                  connectionstyle="arc3,rad=0.1", ax=ax, arrowsize=15)

            ax.set_title("Module Coupling Graph: Instability-Based Layout")
            ax.axis("off")

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting coupling graph: {e}")
            return None

    def plot_martin_metrics(self, report: CouplingReport) -> Figure | None:
        """
        Scatter plot: Abstractness vs Instability with main sequence line.

        Visualizes the Martin metrics (Abstractness and Instability) on a 2D plot,
        showing the "main sequence" line (I + A = 1) where balanced modules lie.

        Args:
            report: CouplingReport with module metrics.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping Martin metrics plot")
            return None

        try:
            modules = report.modules if hasattr(report, "modules") else {}
            if not modules:
                logger.warning("No modules in coupling report")
                return None

            fig, ax = plt.subplots(figsize=(10, 8))

            names = []
            abstractness = []
            instability = []

            for name, md in modules.items():
                names.append(name)
                abstractness.append(md.get("abstractness", 0.5) if isinstance(md, dict) else 0.5)
                instability.append(md.get("instability", 0.5) if isinstance(md, dict) else 0.5)

            # Scatter plot
            ax.scatter(abstractness, instability, s=100, alpha=0.6, color="steelblue")

            # Add labels
            for name, a, i in zip(names, abstractness, instability, strict=False):
                ax.annotate(name, (a, i), fontsize=8, xytext=(3, 3), textcoords="offset points")

            # Main sequence line (I + A = 1)
            x_line = np.linspace(0, 1, 100)
            y_line = 1 - x_line
            ax.plot(x_line, y_line, "r--", linewidth=2, label="Main Sequence (I + A = 1)")

            # Zone labels
            ax.fill_between(x_line, y_line - 0.1, y_line + 0.1, alpha=0.1, color="green", label="Balanced Zone")

            ax.set_xlabel("Abstractness (A)")
            ax.set_ylabel("Instability (I)")
            ax.set_title("Martin Metrics: Abstractness vs Instability")
            ax.set_xlim(-0.05, 1.05)
            ax.set_ylim(-0.05, 1.05)
            ax.grid(alpha=0.3)
            ax.legend()

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting Martin metrics: {e}")
            return None

    def plot_dead_code_summary(self, report: DeadCodeReport) -> Figure | None:
        """
        Bar chart of dead code entries by kind and confidence.

        Visualizes the distribution of dead code findings grouped by:
        - Kind (unused variable, unreachable code, etc.)
        - Confidence (high, medium, low)

        Args:
            report: DeadCodeReport with dead code entries.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping dead code plot")
            return None

        try:
            entries = report.entries if hasattr(report, "entries") else []
            if not entries:
                logger.warning("No entries in dead code report")
                return None

            # Count by kind
            kind_counts: dict[str, int] = {}
            for entry in entries:
                kind = entry.kind if hasattr(entry, "kind") else "unknown"
                kind_counts[kind] = kind_counts.get(kind, 0) + 1

            kinds = list(kind_counts.keys())
            counts = list(kind_counts.values())

            fig, ax = plt.subplots(figsize=(12, 6))

            bars = ax.bar(kinds, counts, color="coral", alpha=0.7, edgecolor="black")
            ax.set_ylabel("Count")
            ax.set_title("Dead Code Summary: Entries by Kind")
            ax.grid(axis="y", alpha=0.3)

            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, height, f" {int(height)}",
                       ha="center", va="bottom", fontsize=10)

            plt.xticks(rotation=45, ha="right")
            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting dead code summary: {e}")
            return None

    def plot_halstead_radar(self, metrics: HalsteadMetrics) -> Figure | None:
        """
        Radar chart of Halstead metrics (volume, difficulty, effort, etc.).

        Visualizes key Halstead metrics on a radar chart:
        - Volume (code size)
        - Difficulty (complexity indicator)
        - Effort (estimated effort to implement)
        - Time (estimated implementation time)
        - Bugs (estimated defect count)

        Args:
            metrics: HalsteadMetrics object with metric values.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np  # noqa: F401
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping Halstead radar")
            return None

        try:
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"projection": "polar"})

            # Extract metrics (normalized to 0-100 scale for visualization)
            metric_names = ["Volume", "Difficulty", "Effort", "Time", "Bugs"]
            metric_values = [
                min(100, getattr(metrics, "volume", 0) / 10),  # Normalize
                min(100, getattr(metrics, "difficulty", 0) * 10),  # Normalize
                min(100, getattr(metrics, "effort", 0) / 100),  # Normalize
                min(100, getattr(metrics, "time", 0) * 10),  # Normalize
                min(100, getattr(metrics, "bugs", 0) * 50),  # Normalize
            ]

            # Number of variables
            num_vars = len(metric_names)
            angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
            metric_values_plot = metric_values + [metric_values[0]]  # Complete the circle
            angles_plot = angles + [angles[0]]

            ax.plot(angles_plot, metric_values_plot, "o-", linewidth=2, color="steelblue")
            ax.fill(angles_plot, metric_values_plot, alpha=0.25, color="steelblue")

            ax.set_xticks(angles)
            ax.set_xticklabels(metric_names)
            ax.set_ylim(0, 100)
            ax.set_title("Halstead Metrics Radar Chart", fontsize=14, weight="bold", pad=20)
            ax.grid(True)

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting Halstead radar: {e}")
            return None

    def to_mermaid_complexity(self, report: ComplexityReport) -> str:
        """
        Mermaid pie chart of complexity distribution.

        Shows the distribution of functions by complexity level (low, moderate, high, very high).

        Args:
            report: ComplexityReport with entries.

        Returns:
            Mermaid pie chart syntax.
        """
        entries = report.entries if hasattr(report, "entries") else []
        if not entries:
            logger.warning("No entries in complexity report")
            return ""

        complexities = [
            entry.cyclomatic_complexity if hasattr(entry, "cyclomatic_complexity") else 0
            for entry in entries
        ]

        low = sum(1 for c in complexities if c <= 5)
        moderate = sum(1 for c in complexities if 6 <= c <= 10)
        high = sum(1 for c in complexities if 11 <= c <= 20)
        very_high = sum(1 for c in complexities if c > 20)

        lines = [
            "pie title Complexity Distribution",
            f'    "Low (1-5)": {low}',
            f'    "Moderate (6-10)": {moderate}',
            f'    "High (11-20)": {high}',
            f'    "Very High (20+)": {very_high}',
        ]

        return "\n".join(lines)

    def to_mermaid_coupling(self, report: CouplingReport) -> str:
        """
        Mermaid graph of module dependencies colored by instability.

        Visualizes module coupling as a Mermaid graph where node colors
        indicate instability level.

        Args:
            report: CouplingReport with module data.

        Returns:
            Mermaid graph syntax.
        """
        modules = report.modules if hasattr(report, "modules") else {}
        if not modules:
            logger.warning("No modules in coupling report")
            return ""

        lines = ["graph TD"]

        # Add nodes with styling based on instability
        for module_name, module_data in modules.items():
            instability = module_data.get("instability", 0.5)
            safe_name = module_name.replace("-", "_").replace(".", "_")

            if instability < 0.3:
                style = "fill:#90EE90"  # Green
            elif instability < 0.7:
                style = "fill:#FFD700"  # Yellow
            else:
                style = "fill:#FF6B6B"  # Red

            lines.append(f'    {safe_name}["{module_name}<br/>(I={instability:.2f})"]')
            lines.append(f'    style {safe_name} {style}')

        # Add edges from coupling matrix
        coupling_matrix = report.coupling_matrix if hasattr(report, "coupling_matrix") else {}
        for source, targets in coupling_matrix.items():
            safe_source = source.replace("-", "_").replace(".", "_")
            for target in targets:
                safe_target = target.replace("-", "_").replace(".", "_")
                lines.append(f"    {safe_source} --> {safe_target}")

        return "\n".join(lines)

    def to_png(self, fig: Any, output_path: str, dpi: int = 150) -> str:
        """
        Save a matplotlib figure to PNG.

        Args:
            fig: Matplotlib Figure object.
            output_path: Path to write PNG file.
            dpi: Resolution in dots per inch.

        Returns:
            Path to rendered file, or empty string if save fails.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping PNG save")
            return ""

        try:
            if fig is None:
                logger.warning("Figure is None; skipping PNG save")
                return ""

            fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Saved figure to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error saving PNG: {e}")
            return ""

    def to_pdf(self, fig: Any, output_path: str) -> str:
        """
        Save a matplotlib figure to PDF.

        Args:
            fig: Matplotlib Figure object.
            output_path: Path to write PDF file.

        Returns:
            Path to rendered file, or empty string if save fails.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping PDF save")
            return ""

        try:
            if fig is None:
                logger.warning("Figure is None; skipping PDF save")
                return ""

            fig.savefig(output_path, format="pdf", bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Saved figure to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error saving PDF: {e}")
            return ""
