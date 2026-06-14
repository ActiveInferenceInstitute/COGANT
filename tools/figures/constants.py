"""Shared constants for manuscript figure promotion."""

from __future__ import annotations

from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parents[1]
COGANT_STAGING_ROOT = _TOOLS_DIR.parent
OUTPUT_FIGURES_DIR = COGANT_STAGING_ROOT / "output" / "figures"
FIGURE_MANIFEST_SCHEMA_VERSION = "1.2"
FIGURE_SIDECAR_SCHEMA_VERSION = "1.2"

_DEGRADED_RENDER_MARKERS = (
    "no " + "svg->png" + " backend available",
    "no " + "svg-png" + " backend available",
    "no " + "svg→png" + " backend available",
    "svg " + "rasterization (degraded)",
    "install cairosvg or rsvg-convert",
)
