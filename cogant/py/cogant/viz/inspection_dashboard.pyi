from __future__ import annotations

from pathlib import Path
from typing import Any

__all__: list[str]

def build_inspection_model(run_dir: Path | str) -> dict[str, Any]: ...
def render_graphical_abstract_svg(
    run_dir: Path | str,
    output_svg: Path | str | None = ...,
) -> Path: ...
def render_graphical_abstract_png(
    run_dir: Path | str,
    output_png: Path | str | None = ...,
    *,
    output_svg: Path | str | None = ...,
) -> Path | None: ...
def render_interpretability_detail_pngs(run_dir: Path | str) -> dict[str, Path]: ...
def render_inspection_dashboard_html(
    run_dir: Path | str,
    output_html: Path | str | None = ...,
    *,
    embed_assets: bool = ...,
) -> Path: ...
def write_inspection_artifacts(
    run_dir: Path | str,
    *,
    dashboard_html: Path | str | None = ...,
    graphical_abstract_svg: Path | str | None = ...,
    graphical_abstract_png: Path | str | None = ...,
    embed_assets: bool = ...,
) -> dict[str, Path]: ...
