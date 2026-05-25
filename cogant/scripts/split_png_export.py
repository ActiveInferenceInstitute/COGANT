#!/usr/bin/env python3
"""One-shot mechanical split of viz/png_export.py into viz/png/* package."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "py/cogant/viz/png_export.py"
OUT = ROOT / "py/cogant/viz/png"

COMMON_HEADER = '''from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from cogant.viz.png.config import (
    DEFAULT_CONFIG,
    RenderConfig,
    draw_color_legend,
    draw_footer,
    draw_metadata_banner,
    downsample_graph,
    sha256_file,
    truncate,
    timestamp,
    write_figure_sidecar,
)

logger = logging.getLogger(__name__)
'''

SECTIONS: list[tuple[str, int, int, str]] = [
    (
        "config.py",
        71,
        348,
        '''from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
FIGURE_SIDECAR_SCHEMA_VERSION = "1.2"


''',
    ),
    ("program_graph.py", 354, 974, COMMON_HEADER),
    ("mermaid.py", 980, 1995, COMMON_HEADER),
    ("svg.py", 2001, 2136, COMMON_HEADER),
    ("dot.py", 2142, 2182, COMMON_HEADER),
    ("state_space.py", 2188, 2696, COMMON_HEADER),
    ("process_gantt.py", 2702, 2837, COMMON_HEADER),
    ("markov_blanket.py", 2842, 3228, COMMON_HEADER),
    ("summary.py", 3234, 3629, COMMON_HEADER + """
from cogant.viz.png.discovery import discover_state_space_json, read_json

"""),
    ("gnn_markdown.py", 3635, 3790, COMMON_HEADER),
    ("discovery.py", 3796, 3870, COMMON_HEADER),
    (
        "orchestrator.py",
        3873,
        4081,
        COMMON_HEADER
        + """
from cogant.viz.png.discovery import (
    discover_process_model_json,
    discover_state_space_json,
    first_existing,
    load_process_model_from_json,
    load_state_space_from_json,
)
from cogant.viz.png.dot import render_all_dot_in_run
from cogant.viz.png.gnn_markdown import render_gnn_markdown_png
from cogant.viz.png.markov_blanket import render_markov_blanket_png
from cogant.viz.png.mermaid import render_all_mermaid_in_run
from cogant.viz.png.process_gantt import render_process_gantt_png
from cogant.viz.png.program_graph import render_program_graph_png
from cogant.viz.png.state_space import (
    render_connections_matrix_png,
    render_state_space_factor_png,
)
from cogant.viz.png.summary import (
    render_interpretability_overview_png,
    render_summary_cover_png,
)
from cogant.viz.png.svg import render_all_svg_in_run

""",
    ),
]


def _rename_private(body: str) -> str:
    """Expose config helpers without leading underscore for cross-module use."""
    replacements = {
        "_DEFAULT_CONFIG": "DEFAULT_CONFIG",
        "_truncate": "truncate",
        "_timestamp": "timestamp",
        "_sha256_file": "sha256_file",
        "_write_figure_sidecar": "write_figure_sidecar",
        "_downsample_graph": "downsample_graph",
        "_draw_metadata_banner": "draw_metadata_banner",
        "_draw_footer": "draw_footer",
        "_draw_color_legend": "draw_color_legend",
        "_discover_state_space_json": "discover_state_space_json",
        "_discover_process_model_json": "discover_process_model_json",
        "_load_state_space_from_json": "load_state_space_from_json",
        "_load_process_model_from_json": "load_process_model_from_json",
        "_first_existing": "first_existing",
        "_read_json": "read_json",
    }
    for old, new in replacements.items():
        body = body.replace(old, new)
    return body


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    OUT.mkdir(parents=True, exist_ok=True)

    for filename, start, end, header in SECTIONS:
        chunk = "".join(lines[start - 1 : end])
        if filename == "config.py":
            chunk = _rename_private(chunk)
            # Keep public names; rename defs to drop leading underscore
            chunk = chunk.replace("def truncate", "def truncate")
        else:
            chunk = _rename_private(chunk)
        (OUT / filename).write_text(header + chunk, encoding="utf-8")

    init = '''"""PNG raster export subpackage — split from monolithic png_export.py."""

from cogant.viz.png.config import DEFAULT_CONFIG, FIGURE_SIDECAR_SCHEMA_VERSION, RenderConfig
from cogant.viz.png.discovery import (
    discover_process_model_json,
    discover_state_space_json,
    first_existing,
    load_process_model_from_json,
    load_state_space_from_json,
    read_json,
)
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

__all__ = [
    "DEFAULT_CONFIG",
    "FIGURE_SIDECAR_SCHEMA_VERSION",
    "RenderConfig",
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
'''
    (OUT / "__init__.py").write_text(init, encoding="utf-8")

    shim = '''"""Backward-compatible re-export shim for PNG raster exports.

Implementation lives in :mod:`cogant.viz.png`; this module preserves legacy
``from cogant.viz.png_export import ...`` import paths.
"""

from cogant.viz.png import *  # noqa: F403
from cogant.viz.png import __all__ as __all__
'''
    SRC.write_text(shim, encoding="utf-8")
    print(f"Split {SRC} into {OUT}/ ({len(SECTIONS)} modules)")


if __name__ == "__main__":
    main()
