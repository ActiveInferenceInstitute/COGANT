"""COGANT Visualization: Graph views, semantic models, interactive HTML, and PNG raster exports."""

from __future__ import annotations

from cogant.viz.ablation_view import render_ablation_png
from cogant.viz.batch_dashboard import (
    BatchDashboardGenerator,
    TargetMetrics,
    write_batch_dashboard,
)
from cogant.viz.boundary import BoundaryMapper
from cogant.viz.dashboard import DashboardGenerator
from cogant.viz.diff_view import DiffVisualizer
from cogant.viz.export_view import ExportView
from cogant.viz.flow import CallGraph, ControlFlowGraph, DependencyGraph, FlowDiagrammer
from cogant.viz.gantt import GanttRenderer
from cogant.viz.graph_view import GraphVisualizer
from cogant.viz.html_renderer import HTMLSiteRenderer
from cogant.viz.inspection_dashboard import (
    build_inspection_model,
    render_graphical_abstract_png,
    render_graphical_abstract_svg,
    render_inspection_dashboard_html,
    write_inspection_artifacts,
)
from cogant.viz.matrix_view import MatrixVisualizer
from cogant.viz.mermaid import MermaidGenerator
from cogant.viz.network_view import NetworkView
from cogant.viz.pdf_export import PDFExporter
from cogant.viz.pipeline_view import PipelineVisualizer
from cogant.viz.plots import StaticPlotter
from cogant.viz.png import (
    RenderConfig,
    render_all_dot_in_run,
    render_all_mermaid_in_run,
    render_all_pngs,
    render_all_svg_in_run,
    render_connections_matrix_png,
    render_gnn_markdown_png,
    render_graphviz_dot_to_png,
    render_interpretability_overview_png,
    render_markov_blanket_png,
    render_mermaid_file_to_png,
    render_mermaid_text_to_png,
    render_process_gantt_png,
    render_program_graph_png,
    render_state_space_factor_png,
    render_summary_cover_png,
    render_svg_file_to_png,
)
from cogant.viz.semantic_view import SemanticVisualizer
from cogant.viz.static_analysis_view import StaticAnalysisView

__all__ = [
    "GraphVisualizer",
    "SemanticVisualizer",
    "GanttRenderer",
    "DiffVisualizer",
    "HTMLSiteRenderer",
    "MermaidGenerator",
    "StaticPlotter",
    "BoundaryMapper",
    "DashboardGenerator",
    "build_inspection_model",
    "render_graphical_abstract_png",
    "render_graphical_abstract_svg",
    "render_inspection_dashboard_html",
    "write_inspection_artifacts",
    # Batch dashboard (cross-target consolidation)
    "BatchDashboardGenerator",
    "TargetMetrics",
    "write_batch_dashboard",
    # Flow diagrams
    "FlowDiagrammer",
    "ControlFlowGraph",
    "CallGraph",
    "DependencyGraph",
    # Matrix visualization
    "MatrixVisualizer",
    # PDF export
    "PDFExporter",
    # Pipeline visualization
    "PipelineVisualizer",
    # Static analysis visualization
    "StaticAnalysisView",
    # Network analysis visualization
    "NetworkView",
    # Export and format visualization
    "ExportView",
    # PNG raster exports
    "RenderConfig",
    "render_all_pngs",
    "render_program_graph_png",
    "render_mermaid_file_to_png",
    "render_mermaid_text_to_png",
    "render_all_mermaid_in_run",
    "render_svg_file_to_png",
    "render_all_svg_in_run",
    "render_graphviz_dot_to_png",
    "render_all_dot_in_run",
    "render_state_space_factor_png",
    "render_connections_matrix_png",
    "render_process_gantt_png",
    "render_markov_blanket_png",
    "render_interpretability_overview_png",
    "render_summary_cover_png",
    "render_gnn_markdown_png",
    "render_ablation_png",
]
