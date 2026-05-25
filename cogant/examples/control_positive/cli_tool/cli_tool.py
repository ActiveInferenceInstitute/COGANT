"""Tiny CLI fixture for COGANT graph and role extraction."""

from __future__ import annotations

import argparse
from pathlib import Path


def count_lines(path: Path) -> int:
    """Count non-empty lines in a text file."""

    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="linecount")
    parser.add_argument("path", type=Path)
    parser.add_argument("--minimum", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    total = count_lines(args.path)
    if total < args.minimum:
        return 2
    print(total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
