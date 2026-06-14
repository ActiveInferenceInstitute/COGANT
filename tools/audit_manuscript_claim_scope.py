#!/usr/bin/env python3
"""Fail on high-risk manuscript claim wording without local caveats."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOTS = (ROOT / "manuscript", ROOT / "output" / "manuscript")


@dataclass(frozen=True)
class ScopeRule:
    name: str
    pattern: re.Pattern[str]
    allowed_context: re.Pattern[str]


RULES = (
    ScopeRule(
        name="positive-guarantee",
        pattern=re.compile(r"\bguarantee(?:s|d)?\b", re.IGNORECASE),
        allowed_context=re.compile(
            r"\b(?:does not|do not|not|no|without|rather than)\b.{0,80}\bguarantee(?:s|d)?\b"
            r"|\bguarantee(?:s|d)?\b.{0,80}\b(?:not|future work|caveat)\b",
            re.IGNORECASE,
        ),
    ),
    ScopeRule(
        name="uncaveated-inferential-statistics",
        pattern=re.compile(
            r"\b(?:confidence interval|p-value|statistical significance|statistically meaningful)\b",
            re.IGNORECASE,
        ),
        allowed_context=re.compile(
            r"\b(?:no|not|without|does not|do not|future work|rather than)\b.{0,120}"
            r"\b(?:confidence interval|p-value|statistical significance|statistically meaningful)\b"
            r"|\b(?:confidence interval|p-value|statistical significance|statistically meaningful)\b"
            r".{0,120}\b(?:not|future work|caveat)\b",
            re.IGNORECASE,
        ),
    ),
    ScopeRule(
        name="semantic-totality-overclaim",
        pattern=re.compile(r"\bfully captures?\b", re.IGNORECASE),
        allowed_context=re.compile(
            r"\b(?:does not|do not|not|no|without)\b.{0,120}\bfully captures?\b",
            re.IGNORECASE,
        ),
    ),
)


def _candidate_files(paths: list[Path]) -> list[Path]:
    roots = [path if path.is_absolute() else ROOT / path for path in paths] if paths else list(DEFAULT_ROOTS)
    files: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        candidates = root.rglob("*.md") if root.is_dir() else [root]
        for path in candidates:
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            files.append(path)
    return sorted(files)


def _context(lines: list[str], index: int) -> str:
    start = max(0, index - 1)
    end = min(len(lines), index + 2)
    return " ".join(line.strip() for line in lines[start:end])


def audit(paths: list[Path] | None = None) -> list[str]:
    """Return claim-scope findings."""

    findings: list[str] = []
    for path in _candidate_files(paths or []):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        for idx, line in enumerate(lines):
            if not line.strip():
                continue
            window = _context(lines, idx)
            for rule in RULES:
                if not rule.pattern.search(line):
                    continue
                if rule.allowed_context.search(window):
                    continue
                findings.append(f"{rel}:{idx + 1}: {rule.name}: {line.strip()!r}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Optional manuscript files or dirs to scan")
    args = parser.parse_args()
    findings = audit(args.paths)
    print(f"audit_manuscript_claim_scope: {len(findings)} finding(s)")
    for finding in findings:
        print(f"  FAIL {finding}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
