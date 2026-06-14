#!/usr/bin/env python3
"""Audit COGANT-owned folder README/AGENTS coverage and link hygiene."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_DOC_NAMES = {"README.md", "AGENTS.md"}

HARD_EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "htmlcov",
    "node_modules",
    "site",
    "target",
}
EXCLUDED_PREFIXES = {
    "cogant/evaluation/eval_repos",
    "cogant/out",
    "cogant/output",
    "output",
}
README_EXCEPTIONS = {
    "cogant/docs": "MkDocs uses docs/index.md as the site root; docs/README.md is intentionally absent.",
}
DOCUMENTABLE_SUFFIXES = {
    ".bib",
    ".html",
    ".ipynb",
    ".json",
    ".md",
    ".mmd",
    ".py",
    ".rs",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
DOCUMENTABLE_FILENAMES = {
    "Dockerfile",
    "Makefile",
}
PLACEHOLDER_PATTERNS = (
    "Describe what belongs",
    "This directory is part of the COGANT codebase-to-GNN translation engine",
    "Machine-oriented index for automation and editors",
    "Run `uv run pytest tests/` from the repository root",
)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


@dataclass(frozen=True)
class Finding:
    path: Path
    message: str
    line: int | None = None

    def render(self) -> str:
        rel = self.path.relative_to(ROOT) if self.path.is_relative_to(ROOT) else self.path
        if self.line is None:
            return f"{rel}: {self.message}"
        return f"{rel}:{self.line}: {self.message}"


def is_excluded(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    if any(part in HARD_EXCLUDED_PARTS for part in path.relative_to(ROOT).parts):
        return True
    return any(rel == prefix or rel.startswith(f"{prefix}/") for prefix in EXCLUDED_PREFIXES)


def tracked_and_untracked_files() -> set[Path]:
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True
    ).splitlines()
    files: set[Path] = set()
    for raw in [*tracked, *untracked]:
        path = ROOT / raw
        if path.is_file() and not is_excluded(path):
            files.add(path)
    return files


def files_under(paths: Iterable[Path]) -> set[Path]:
    files: set[Path] = set()
    for raw_path in paths:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        if not path.exists() or is_excluded(path):
            continue
        if path.is_file():
            files.add(path)
            continue
        for child in path.rglob("*"):
            if child.is_file() and not is_excluded(child):
                files.add(child)
    return files


def is_documentable_file(path: Path) -> bool:
    if path.name in DOCUMENTABLE_FILENAMES:
        return True
    return path.suffix.lower() in DOCUMENTABLE_SUFFIXES


def documentable_dirs(files: set[Path]) -> set[Path]:
    dirs: set[Path] = set()
    for path in files:
        if not is_documentable_file(path):
            continue
        parent = path.parent
        while parent != ROOT.parent and parent != parent.parent:
            if parent == ROOT or is_excluded(parent):
                break
            dirs.add(parent)
            parent = parent.parent
    return dirs


def audit_coverage(files: set[Path]) -> list[Finding]:
    findings: list[Finding] = []
    file_set = {path.relative_to(ROOT) for path in files if path.is_relative_to(ROOT)}
    for folder in sorted(documentable_dirs(files), key=lambda p: p.relative_to(ROOT).as_posix()):
        rel = folder.relative_to(ROOT).as_posix()
        readme = Path(rel) / "README.md"
        agents = Path(rel) / "AGENTS.md"
        if readme not in file_set and rel not in README_EXCEPTIONS:
            findings.append(Finding(folder, "missing README.md"))
        if agents not in file_set:
            findings.append(Finding(folder, "missing AGENTS.md"))
    return findings


def iter_doc_files(files: set[Path]) -> Iterable[Path]:
    for path in sorted(files):
        if path.name in TEXT_DOC_NAMES and not is_excluded(path):
            yield path


def audit_placeholders(files: set[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_doc_files(files):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in PLACEHOLDER_PATTERNS:
                if pattern in line:
                    findings.append(Finding(path, f"placeholder boilerplate: {pattern!r}", line_number))
    return findings


def is_external_link(target: str) -> bool:
    lowered = target.lower()
    return (
        target.startswith("#")
        or lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("mailto:")
    )


def audit_links(files: set[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_doc_files(files):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK_RE.finditer(line):
                target = match.group(1).strip()
                if is_external_link(target):
                    continue
                target = target.split("#", 1)[0]
                if not target:
                    continue
                resolved = (path.parent / target).resolve()
                if not resolved.exists():
                    findings.append(Finding(path, f"broken relative link: {match.group(1)!r}", line_number))
    return findings


def audit_documented_exceptions(files: set[Path]) -> list[Finding]:
    findings: list[Finding] = []
    file_set = {path.relative_to(ROOT) for path in files if path.is_relative_to(ROOT)}
    for rel, reason in README_EXCEPTIONS.items():
        readme = Path(rel) / "README.md"
        if readme in file_set:
            findings.append(Finding(ROOT / readme, f"README.md should remain absent: {reason}"))
    return findings


def audit(files: set[Path]) -> list[Finding]:
    return [
        *audit_coverage(files),
        *audit_documented_exceptions(files),
        *audit_placeholders(files),
        *audit_links(files),
    ]



def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional files or directories to scan. Defaults to git-tracked and untracked COGANT-owned files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    files = files_under(args.paths) if args.paths else tracked_and_untracked_files()
    findings = audit(files)
    if findings:
        print("Folder documentation audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding.render()}", file=sys.stderr)
        return 1
    print("Folder documentation audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
