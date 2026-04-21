"""
Pipeline stage visualization for COGANT's 10-stage processing pipeline.

Renders:
- Pipeline flowchart as Mermaid diagram
- Per-stage timing analysis as horizontal bar chart
- Stage outputs and key statistics as multi-panel figure
- Export to PNG and PDF
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PipelineVisualizer:
    """Visualize COGANT's pipeline stages, timing, and outputs."""

    def __init__(self) -> None:
        """Initialize the PipelineVisualizer."""
        pass

    def render_stage_diagram(self) -> str:
        """
        Render the 10-stage COGANT pipeline as a Mermaid flowchart.

        The 10 stages are:
        1. Ingest (parse source code)
        2. Parse (extract AST/tokens)
        3. Extract (identify symbols)
        4. Build (construct program graph)
        5. Translate (apply semantic rules)
        6. Markov (compute Markov blankets)
        7. StateSpace (compile state space)
        8. Export (generate GNN bundle)
        9. Validate (check constraints)
        10. Render (generate visualizations)

        Returns:
            Mermaid flowchart syntax as string.
        """
        lines = [
            "flowchart TD",
            '    A["1. Ingest<br/>Parse source files"]',
            '    B["2. Parse<br/>Extract AST/tokens"]',
            '    C["3. Extract<br/>Identify symbols"]',
            '    D["4. Build<br/>Construct program graph"]',
            '    E["5. Translate<br/>Apply semantic rules"]',
            '    F["6. Markov<br/>Compute blankets"]',
            '    G["7. StateSpace<br/>Compile state space"]',
            '    H["8. Export<br/>Generate GNN bundle"]',
            '    I["9. Validate<br/>Check constraints"]',
            '    J["10. Render<br/>Generate visualizations"]',
            "    A --> B",
            "    B --> C",
            "    C --> D",
            "    D --> E",
            "    E --> F",
            "    F --> G",
            "    G --> H",
            "    H --> I",
            "    I --> J",
        ]

        return "\n".join(lines)

    def render_timing_chart(self, timing_dict: dict[str, float]) -> Any:
        """
        Render per-stage timing as a horizontal bar chart.

        Args:
            timing_dict: Dict mapping stage names to elapsed time in seconds.
                Example: {"ingest": 0.5, "parse": 1.2, ...}

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping timing chart")
            return None

        try:
            fig, ax = plt.subplots(figsize=(12, 8))

            stages = list(timing_dict.keys())
            times = list(timing_dict.values())

            # Sort by time descending
            sorted_pairs = sorted(
                zip(stages, times, strict=False), key=lambda x: x[1], reverse=True
            )
            sorted_stages, sorted_times = (
                zip(*sorted_pairs, strict=False) if sorted_pairs else ([], [])
            )

            ax.barh(sorted_stages, sorted_times, color="steelblue", alpha=0.8)
            ax.set_xlabel("Time (seconds)")
            ax.set_title("Pipeline Stage Timing Analysis")
            ax.grid(axis="x", alpha=0.3)

            # Add value labels
            for idx, (_, time) in enumerate(zip(sorted_stages, sorted_times, strict=False)):
                ax.text(time, idx, f" {time:.2f}s", va="center", fontsize=10)

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error rendering timing chart: {e}")
            return None

    def render_stage_outputs(self, pipeline_result: Any) -> Any:
        """
        Render stage outputs as a 2×2 multi-panel figure showing key statistics.

        Extracts four metric series from ``pipeline_result`` and plots them:
        - Top-left: node count per stage (from ``node_counts`` / ``node_count_by_stage``)
        - Top-right: edge count per stage (from ``edge_counts`` / ``edge_count_by_stage``)
        - Bottom-left: rule firings per stage (from ``rule_firings``)
        - Bottom-right: validation finding counts (from ``validation_findings`` / ``findings``)

        If a metric series is absent in ``pipeline_result``, the panel shows
        a "No data" label rather than a placeholder title.

        Args:
            pipeline_result: Pipeline result dict or object with stage metrics.
                Recognised keys: ``node_counts``, ``node_count_by_stage``,
                ``edge_counts``, ``edge_count_by_stage``, ``rule_firings``,
                ``validation_findings``, ``findings``, ``stage_results``,
                ``stage_timings``, ``timing``.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping stage outputs plot")
            return None

        try:
            # Normalise to dict
            if isinstance(pipeline_result, dict):
                res = pipeline_result
            else:
                res = {
                    attr: getattr(pipeline_result, attr, None)
                    for attr in (
                        "node_counts",
                        "node_count_by_stage",
                        "edge_counts",
                        "edge_count_by_stage",
                        "rule_firings",
                        "validation_findings",
                        "findings",
                        "stage_results",
                        "stage_timings",
                        "timing",
                    )
                }

            # Extract per-stage metric dicts (fall back to stage_results internals)
            def _metric_series(primary: str, alt: str, sub_key: str) -> dict[str, float]:
                data = res.get(primary) or res.get(alt)
                if isinstance(data, dict):
                    return {k: float(v) for k, v in data.items()}
                # Try to pull from nested stage_results
                stage_results: dict[str, Any] = res.get("stage_results") or {}
                out: dict[str, float] = {}
                for stage, sr in stage_results.items():
                    if isinstance(sr, dict) and sub_key in sr:
                        try:
                            out[stage] = float(sr[sub_key])
                        except (TypeError, ValueError):
                            pass
                return out

            def _finding_series() -> dict[str, float]:
                findings = res.get("validation_findings") or res.get("findings")
                if isinstance(findings, dict):
                    return {
                        k: float(v if not isinstance(v, list) else len(v))
                        for k, v in findings.items()
                    }
                if isinstance(findings, list):
                    return {"total": float(len(findings))}
                stage_results: dict[str, Any] = res.get("stage_results") or {}
                out: dict[str, float] = {}
                for stage, sr in stage_results.items():
                    if isinstance(sr, dict):
                        f = sr.get("findings") or sr.get("validation_findings")
                        if isinstance(f, list):
                            out[stage] = float(len(f))
                        elif isinstance(f, (int, float)):
                            out[stage] = float(f)
                return out

            node_data = _metric_series("node_counts", "node_count_by_stage", "node_count")
            edge_data = _metric_series("edge_counts", "edge_count_by_stage", "edge_count")
            rule_data = _metric_series("rule_firings", "rule_firings", "rule_firings")
            find_data = _finding_series()

            def _bar_panel(ax: Any, data: dict[str, float], title: str, color: str) -> None:
                if data:
                    stages = list(data.keys())
                    values = [data[s] for s in stages]
                    ax.barh(stages, values, color=color, alpha=0.8)
                    for idx, v in enumerate(values):
                        ax.text(v, idx, f"  {int(v)}", va="center", fontsize=8)
                    ax.set_xlabel("Count")
                    ax.grid(axis="x", alpha=0.3)
                else:
                    ax.text(
                        0.5, 0.5, "No data", ha="center", va="center", fontsize=11, color="#AAAAAA"
                    )
                    ax.set_xlim(0, 1)
                    ax.set_ylim(0, 1)
                    ax.axis("off")
                ax.set_title(title, fontsize=11, weight="bold")

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            _bar_panel(axes[0, 0], node_data, "Node Count by Stage", "#4C72B0")
            _bar_panel(axes[0, 1], edge_data, "Edge Count by Stage", "#55A868")
            _bar_panel(axes[1, 0], rule_data, "Rule Firings", "#DD8452")
            _bar_panel(axes[1, 1], find_data, "Validation Findings", "#C44E52")

            fig.suptitle("Pipeline Stage Outputs", fontsize=16, weight="bold")
            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error("Error rendering stage outputs: %s", e)
            return None

    def to_mermaid_pipeline(self) -> str:
        """
        Render the pipeline as a Mermaid diagram with stage descriptions.

        Returns:
            Mermaid ``flowchart TD`` source as a string. Each stage
            node carries a bold title and a multi-line description.
        """
        lines = [
            "flowchart TD",
            '    A["<b>1. Ingest</b><br/>Parse source files<br/>from repository"]',
            '    B["<b>2. Parse</b><br/>Extract AST and<br/>token streams"]',
            '    C["<b>3. Extract</b><br/>Identify symbols,<br/>definitions"]',
            '    D["<b>4. Build</b><br/>Construct program graph<br/>with edges"]',
            '    E["<b>5. Translate</b><br/>Apply 22 semantic<br/>translation rules"]',
            '    F["<b>6. Markov</b><br/>Compute Markov blanket<br/>partitions"]',
            '    G["<b>7. StateSpace</b><br/>Compile hidden states,<br/>observations, actions"]',
            '    H["<b>8. Export</b><br/>Generate GNN markdown<br/>bundle"]',
            '    I["<b>9. Validate</b><br/>Check AII constraints<br/>and findings"]',
            '    J["<b>10. Render</b><br/>Generate PNG, PDF,<br/>interactive HTML"]',
            "    A --> B",
            "    B --> C",
            "    C --> D",
            "    D --> E",
            "    E --> F",
            "    F --> G",
            "    G --> H",
            "    H --> I",
            "    I --> J",
        ]

        return "\n".join(lines)

    def to_png(self, output_path: str) -> str:
        """
        Render the pipeline diagram to PNG.

        Requires matplotlib and mermaid renderer. Falls back gracefully if unavailable.

        Args:
            output_path: Path to write PNG file.

        Returns:
            Path to rendered file, or empty string if unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.patches import FancyBboxPatch
        except ImportError:
            logger.warning("matplotlib not available; skipping PNG render")
            return ""

        try:
            fig, ax = plt.subplots(figsize=(12, 10))

            # Draw simple box representation of pipeline
            stages = [
                "Ingest",
                "Parse",
                "Extract",
                "Build",
                "Translate",
                "Markov",
                "StateSpace",
                "Export",
                "Validate",
                "Render",
            ]

            y_pos = 0.9
            for i, stage in enumerate(stages):
                color = "lightblue" if i % 2 == 0 else "lightgreen"
                box = FancyBboxPatch(
                    (0.1, y_pos - 0.08),
                    0.8,
                    0.07,
                    boxstyle="round,pad=0.01",
                    edgecolor="black",
                    facecolor=color,
                    linewidth=2,
                )
                ax.add_patch(box)
                ax.text(
                    0.5, y_pos - 0.045, f"{i + 1}. {stage}", ha="center", va="center", fontsize=11
                )

                if i < len(stages) - 1:
                    ax.arrow(
                        0.5,
                        y_pos - 0.08,
                        0,
                        -0.02,
                        head_width=0.05,
                        head_length=0.01,
                        fc="black",
                        ec="black",
                    )

                y_pos -= 0.09

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            ax.set_title("COGANT Pipeline Stages", fontsize=16, weight="bold", pad=20)

            fig.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Rendered pipeline diagram to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error rendering PNG: {e}")
            return ""

    def to_pdf(self, output_path: str) -> str:
        """
        Render the pipeline diagram to PDF.

        Args:
            output_path: Path to write PDF file.

        Returns:
            Path to rendered file, or empty string if unavailable.
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.patches import FancyBboxPatch
        except ImportError:
            logger.warning("matplotlib not available; skipping PDF render")
            return ""

        try:
            fig, ax = plt.subplots(figsize=(12, 10))

            # Draw simple box representation of pipeline
            stages = [
                "Ingest",
                "Parse",
                "Extract",
                "Build",
                "Translate",
                "Markov",
                "StateSpace",
                "Export",
                "Validate",
                "Render",
            ]

            y_pos = 0.9
            for i, stage in enumerate(stages):
                color = "lightblue" if i % 2 == 0 else "lightgreen"
                box = FancyBboxPatch(
                    (0.1, y_pos - 0.08),
                    0.8,
                    0.07,
                    boxstyle="round,pad=0.01",
                    edgecolor="black",
                    facecolor=color,
                    linewidth=2,
                )
                ax.add_patch(box)
                ax.text(
                    0.5, y_pos - 0.045, f"{i + 1}. {stage}", ha="center", va="center", fontsize=11
                )

                if i < len(stages) - 1:
                    ax.arrow(
                        0.5,
                        y_pos - 0.08,
                        0,
                        -0.02,
                        head_width=0.05,
                        head_length=0.01,
                        fc="black",
                        ec="black",
                    )

                y_pos -= 0.09

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            ax.set_title("COGANT Pipeline Stages", fontsize=16, weight="bold", pad=20)

            fig.savefig(output_path, format="pdf", bbox_inches="tight")
            plt.close(fig)

            logger.info(f"Rendered pipeline diagram to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error rendering PDF: {e}")
            return ""

    def render_dataflow_diagram(self) -> str:
        """
        Render a Mermaid diagram showing data flow between the 10 pipeline stages.

        Shows what each stage consumes and produces.

        Returns:
            Mermaid flowchart syntax showing data flow.
        """
        lines = [
            "graph TD",
            '    A["<b>1. Ingest</b><br/>Input: Source files"]',
            '    B["<b>2. Parse</b><br/>Input: Raw source<br/>Output: AST/tokens"]',
            '    C["<b>3. Extract</b><br/>Input: AST<br/>Output: Symbols"]',
            '    D["<b>4. Build</b><br/>Input: Symbols<br/>Output: Graph"]',
            '    E["<b>5. Translate</b><br/>Input: Graph<br/>Output: Semantic roles"]',
            '    F["<b>6. Markov</b><br/>Input: Semantic roles<br/>Output: Partitions"]',
            '    G["<b>7. StateSpace</b><br/>Input: Partitions<br/>Output: States/Obs/Acts"]',
            '    H["<b>8. Export</b><br/>Input: State space<br/>Output: GNN bundle"]',
            '    I["<b>9. Validate</b><br/>Input: GNN bundle<br/>Output: Findings"]',
            '    J["<b>10. Render</b><br/>Input: All artifacts<br/>Output: PNG/PDF/HTML"]',
            "    A --> B",
            "    B --> C",
            "    C --> D",
            "    D --> E",
            "    E --> F",
            "    F --> G",
            "    G --> H",
            "    H --> I",
            "    I --> J",
        ]

        return "\n".join(lines)

    def plot_stage_memory_usage(self, memory_dict: dict[str, float]) -> Any:
        """
        Bar chart of memory usage per stage.

        Visualizes peak memory consumption for each pipeline stage in MB.

        Args:
            memory_dict: Dict mapping stage names to memory usage in bytes.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping memory usage plot")
            return None

        try:
            if not memory_dict:
                logger.warning("No memory data provided")
                return None

            fig, ax = plt.subplots(figsize=(12, 6))

            stages = list(memory_dict.keys())
            memory_mb = [v / (1024 * 1024) for v in memory_dict.values()]  # Convert to MB

            # Sort by memory descending
            sorted_pairs = sorted(
                zip(stages, memory_mb, strict=False), key=lambda x: x[1], reverse=True
            )
            stages_sorted, memory_sorted = (
                zip(*sorted_pairs, strict=False) if sorted_pairs else ([], [])
            )

            bars = ax.barh(stages_sorted, memory_sorted, color="steelblue", alpha=0.7)
            ax.set_xlabel("Memory (MB)")
            ax.set_title("Pipeline Stage Memory Usage Analysis")
            ax.grid(axis="x", alpha=0.3)

            # Add value labels
            for bar, memory in zip(bars, memory_sorted, strict=False):
                width = bar.get_width()
                ax.text(
                    width,
                    bar.get_y() + bar.get_height() / 2,
                    f" {memory:.1f} MB",
                    va="center",
                    fontsize=10,
                )

            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error plotting memory usage: {e}")
            return None

    def render_stage_grid(self, results: dict[str, Any]) -> Any:
        """
        2x5 grid of mini-charts, one per stage, showing key stats.

        Each mini-chart shows stage-specific metrics (node count, edge count, etc.).

        Args:
            results: Dict with stage names as keys and stage results as values.

        Returns:
            Matplotlib Figure object, or None if matplotlib unavailable.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not available; skipping stage grid plot")
            return None

        try:
            fig, axes = plt.subplots(2, 5, figsize=(16, 8))
            axes_flat = axes.flatten()

            stages = [
                "Ingest",
                "Parse",
                "Extract",
                "Build",
                "Translate",
                "Markov",
                "StateSpace",
                "Export",
                "Validate",
                "Render",
            ]

            for idx, (ax, stage) in enumerate(zip(axes_flat, stages, strict=False)):
                stage_result = results.get(stage, {})

                if isinstance(stage_result, dict):
                    metrics = stage_result.get("metrics", {})
                    if metrics:
                        # Simple bar chart per stage
                        metric_names = list(metrics.keys())[:3]  # Top 3 metrics
                        metric_values = [metrics[m] for m in metric_names]

                        ax.bar(
                            range(len(metric_names)), metric_values, color="steelblue", alpha=0.7
                        )
                        ax.set_xticks(range(len(metric_names)))
                        ax.set_xticklabels(metric_names, rotation=45, ha="right", fontsize=8)
                        ax.set_ylabel("Value")
                        ax.set_title(f"Stage {idx + 1}: {stage}", fontsize=10, weight="bold")
                        ax.grid(axis="y", alpha=0.3)
                    else:
                        ax.text(
                            0.5, 0.5, f"{stage}\n(no data)", ha="center", va="center", fontsize=10
                        )
                        ax.set_xlim(0, 1)
                        ax.set_ylim(0, 1)
                else:
                    ax.text(0.5, 0.5, f"{stage}", ha="center", va="center", fontsize=10)
                    ax.set_xlim(0, 1)
                    ax.set_ylim(0, 1)

                ax.axis("off")

            fig.suptitle("Pipeline Stage Analysis: Key Statistics", fontsize=14, weight="bold")
            fig.tight_layout()
            return fig

        except Exception as e:
            logger.error(f"Error rendering stage grid: {e}")
            return None
