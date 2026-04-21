"""
Visualizations for export/format summaries and bundle composition.

Renders export format comparisons, pipeline overviews, and GNN bundle
composition as matplotlib figures and Mermaid diagrams.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


class ExportView:
    """Summary and diagnostic visualizations for export operations."""

    def __init__(self) -> None:
        """Initialize the ExportView."""
        pass

    def plot_export_formats(self, export_results: dict[str, Any]) -> Figure | None:
        """
        Bar chart showing file sizes by export format.

        Visualizes the size distribution across different export formats
        (e.g., PNG, PDF, JSON, Markdown).

        Args:
            export_results: Dict with format names as keys and size info as values.
                Each value should have a 'size' key (in bytes) or 'file_path' for stat lookup.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping export formats plot")
            return None

        try:
            if not export_results:
                logger.warning("No export results provided")
                return None

            formats = []
            sizes_mb = []

            for format_name, result_data in export_results.items():
                formats.append(format_name)

                # Try to get size from result data
                if isinstance(result_data, dict):
                    if "size" in result_data:
                        size = result_data["size"]
                    elif "file_path" in result_data:
                        try:
                            from pathlib import Path

                            size = Path(result_data["file_path"]).stat().st_size
                        except Exception:
                            size = 0
                    else:
                        size = 0
                else:
                    size = 0

                sizes_mb.append(size / (1024 * 1024))  # Convert to MB

            fig, ax = plt.subplots(figsize=(12, 6))

            bars = ax.bar(formats, sizes_mb, color="steelblue", alpha=0.7, edgecolor="black")
            ax.set_ylabel("Size (MB)")
            ax.set_title("Export Formats: File Size Comparison")
            ax.grid(axis="y", alpha=0.3)

            # Add value labels
            for bar, size in zip(bars, sizes_mb, strict=False):
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f" {size:.2f} MB",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                )

            plt.xticks(rotation=45, ha="right")
            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting export formats: {e}")
            return None

    def to_mermaid_export_pipeline(self) -> str:
        """
        Mermaid diagram of the export pipeline (source → formats → files).

        Shows the flow from source artifacts through various export formats
        to final output files.

        Returns:
            Mermaid flowchart syntax.
        """
        lines = [
            "graph LR",
            '    A["Program<br/>Graph"]',
            '    B["GNN<br/>Bundle"]',
            '    C["State<br/>Space"]',
            '    D["Semantic<br/>Mappings"]',
            "",
            '    A --> E["Export<br/>Engine"]',
            "    B --> E",
            "    C --> E",
            "    D --> E",
            "",
            '    E --> F["JSON<br/>Export"]',
            '    E --> G["Markdown<br/>Export"]',
            '    E --> H["PNG<br/>Export"]',
            '    E --> I["PDF<br/>Export"]',
            '    E --> J["HTML<br/>Export"]',
            "",
            '    F --> K["model.json"]',
            '    G --> L["model.gnn.md"]',
            '    H --> M["*.png"]',
            '    I --> N["report.pdf"]',
            '    J --> O["index.html"]',
        ]

        return "\n".join(lines)

    def plot_bundle_composition(self, bundle: dict[str, Any]) -> Figure | None:
        """
        Pie chart of GNN bundle component sizes (matrices vs metadata vs roles).

        Shows the composition of a GNN bundle by component type and relative size.

        Args:
            bundle: Dict representing a GNN bundle with various components.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping bundle composition plot")
            return None

        try:
            if not bundle:
                logger.warning("No bundle data provided")
                return None

            # Estimate component sizes
            component_sizes: dict[str, float] = {}

            # Matrices
            matrices = ["A", "B", "C", "D"]
            matrix_size = 0
            for matrix_name in matrices:
                if matrix_name in bundle:
                    try:
                        import json

                        if isinstance(bundle[matrix_name], str):
                            matrix_size += len(bundle[matrix_name])
                        else:
                            matrix_size += len(json.dumps(bundle[matrix_name]))
                    except Exception:
                        matrix_size += 1000  # Default estimate

            if matrix_size > 0:
                component_sizes["Matrices (A/B/C/D)"] = matrix_size

            # Metadata
            metadata_size = 0
            if "metadata" in bundle:
                try:
                    import json

                    metadata_size = len(json.dumps(bundle["metadata"]))
                except Exception:
                    metadata_size = 500

            if metadata_size > 0:
                component_sizes["Metadata"] = metadata_size

            # Roles
            roles_size = 0
            if "roles" in bundle:
                try:
                    import json

                    roles_size = len(json.dumps(bundle["roles"]))
                except Exception:
                    roles_size = 500

            if roles_size > 0:
                component_sizes["Roles"] = roles_size

            # Mappings
            mappings_size = 0
            if "mappings" in bundle:
                try:
                    import json

                    mappings_size = len(json.dumps(bundle["mappings"]))
                except Exception:
                    mappings_size = 500

            if mappings_size > 0:
                component_sizes["Semantic Mappings"] = mappings_size

            # Other
            other_size = sum(
                len(str(v))
                for k, v in bundle.items()
                if k not in ["A", "B", "C", "D", "metadata", "roles", "mappings"]
            )
            if other_size > 0:
                component_sizes["Other"] = other_size

            if not component_sizes:
                logger.warning("Bundle has no measurable components")
                return None

            fig, ax = plt.subplots(figsize=(10, 8))

            labels = list(component_sizes.keys())
            sizes = list(component_sizes.values())

            colors = ["#FF9999", "#66B2FF", "#99FF99", "#FFCC99", "#FF99CC"]
            ax.pie(
                sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors[: len(labels)]
            )
            ax.set_title("GNN Bundle Composition: Component Sizes")

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting bundle composition: {e}")
            return None

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
