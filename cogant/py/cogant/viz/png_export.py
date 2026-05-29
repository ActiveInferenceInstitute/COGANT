"""Backward-compatible re-export shim for PNG raster exports.

Implementation lives in :mod:`cogant.viz.png`; this module preserves legacy
``from cogant.viz.png_export import ...`` import paths.
"""

from __future__ import annotations

import shutil
import subprocess

from cogant.viz.png.config import DEFAULT_CONFIG, FIGURE_SIDECAR_SCHEMA_VERSION, RenderConfig
from cogant.viz.png.dot import find_graph_dot, render_all_dot_in_run, render_graphviz_dot_to_png
from cogant.viz.png.gnn_markdown import render_gnn_markdown_png
from cogant.viz.png.markov_blanket import render_markov_blanket_png
from cogant.viz.png.mermaid import (
    render_all_mermaid_in_run,
    render_mermaid_file_to_png,
    render_mermaid_text_to_png,
)
from cogant.viz.png.orchestrator import render_all_pngs
from cogant.viz.png.process_gantt import render_process_gantt_png
from cogant.viz.png.program_graph import program_graph_dict_to_networkx, render_program_graph_png
from cogant.viz.png.state_space import render_connections_matrix_png, render_state_space_factor_png
from cogant.viz.png.summary import render_interpretability_overview_png, render_summary_cover_png
from cogant.viz.png.svg import render_all_svg_in_run, render_svg_file_to_png
from cogant.viz.png.config import (
    downsample_graph as _downsample_graph,
)
from cogant.viz.png.config import (
    truncate as _truncate,
)
from cogant.viz.png.discovery import (
    discover_process_model_json as _discover_process_model_json,
)
from cogant.viz.png.discovery import (
    discover_state_space_json as _discover_state_space_json,
)
from cogant.viz.png.discovery import (
    load_process_model_from_json as _load_process_model_from_json,
)
from cogant.viz.png.discovery import (
    load_state_space_from_json as _load_state_space_from_json,
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
from cogant.viz.png.svg import _render_svg_placeholder_png

# Legacy private alias used in tests and introspection.
_DEFAULT_CONFIG = DEFAULT_CONFIG

__all__ = [
    "DEFAULT_CONFIG",
    "FIGURE_SIDECAR_SCHEMA_VERSION",
    "RenderConfig",
    "_DEFAULT_CONFIG",
    "_build_kind_legend",
    "_discover_process_model_json",
    "_discover_state_space_json",
    "_detect_mermaid_kind",
    "_downsample_graph",
    "_kind_color",
    "_load_process_model_from_json",
    "_load_state_space_from_json",
    "_mmdc_command",
    "_parse_mermaid_class_diagram",
    "_parse_mermaid_flowchart",
    "_parse_mermaid_gantt",
    "_parse_mermaid_sequence",
    "_parse_mermaid_state_diagram",
    "_read_json",
    "_render_svg_placeholder_png",
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
    "shutil",
    "subprocess",
]
