"""Compatibility wrapper for artifact-first inspection dashboard helpers.

The implementation is split across :mod:`cogant.viz.inspection` modules; this
module preserves the original public import path.
"""

from __future__ import annotations

from cogant.viz.inspection.abstract import (
    render_graphical_abstract_png,
    render_graphical_abstract_svg,
)
from cogant.viz.inspection.details import render_interpretability_detail_pngs
from cogant.viz.inspection.html import render_inspection_dashboard_html
from cogant.viz.inspection.model import build_inspection_model
from cogant.viz.inspection.writer import write_inspection_artifacts

__all__ = [
    "build_inspection_model",
    "render_graphical_abstract_png",
    "render_graphical_abstract_svg",
    "render_interpretability_detail_pngs",
    "render_inspection_dashboard_html",
    "write_inspection_artifacts",
]
