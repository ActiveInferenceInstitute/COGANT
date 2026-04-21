"""Generate PNG figures for COGANT pipeline output directories."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from cogant.viz.png_export import (
    find_graph_dot,
    render_all_mermaid_in_run,
    render_graphviz_dot_to_png,
    render_program_graph_png,
)

logger = logging.getLogger(__name__)


def _has_program_graph(d: Path) -> bool:
    return (d / "program_graph.json").is_file() or (d / "data" / "program_graph.json").is_file()


def _discover_run_dirs(path: Path) -> list[Path]:
    """Return concrete run directories to render (one or many)."""
    path = path.resolve()
    if not path.is_dir():
        return []

    ex_cp = path / "examples" / "control_positive"
    if ex_cp.is_dir():
        runs = sorted(
            d
            for d in ex_cp.iterdir()
            if d.is_dir() and not d.name.startswith(".") and _has_program_graph(d)
        )
        if runs:
            return runs

    subdirs = sorted(d for d in path.iterdir() if d.is_dir() and not d.name.startswith("."))
    if subdirs and all(_has_program_graph(d) for d in subdirs):
        return subdirs

    if _has_program_graph(path):
        return [path]
    return []


def _process_run_dir(run_dir: Path) -> int:
    pg = run_dir / "data" / "program_graph.json"
    if not pg.exists():
        pg = run_dir / "program_graph.json"
    figures = run_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    n = 0
    if pg.exists():
        out = figures / "program_graph.png"
        if render_program_graph_png(pg, out):
            logger.info("Wrote %s", out)
            n += 1

    dot = find_graph_dot(run_dir)
    if dot is not None:
        dot_out = figures / "program_graph_graphviz.png"
        if render_graphviz_dot_to_png(dot, dot_out):
            logger.info("Wrote %s", dot_out)
            n += 1

    mmd = render_all_mermaid_in_run(run_dir, figures)
    n += len(mmd)
    for p in mmd:
        logger.info("Wrote %s", p)
    if n == 0:
        logger.warning("No figures produced under %s", run_dir)
    return n


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: render every Mermaid file under one or more run dirs into PNGs."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(description="Render PNG figures for COGANT output run directories.")
    p.add_argument("path", type=Path, help="Output root, suite folder, or single run directory")
    args = p.parse_args(argv)
    path: Path = args.path.resolve()
    if not path.exists():
        logger.error("Path not found: %s", path)
        return 1

    runs = _discover_run_dirs(path)
    if not runs:
        logger.error("No run with program_graph.json under %s", path)
        return 1

    total = sum(_process_run_dir(r) for r in runs)
    logger.info("Done. Total PNGs written: %s (runs=%s)", total, len(runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
