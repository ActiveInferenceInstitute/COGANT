#!/usr/bin/env python3
"""Fail when source text reintroduces removed GNN/API/version language."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {
    "",
    ".bib",
    ".cfg",
    ".css",
    ".html",
    ".ipynb",
    ".json",
    ".md",
    ".py",
    ".pyi",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "output",
}

EXCLUDED_RELATIVE = {
    Path("cogant/coverage.json"),
    Path("manuscript/references.bib"),
}


@dataclass(frozen=True)
class BannedPattern:
    name: str
    needle: str


def _p(*parts: str) -> str:
    return "".join(parts)


BANNED_PATTERNS = (
    BannedPattern("removed-generic-label", _p("leg", "acy")),
    BannedPattern("removed-generic-label", _p("depre", "cated")),
    BannedPattern("removed-generic-label", _p("depre", "cate")),
    BannedPattern("removed-generic-label", _p("arch", "ived")),
    BannedPattern("removed-generic-label", _p("hist", "orical")),
    BannedPattern("removed-generic-label", _p("obso", "lete")),
    BannedPattern("removed-generic-label", _p("st", "ale")),
    BannedPattern("removed-version", _p("v", "0.1.0")),
    BannedPattern("removed-version", _p("v", "0.2.0")),
    BannedPattern("removed-version", _p("v", "0.5")),
    BannedPattern("removed-gnn-version", _p("GNN v", "1")),
    BannedPattern("removed-gnn-version", _p("v", "1.1")),
    BannedPattern("removed-gnn-version", _p("v", "1.6")),
    BannedPattern("removed-gnn-version", _p("GNNVersion=1", ".0")),
    BannedPattern("removed-api", _p("ROLE_MATCH_", "THRESHOLD")),
    BannedPattern("removed-api", _p("role_match_", "score")),
    BannedPattern("removed-api", _p("is_", "isomorphic")),
    BannedPattern("removed-api", _p("roundtrip_", "invariants")),
    BannedPattern("removed-api", _p("mean_", "epsilon")),
    BannedPattern("removed-api", _p("epsilon_", "for")),
    BannedPattern("removed-api", _p("isomorphic_", "count")),
    BannedPattern("removed-schema-api", _p("Schema", "Version")),
    BannedPattern("removed-schema-api", _p("migrate_", "gnn")),
    BannedPattern("removed-renderer-failure", _p("No SVG", "->PNG")),
    BannedPattern("removed-renderer-failure", _p("SVG raster", "ization")),
    BannedPattern("removed-figure-caption", _p("first", " page")),
)


def _git_paths(args: list[str]) -> list[Path]:
    result = subprocess.run(
        ["git", *args, "-z"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return []
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def _candidate_paths(extra_paths: list[Path]) -> list[Path]:
    if extra_paths:
        raw = [path if path.is_absolute() else ROOT / path for path in extra_paths]
    else:
        raw = [
            *_git_paths(["ls-files"]),
            *_git_paths(["ls-files", "--others", "--exclude-standard"]),
        ]
    seen: set[Path] = set()
    paths: list[Path] = []
    for path in raw:
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            rel = path
        if rel in EXCLUDED_RELATIVE:
            continue
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        paths.append(path)
    return sorted(paths)


def audit(paths: list[Path] | None = None) -> list[str]:
    """Return current-only language findings."""

    findings: list[str] = []
    for path in _candidate_paths(paths or []):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lowered = text.lower()
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        for pattern in BANNED_PATTERNS:
            needle = pattern.needle
            offset = lowered.find(needle.lower())
            if offset < 0:
                continue
            line_no = text.count("\n", 0, offset) + 1
            findings.append(f"{rel}:{line_no}: {pattern.name}: {needle!r}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Optional files to scan")
    args = parser.parse_args()
    findings = audit(args.paths)
    print(f"audit_current_only_language: {len(findings)} finding(s)")
    for finding in findings:
        print(f"  FAIL {finding}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
