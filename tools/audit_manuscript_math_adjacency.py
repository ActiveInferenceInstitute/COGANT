#!/usr/bin/env python3
"""Audit the COGANT manuscript for Pandoc inline-math adjacency leaks.

Pandoc does **not** treat a closing ``$`` that is immediately followed by a
digit as the end of an inline-math span. As a result a cell such as
``$-${{ABLATION_..._DELTA}}`` — intended as a typographic minus before an
injected count — renders the dollars *literally* (``$-$10``) in both the HTML
and PDF outputs once the variable resolves to a number. The other inline math
on the same line (``$0.65$``) renders fine because its closing ``$`` is not
digit-adjacent, which is exactly why the bug is easy to miss in review.

This audit resolves manuscript variables first (so a ``$...${{TOKEN}}`` that
expands to ``$...$10`` is caught), then tokenizes inline math span-by-span and
flags any span whose closing ``$`` is immediately followed by a digit. Use a
Unicode minus ``−`` (or a plain ``-``) instead of ``$-$`` before a number.

Exit codes
----------
* ``0`` — no digit-adjacent inline-math spans found.
* ``1`` — at least one leak found, or the manuscript could not be read.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
SKIP_NAMES = frozenset({"AGENTS.md", "README.md", "SYNTAX.md"})


def _strip_code(text: str) -> str:
    """Remove fenced and inline code, where ``$`` is literal, not math."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.S)
    # keep newlines so line numbers survive; blank out inline code spans only
    return re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), text)


def find_digit_adjacent_math(text: str) -> list[tuple[int, int, str]]:
    """Return (lineno, col, context) for inline-math spans whose closing ``$``
    is immediately followed by a digit (the Pandoc leak condition)."""
    violations: list[tuple[int, int, str]] = []
    for lineno, line in enumerate(_strip_code(text).splitlines(), start=1):
        n = len(line)
        i = 0
        while i < n:
            ch = line[i]
            if ch == "\\":
                i += 2
                continue
            if ch != "$":
                i += 1
                continue
            # display math `$$...$$` — skip the delimiter, not our concern
            if i + 1 < n and line[i + 1] == "$":
                i += 2
                continue
            # opening inline `$`: Pandoc requires the next char to be non-space
            if i + 1 >= n or line[i + 1].isspace():
                i += 1
                continue
            j = i + 1
            while j < n:
                if line[j] == "\\":
                    j += 2
                    continue
                if line[j] == "$" and not line[j - 1].isspace():
                    break
                j += 1
            if j >= n or line[j] != "$":
                break  # no closing `$` on this line
            after = line[j + 1] if j + 1 < n else ""
            if after.isdigit():
                ctx = line[max(0, i - 4) : min(n, j + 6)]
                violations.append((lineno, i + 1, ctx))
            i = j + 1
    return violations


def _resolve(text: str) -> str:
    """Best-effort manuscript-variable resolution so token-adjacent leaks
    (``$-${{COUNT}}`` -> ``$-$10``) are caught. Falls back to raw text if the
    injector or METRICS.yaml is unavailable."""
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import inject_manuscript_vars as inj  # type: ignore

        resolved, _ = inj.inject(text, inj.load_metrics(), dry_run=False)
        return resolved
    except Exception:
        return text


def audit(manuscript_dir: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(manuscript_dir.glob("*.md")):
        if path.name in SKIP_NAMES:
            continue
        text = _resolve(path.read_text(encoding="utf-8"))
        for lineno, col, ctx in find_digit_adjacent_math(text):
            rel = path.relative_to(ROOT)
            findings.append(f"{rel}:{lineno}:{col}: inline math closes before a digit -> '{ctx}'")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript-dir", type=Path, default=MANUSCRIPT_DIR)
    args = parser.parse_args(argv)

    try:
        findings = audit(args.manuscript_dir)
    except OSError as exc:
        print(f"math-adjacency audit failed: {exc}", file=sys.stderr)
        return 1

    for line in findings:
        print(line, file=sys.stderr)
    print(
        f"math-adjacency audit: {len(findings)} digit-adjacent inline-math span(s) "
        f"(use a Unicode minus − or plain '-' before numbers, not $-$)"
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
