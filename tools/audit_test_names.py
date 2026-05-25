#!/usr/bin/env python3
"""Audit active tests and examples for functional, durable names.

This guard catches generated-era campaign labels that make tests hard to
navigate later, such as ``wave20`` filenames, ``coverage_boost`` batches, and
``*_cov.py`` suffixes. It intentionally scans active tests and orchestrated
examples, not archival R&D logs.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_ROOTS = (
    ROOT / "cogant" / "tests",
    ROOT / "cogant" / "examples" / "thin_orchestrated",
)
TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yaml", ".yml"}
IGNORED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int | None
    pattern: str
    text: str

    def render(self) -> str:
        rel = self.path.relative_to(ROOT)
        location = f"{rel}:{self.line}" if self.line is not None else str(rel)
        return f"{location}: {self.pattern}: {self.text}"


FILENAME_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("campaign wave label in filename", re.compile(r"wave[-_ ]?\d+[a-z]*", re.IGNORECASE)),
    ("coverage_boost filename", re.compile(r"coverage[_-]?boost", re.IGNORECASE)),
    ("dated _wNN filename suffix", re.compile(r"_w\d+\b", re.IGNORECASE)),
    ("opaque _cov.py filename suffix", re.compile(r"_cov\.py$", re.IGNORECASE)),
    ("generic *_coverage.py filename", re.compile(r"_coverage\.py$", re.IGNORECASE)),
)

CONTENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("campaign wave label in active test/example text", re.compile(r"\bwave[-_ ]?\d+[a-z]*\b", re.IGNORECASE)),
    ("coverage boost campaign wording", re.compile(r"coverage[-_ ]boost", re.IGNORECASE)),
    ("dated week label", re.compile(r"\bweek\s+18\b", re.IGNORECASE)),
    ("mutation-killer campaign wording", re.compile(r"mutation[-_ ]killer", re.IGNORECASE)),
)


def iter_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if root.is_file():
            yield root
            continue
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if any(part in IGNORED_DIR_NAMES for part in path.parts):
                continue
            if path.is_file():
                yield path


def audit_filename(path: Path) -> list[Violation]:
    name = path.name
    violations: list[Violation] = []
    for label, pattern in FILENAME_PATTERNS:
        if pattern.search(name):
            violations.append(Violation(path=path, line=None, pattern=label, text=name))
    return violations


def audit_content(path: Path) -> list[Violation]:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    violations: list[Violation] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in CONTENT_PATTERNS:
            if pattern.search(line):
                violations.append(
                    Violation(
                        path=path,
                        line=line_number,
                        pattern=label,
                        text=line.strip(),
                    )
                )
    return violations


def audit(roots: Iterable[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in sorted(set(iter_files(roots))):
        violations.extend(audit_filename(path))
        violations.extend(audit_content(path))
    return violations


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional files or directories to scan. Defaults to active tests and thin examples.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    roots = tuple(path if path.is_absolute() else ROOT / path for path in args.paths)
    scan_roots = roots or DEFAULT_SCAN_ROOTS
    violations = audit(scan_roots)
    if violations:
        print("Found non-functional test/example naming labels:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation.render()}", file=sys.stderr)
        return 1
    scanned = ", ".join(str(path.relative_to(ROOT)) for path in scan_roots)
    print(f"OK: active test/example naming is functional ({scanned})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
