from collections.abc import Mapping
from typing import Any

from cogant.viz.flow import FlowDiagrammer as FlowDiagrammer
from cogant.viz.inspection_dashboard import build_inspection_model as build_inspection_model
from cogant.viz.inspection_dashboard import (
    render_graphical_abstract_png as render_graphical_abstract_png,
)
from cogant.viz.inspection_dashboard import (
    render_graphical_abstract_svg as render_graphical_abstract_svg,
)
from cogant.viz.inspection_dashboard import (
    render_inspection_dashboard_html as render_inspection_dashboard_html,
)
from cogant.viz.inspection_dashboard import write_inspection_artifacts as write_inspection_artifacts
from cogant.viz.matrix_view import MatrixVisualizer as MatrixVisualizer
from cogant.viz.pdf_export import PDFExporter as PDFExporter
from cogant.viz.pipeline_view import PipelineVisualizer as PipelineVisualizer

__all__ = [
    "FlowDiagrammer",
    "GraphToMermaid",
    "MatrixVisualizer",
    "PDFExporter",
    "PipelineVisualizer",
    "build_inspection_model",
    "render_graphical_abstract_png",
    "render_graphical_abstract_svg",
    "render_inspection_dashboard_html",
    "write_inspection_artifacts",
]

class GraphToMermaid:
    def graph_to_mermaid(self, graph: Mapping[str, Any]) -> str: ...
