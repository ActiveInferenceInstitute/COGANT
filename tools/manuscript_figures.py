"""Prepare rendered COGANT figures for the manuscript output tree.

The inner COGANT package writes real run artifacts under ``cogant/output``.
The template renderer expects manuscript-local assets under ``output/figures``
next to ``output/manuscript``. This module exposes the figure-copying CLI and
public registry; rendering and artifact inspection live in ``figures/``.
"""

from __future__ import annotations

import argparse

from figures.copier import copy_manuscript_figures
from manuscript_figure_registry import MANUSCRIPT_FIGURES, ManuscriptFigure

__all__ = [
    "MANUSCRIPT_FIGURES",
    "ManuscriptFigure",
    "copy_manuscript_figures",
]

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy curated COGANT output figures into output/figures/."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any registered figure source is missing.",
    )
    args = parser.parse_args(argv)
    manifest = copy_manuscript_figures(strict=args.strict)
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
