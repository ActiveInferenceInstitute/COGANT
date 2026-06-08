"""Tiny CLI fixture for COGANT graph and role extraction."""

from __future__ import annotations

import argparse
from pathlib import Path


class LineCounterState:
    """State holder that makes this fixture role-bearing."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def get_path(self) -> Path:
        return self.path

    def read_count(self) -> int:
        return count_lines(self.path)


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
    state = LineCounterState(args.path)
    total = state.read_count()
    if total < args.minimum:
        return 2
    print(total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
