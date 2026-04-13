"""
Visualizations for graph/network analysis of ProgramGraph.

Renders degree distributions, centrality rankings, community detection,
adjacency heatmaps, and hotspot analysis as matplotlib figures and Mermaid diagrams.

Supports network statistics visualization with graceful degradation if matplotlib
or networkx are unavailable.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


class NetworkView:
    """Visualizations for ProgramGraph network analysis."""

    def __init__(self) -> None:
        """Initialize the NetworkView."""
        pass

    def plot_degree_distribution(self, metrics: dict[str, Any]) -> Figure | None:
        """
        Log-log degree distribution plot.

        Visualizes the distribution of node degrees on a log-log scale,
        useful for identifying power-law or scale-free network properties.

        Args:
            metrics: Dict with 'degrees' key containing list of degree values.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping degree distribution plot")
            return None

        try:
            degrees = metrics.get("degrees", [])
            if not degrees:
                logger.warning("No degree data in metrics")
                return None

            fig, ax = plt.subplots(figsize=(10, 8))

            # Calculate degree distribution histogram
            unique_degrees, counts = np.unique(degrees, return_counts=True)

            # Log-log plot
            ax.loglog(unique_degrees, counts, "o-", linewidth=2, markersize=8, color="steelblue")
            ax.set_xlabel("Degree (log scale)")
            ax.set_ylabel("Frequency (log scale)")
            ax.set_title("Degree Distribution: Log-Log Plot")
            ax.grid(True, alpha=0.3, which="both")

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting degree distribution: {e}")
            return None

    def plot_centrality_ranking(self, centrality: dict[str, float], top_n: int = 15) -> Figure | None:
        """
        Horizontal bar chart of top-N nodes by centrality score.

        Ranks and visualizes the most central nodes in the network.

        Args:
            centrality: Dict mapping node names to centrality scores.
            top_n: Number of top nodes to display (default 15).

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping centrality ranking plot")
            return None

        try:
            if not centrality:
                logger.warning("No centrality data provided")
                return None

            # Sort by centrality descending
            sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:top_n]
            nodes, scores = zip(*sorted_nodes, strict=False) if sorted_nodes else ([], [])

            fig, ax = plt.subplots(figsize=(12, max(8, len(nodes) * 0.3)))

            bars = ax.barh(nodes, scores, color="steelblue", alpha=0.7)
            ax.set_xlabel("Centrality Score")
            ax.set_title(f"Top {top_n} Nodes by Centrality Score")
            ax.grid(axis="x", alpha=0.3)

            # Add value labels
            for bar, score in zip(bars, scores, strict=False):
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height() / 2, f" {score:.3f}",
                       va="center", fontsize=9)

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting centrality ranking: {e}")
            return None

    def plot_community_graph(self, graph: Any, communities: list[frozenset]) -> Figure | None:
        """
        Node-link diagram with communities colored differently.

        Visualizes the network structure with nodes colored by community membership.

        Args:
            graph: NetworkX graph object.
            communities: List of frozensets, each containing node IDs in a community.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
        except ImportError:
            logger.warning("matplotlib or networkx not available; skipping community graph plot")
            return None

        try:
            if graph is None or not graph.nodes():
                logger.warning("Empty graph provided")
                return None

            fig, ax = plt.subplots(figsize=(14, 10))

            # Layout
            pos = nx.spring_layout(graph, k=2, iterations=50, seed=42)

            # Assign colors to communities
            import matplotlib.colors as mcolors
            colors_list = list(mcolors.TABLEAU_COLORS.values())
            node_color_map = {}

            for community_idx, community in enumerate(communities):
                color = colors_list[community_idx % len(colors_list)]
                for node in community:
                    node_color_map[node] = color

            # Default color for nodes not in any community
            node_colors = [
                node_color_map.get(node, "lightgray")
                for node in graph.nodes()
            ]

            # Draw graph
            nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=300, alpha=0.9, ax=ax)
            nx.draw_networkx_labels(graph, pos, font_size=7, ax=ax)
            nx.draw_networkx_edges(graph, pos, alpha=0.3, ax=ax, width=0.5)

            ax.set_title(f"Community Detection: {len(communities)} Communities")
            ax.axis("off")

            # Add legend
            legend_elements = [
                plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=colors_list[i % len(colors_list)],
                          markersize=8, label=f"Community {i + 1}")
                for i in range(len(communities))
            ]
            ax.legend(handles=legend_elements, loc="upper left", fontsize=9)

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting community graph: {e}")
            return None

    def plot_adjacency_heatmap(self, matrix: list[list[int]], labels: list[str] | None = None) -> Figure | None:
        """
        Adjacency matrix as heatmap.

        Visualizes the adjacency matrix as a colored heatmap showing node connections.

        Args:
            matrix: 2D list or array representing adjacency matrix.
            labels: Optional list of node labels (row/column names).

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.warning("matplotlib or numpy not available; skipping adjacency heatmap")
            return None

        try:
            matrix_array = np.asarray(matrix, dtype=int)
            if matrix_array.size == 0:
                logger.warning("Empty matrix provided")
                return None

            fig, ax = plt.subplots(figsize=(12, 10))

            im = ax.imshow(matrix_array, cmap="YlOrRd", aspect="auto", origin="upper")

            ax.set_xlabel("Target Node")
            ax.set_ylabel("Source Node")
            ax.set_title("Adjacency Matrix Heatmap")

            plt.colorbar(im, ax=ax, label="Edge Weight")

            if labels:
                # Show a subset of labels to avoid clutter
                n_labels = len(labels)
                step = max(1, n_labels // 20)  # Show at most 20 labels
                label_positions = list(range(0, n_labels, step))
                ax.set_xticks(label_positions)
                ax.set_xticklabels([labels[i] for i in label_positions], rotation=45, ha="right", fontsize=8)
                ax.set_yticks(label_positions)
                ax.set_yticklabels([labels[i] for i in label_positions], fontsize=8)

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting adjacency heatmap: {e}")
            return None

    def plot_hotspot_treemap(self, hotspots: dict[str, float]) -> Figure | None:
        """
        Treemap of node importance (area = centrality score).

        Creates a treemap visualization where the area of each rectangle
        is proportional to the node's importance score.

        Args:
            hotspots: Dict mapping node names to importance/centrality scores.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            import squarify
        except ImportError:
            logger.warning("matplotlib or squarify not available; skipping hotspot treemap")
            return None

        try:
            if not hotspots:
                logger.warning("No hotspot data provided")
                return None

            fig, ax = plt.subplots(figsize=(14, 10))

            # Prepare data
            labels = list(hotspots.keys())
            sizes = list(hotspots.values())

            # Create treemap
            colors = plt.cm.RdYlGn_r([(s - min(sizes)) / (max(sizes) - min(sizes)) for s in sizes])

            squarify.plot(sizes=sizes, label=labels, ax=ax, color=colors, alpha=0.8, edgecolor="white", linewidth=2)

            ax.set_title("Hotspot Treemap: Node Importance (Area = Score)")
            ax.axis("off")

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting hotspot treemap: {e}")
            return None

    def to_mermaid_community(self, communities: list[frozenset]) -> str:
        """
        Mermaid subgraph diagram with one subgraph per community.

        Creates a Mermaid diagram showing community structure with nodes grouped
        into subgraphs by community membership.

        Args:
            communities: List of frozensets, each containing node IDs in a community.

        Returns:
            Mermaid graph syntax.
        """
        if not communities:
            logger.warning("No communities provided")
            return ""

        lines = ["graph TD"]

        # Add subgraphs for each community
        for cidx, community in enumerate(communities):
            safe_id = f"community_{cidx}"
            lines.append(f"    subgraph {safe_id}[\"Community {cidx + 1}\"]")

            for node_id in list(community)[:10]:  # Limit nodes per subgraph for readability
                safe_node = str(node_id).replace("-", "_").replace(".", "_")
                lines.append(f'        {safe_node}["{node_id}"]')

            if len(community) > 10:
                extra_count = len(community) - 10
                lines.append(f'        more_nodes["... +{extra_count} more"]')

            lines.append("    end")

        return "\n".join(lines)

    def to_mermaid_hotspots(self, hotspots: dict[str, float]) -> str:
        """
        Mermaid flowchart highlighting hub/bottleneck/source/sink nodes.

        Creates a flowchart showing the most important nodes, classified by their role:
        - Hubs: High in-degree and out-degree
        - Bottlenecks: High in-degree
        - Sources: High out-degree
        - Sinks: High in-degree, low out-degree

        Args:
            hotspots: Dict mapping node names to importance scores.

        Returns:
            Mermaid flowchart syntax.
        """
        if not hotspots:
            logger.warning("No hotspot data provided")
            return ""

        lines = ["graph TD"]

        # Sort by score and take top 10
        top_hotspots = sorted(hotspots.items(), key=lambda x: x[1], reverse=True)[:10]

        for _, (node_name, score) in enumerate(top_hotspots):
            safe_name = str(node_name).replace("-", "_").replace(".", "_")
            lines.append(f'    {safe_name}["{node_name}<br/>(Score: {score:.3f})"]')

            # Color based on score percentile
            max_score = top_hotspots[0][1] if top_hotspots else 1
            percentile = score / max_score

            if percentile > 0.75:
                lines.append(f"    style {safe_name} fill:#FF6B6B")  # Red - Critical
            elif percentile > 0.5:
                lines.append(f"    style {safe_name} fill:#FFD700")  # Yellow - Important
            else:
                lines.append(f"    style {safe_name} fill:#90EE90")  # Green - Moderate

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
