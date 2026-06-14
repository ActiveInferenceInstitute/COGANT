from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from cogant.viz.png.config import (
    DEFAULT_CONFIG,
    RenderConfig,
    draw_footer,
    draw_metadata_banner,
)

logger = logging.getLogger(__name__)


def render_svg_file_to_png(svg_file: Path, output_png: Path, *, timeout: int = 60) -> bool:
    """Convert an SVG file to PNG.

    Preference order:
      1. ``cairosvg`` (pure-Python, no external binary).
      2. ``rsvg-convert`` binary.
      3. ``inkscape`` binary.
      4. ImageMagick ``convert`` binary.
    Returns ``True`` on success.
    """
    if not svg_file.is_file():
        return False
    output_png.parent.mkdir(parents=True, exist_ok=True)

    # 1) cairosvg
    try:
        import cairosvg  # type: ignore[import-not-found,unused-ignore]

        cairosvg.svg2png(url=str(svg_file), write_to=str(output_png), output_width=1400)
        if output_png.is_file():
            return True
    except Exception:
        pass

    if os.environ.get("COGANT_USE_EXTERNAL_SVG_CONVERTERS") != "1":
        logger.debug(
            "External SVG converters disabled for %s; using degraded companion if requested",
            svg_file.name,
        )
        return False

    # 2) rsvg-convert
    if shutil.which("rsvg-convert"):
        cmd = ["rsvg-convert", "-w", "1400", "-o", str(output_png), str(svg_file)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
            if output_png.is_file():
                return True
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
            logger.debug("rsvg-convert failed for %s: %s", svg_file.name, e)

    # 3) inkscape
    if shutil.which("inkscape"):
        cmd = [
            "inkscape",
            str(svg_file),
            "--export-type=png",
            f"--export-filename={output_png}",
            "--export-width=1400",
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
            if output_png.is_file():
                return True
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
            logger.debug("inkscape failed for %s: %s", svg_file.name, e)

    # 4) ImageMagick convert
    if shutil.which("convert"):
        cmd = ["convert", "-density", "150", str(svg_file), str(output_png)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
            if output_png.is_file():
                return True
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
            logger.debug("ImageMagick convert failed for %s: %s", svg_file.name, e)

    logger.debug("No SVG→PNG backend succeeded for %s", svg_file.name)
    return False


def render_all_svg_in_run(run_dir: Path) -> list[Path]:
    """Convert every ``.svg`` under ``run_dir`` to a sibling ``.png``.

    If no native SVG backend is available, uses a matplotlib-based degraded
    companion image carrying the same banner/metadata shell so the run still
    yields one PNG per SVG.
    """
    written: list[Path] = []
    for svg in sorted(run_dir.rglob("*.svg")):
        png = svg.with_suffix(".png")
        try:
            if render_svg_file_to_png(svg, png):
                written.append(png)
            elif render_svg_degraded_png(svg, png):
                written.append(png)
        except Exception as e:  # noqa: BLE001
            logger.warning("SVG→PNG failed for %s: %s", svg.name, e)
    return written


def render_svg_degraded_png(
    svg_file: Path,
    output_png: Path,
    *,
    cfg: RenderConfig | None = None,
) -> bool:
    """When no SVG backend exists, emit a matplotlib degraded companion image."""
    cfg = cfg or DEFAULT_CONFIG
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    try:
        size = svg_file.stat().st_size if svg_file.is_file() else 0
    except OSError:
        size = 0

    fig, ax = plt.subplots(figsize=cfg.figsize)
    ax.set_axis_off()
    draw_metadata_banner(
        ax,
        title=svg_file.stem.replace("_", " ").title(),
        subtitle="vector conversion (degraded)",
        stats={"bytes": size, "format": "svg"},
        cfg=cfg,
    )
    ax.text(
        0.5,
        0.5,
        "No SVG→PNG backend available.\nInstall cairosvg or rsvg-convert to rasterize.",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=cfg.node_fontsize,
        color="#555555",
        bbox={
            "boxstyle": "round,pad=0.6",
            "facecolor": "#f0f2f5",
            "edgecolor": "#cccccc",
        },
    )
    draw_footer(fig, source=svg_file.name, cfg=cfg)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=cfg.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_png.is_file()


# Backward-compatible alias for callers not yet migrated.
_render_svg_placeholder_png = render_svg_degraded_png
