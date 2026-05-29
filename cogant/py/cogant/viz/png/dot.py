from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def render_graphviz_dot_to_png(dot_file: Path, output_png: Path, *, timeout: int = 120) -> bool:
    """Render a Graphviz ``.dot`` file to PNG using the ``dot`` binary if available."""
    dot_bin = shutil.which("dot")
    if not dot_bin:
        logger.warning("Graphviz ``dot`` not on PATH; skip %s", dot_file.name)
        return False
    if not dot_file.is_file():
        return False
    output_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [dot_bin, "-Tpng", str(dot_file), "-o", str(output_png)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
        return output_png.is_file()
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
        logger.warning("Graphviz render failed for %s: %s", dot_file.name, e)
        return False


def render_all_dot_in_run(run_dir: Path) -> list[Path]:
    """Render every ``.dot`` under ``run_dir`` to a sibling ``.png`` via dot/Graphviz."""
    written: list[Path] = []
    if not shutil.which("dot"):
        return written
    for dot in sorted(run_dir.rglob("*.dot")):
        png = dot.with_suffix(".png")
        try:
            if render_graphviz_dot_to_png(dot, png):
                written.append(png)
        except Exception as e:  # noqa: BLE001
            logger.warning("dot→PNG failed for %s: %s", dot.name, e)
    return written


def find_graph_dot(run_dir: Path) -> Path | None:
    """Return path to ``graph.dot`` under ``diagrams/`` or run root."""
    for candidate in (run_dir / "diagrams" / "graph.dot", run_dir / "graph.dot"):
        if candidate.is_file():
            return candidate
    return None
