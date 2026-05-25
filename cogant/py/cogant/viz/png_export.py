"""Backward-compatible re-export shim for PNG raster exports.

Implementation lives in :mod:`cogant.viz.png`; this module preserves legacy
``from cogant.viz.png_export import ...`` import paths.
"""

from __future__ import annotations

from cogant.viz.png import (
    DEFAULT_CONFIG,
    FIGURE_SIDECAR_SCHEMA_VERSION,
    RenderConfig,
    find_graph_dot,
    program_graph_dict_to_networkx,
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
from cogant.viz.png.config import (
    downsample_graph as _downsample_graph,
    truncate as _truncate,
)
from cogant.viz.png.discovery import read_json as _read_json
from cogant.viz.png.gnn_markdown import _split_gnn_markdown
from cogant.viz.png.mermaid import (
    _detect_mermaid_kind,
    _mmdc_command,
    _parse_mermaid_class_diagram,
    _parse_mermaid_flowchart,
    _parse_mermaid_gantt,
    _parse_mermaid_sequence,
    _parse_mermaid_state_diagram,
)
from cogant.viz.png.program_graph import _build_kind_legend, _kind_color

# Legacy private alias used in tests and introspection.
_DEFAULT_CONFIG = DEFAULT_CONFIG

__all__ = [
    "DEFAULT_CONFIG",
    "FIGURE_SIDECAR_SCHEMA_VERSION",
    "RenderConfig",
    "_DEFAULT_CONFIG",
    "_build_kind_legend",
    "_detect_mermaid_kind",
    "_downsample_graph",
    "_kind_color",
    "_mmdc_command",
    "_parse_mermaid_class_diagram",
    "_parse_mermaid_flowchart",
    "_parse_mermaid_gantt",
    "_parse_mermaid_sequence",
    "_parse_mermaid_state_diagram",
    "_read_json",
    "_split_gnn_markdown",
    "_truncate",
    "find_graph_dot",
    "program_graph_dict_to_networkx",
    "render_all_dot_in_run",
    "render_all_mermaid_in_run",
    "render_all_pngs",
    "render_all_svg_in_run",
    "render_connections_matrix_png",
    "render_gnn_markdown_png",
    "render_graphviz_dot_to_png",
    "render_interpretability_overview_png",
    "render_markov_blanket_png",
    "render_mermaid_file_to_png",
    "render_mermaid_text_to_png",
    "render_process_gantt_png",
    "render_program_graph_png",
    "render_state_space_factor_png",
    "render_summary_cover_png",
    "render_svg_file_to_png",
]
