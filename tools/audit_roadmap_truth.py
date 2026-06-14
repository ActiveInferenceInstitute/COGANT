#!/usr/bin/env python3
"""Audit roadmap docs for current-version and benchmark-truth claims."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROADMAP_DIR = REPO_ROOT / "cogant" / "docs" / "roadmap"
TODO_PATH = REPO_ROOT / "TODO.md"
TASKS_PATH = REPO_ROOT / "tasks.yaml"
REMOVED_BASELINE_RE = r"v" + r"0\.1\.0"
REMOVED_BASELINE_LABEL_RE = r"Version\s+0\.1\.0"


@dataclass(frozen=True)
class DriftPattern:
    path: Path
    pattern: re.Pattern[str]
    message: str


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _pattern_findings() -> list[str]:
    checks = (
        DriftPattern(
            ROADMAP_DIR / "version_010_current.md",
            re.compile(REMOVED_BASELINE_LABEL_RE + r"\s*\(current\)", re.IGNORECASE),
            "removed baseline label must not be described as the current version",
        ),
        DriftPattern(
            ROADMAP_DIR / "cogant_benchmarks.md",
            re.compile(r"\bnine pipeline stages\b", re.IGNORECASE),
            "benchmark docs must not use removed nine-stage pipeline wording",
        ),
        DriftPattern(
            ROADMAP_DIR / "cogant_benchmarks.md",
            re.compile(r"\bthree control-positive fixture repos\b", re.IGNORECASE),
            "benchmark docs must not imply the batch evidence surface is only three fixtures",
        ),
        DriftPattern(
            ROADMAP_DIR / "cogant_benchmarks.md",
            re.compile(r"All three achieve\s+\*\*100%\s+GNN validation score\*\*", re.IGNORECASE),
            "hard-coded perfect validation claims must come from metrics artifacts instead",
        ),
        DriftPattern(
            ROADMAP_DIR / "cogant_benchmarks.md",
            re.compile(r"emit\s+\*\*111 files\*\*", re.IGNORECASE),
            "hard-coded output artifact counts must come from generated manifests instead",
        ),
        DriftPattern(
            ROADMAP_DIR / "cogant_benchmarks.md",
            re.compile(r"Observed\s+\(" + REMOVED_BASELINE_RE + r"\)", re.IGNORECASE),
            "current benchmark tables must not publish removed observed values",
        ),
        DriftPattern(
            ROADMAP_DIR / "feature_backlog.md",
            re.compile(
                r"Roadmap docs still describe " + REMOVED_BASELINE_RE + r" as [\"']current[\"']",
                re.IGNORECASE,
            ),
            "feature backlog must not retain a resolved roadmap finding as open work",
        ),
    )
    findings: list[str] = []
    for check in checks:
        text = _read(check.path)
        if check.pattern.search(text):
            findings.append(f"{check.path.relative_to(REPO_ROOT)}: {check.message}")
    return findings


def _coordination_findings() -> list[str]:
    todo = _read(TODO_PATH)
    tasks = _read(TASKS_PATH)
    findings: list[str] = []
    required_todo = (
        "Refactor-first maintainability tranche",
        "roadmap truth audit",
        "tools/manuscript_figures.py",
        "viz/inspection_dashboard.py",
    )
    for marker in required_todo:
        if marker not in todo:
            findings.append(f"TODO.md: current sequence missing {marker!r}")
    required_tasks = (
        "Roadmap truth audit + current benchmark cleanup",
        "Refactor manuscript figure and inspection dashboard modules",
    )
    for marker in required_tasks:
        if marker not in tasks:
            findings.append(f"tasks.yaml: missing task {marker!r}")
    release_block = re.search(r"- id:\s*cog-m1\b(?P<body>[\s\S]*?)(?:\n- id:|\Z)", tasks)
    if release_block is None:
        findings.append("tasks.yaml: missing release milestone cog-m1")
        return findings
    release_text = release_block.group("body")
    release_blockers = ("cog-6", "cog-7", "cog-8", "cog-9")
    for blocker in release_blockers:
        if f"  - {blocker}" not in release_text:
            findings.append(f"tasks.yaml: release milestone dependency missing {blocker}")
    return findings


def audit() -> list[str]:
    """Return roadmap-truth findings; an empty list means the audit is clean."""

    return [*_pattern_findings(), *_coordination_findings()]


def main() -> int:
    findings = audit()
    print(f"audit_roadmap_truth: {len(findings)} finding(s)")
    for finding in findings:
        print(f"  FAIL {finding}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
