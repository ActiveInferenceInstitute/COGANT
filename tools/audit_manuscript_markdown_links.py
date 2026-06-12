#!/usr/bin/env python3
"""Reject rendered-manuscript links to Markdown files.

The publication manuscript should use intra-manuscript cross-references
(``@sec:``, ``@fig:``, ``@tbl:``, ``@eq:``) instead of clickable links to
``.md`` source files. Contributor-oriented helper files such as ``README.md``,
``AGENTS.md``, and ``SYNTAX.md`` are excluded from this body-fragment audit.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_NAMES = frozenset({"AGENTS.md", "README.md", "SYNTAX.md"})
MARKDOWN_LINK_RE = re.compile(
    r"(?<!!)\[[^\]\n]+\]\(\s*<?"
    r"(?P<target>[^)>\s]+\.md(?:#[^)>\s]+)?)"
    r">?(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    """A Markdown-file link found in a renderable manuscript fragment."""

    path: Path
    line_no: int
    target: str
    line: str

    def format(self, root: Path = ROOT) -> str:
        try:
            rel = self.path.relative_to(root)
        except ValueError:
            rel = self.path
        return f"{rel}:{self.line_no}: markdown file link `{self.target}`"


def _strip_fenced_code_lines(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    in_fence = False
    fence_marker = ""
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue
        if not in_fence:
            out.append((line_no, line))
    return out


def iter_body_markdown(directory: Path) -> list[Path]:
    """Return renderable body Markdown fragments under ``directory``."""

    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("*.md") if path.name not in SKIP_NAMES)


def scan_file(path: Path) -> list[Finding]:
    """Return Markdown-file links in one body fragment, excluding fenced code."""

    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return findings
    for line_no, line in _strip_fenced_code_lines(text):
        for match in MARKDOWN_LINK_RE.finditer(line):
            findings.append(Finding(path, line_no, match.group("target"), line.strip()))
    return findings


def audit_directories(directories: list[Path]) -> list[Finding]:
    """Scan each supplied manuscript directory for body Markdown-file links."""

    findings: list[Finding] = []
    for directory in directories:
        for path in iter_body_markdown(directory):
            findings.extend(scan_file(path))
    return findings


def audit(root: Path = ROOT, *, include_generated: bool = True) -> list[Finding]:
    """Scan source manuscript and, optionally, generated manuscript output."""

    directories = [root / "manuscript"]
    if include_generated:
        directories.append(root / "output" / "manuscript")
    return audit_directories(directories)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manuscript-dir",
        type=Path,
        default=ROOT / "manuscript",
        help="Source manuscript directory to scan.",
    )
    parser.add_argument(
        "--generated-dir",
        type=Path,
        default=ROOT / "output" / "manuscript",
        help="Generated manuscript directory to scan when it exists.",
    )
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="Scan only --manuscript-dir.",
    )
    args = parser.parse_args(argv)

    directories = [args.manuscript_dir]
    if not args.source_only:
        directories.append(args.generated_dir)
    findings = audit_directories(directories)
    if findings:
        print("Markdown-file links are not allowed in manuscript body fragments:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding.format(ROOT)}", file=sys.stderr)
        print(
            "Use @sec:/@fig:/@tbl:/@eq: cross-references, plain artifact names, or citations.",
            file=sys.stderr,
        )
        return 1
    scanned = sum(len(iter_body_markdown(directory)) for directory in directories)
    print(f"manuscript markdown-link audit: {scanned} body file(s), 0 markdown-file links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
