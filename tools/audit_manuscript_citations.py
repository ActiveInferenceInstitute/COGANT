#!/usr/bin/env python3
"""Audit Pandoc citation keys used by the COGANT manuscript.

The audit scans rendered-body Markdown fragments, strips fenced and inline code,
collects Pandoc citation keys, and verifies that every used key exists in
``manuscript/references.bib``. Cross-reference tokens such as ``@sec:...`` and
formalism tokens such as ``@def:...`` are handled by dedicated audits and ignored
here.

Exit codes
----------
* ``0`` — no missing or duplicate BibTeX keys (unused keys warn only).
* ``1`` — at least one used citation key is missing, a BibTeX key is duplicated,
          or ``--fail-on-unused`` found unused BibTeX entries.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
BIB_PATH = MANUSCRIPT_DIR / "references.bib"

SKIP_NAMES = frozenset({"AGENTS.md", "README.md", "SYNTAX.md"})
CITATION_RE = re.compile(r"(?<![\w])@([A-Za-z][A-Za-z0-9_:-]+)")
BIB_KEY_RE = re.compile(r"@\w+\{([^,\s]+)\s*,")
XREF_PREFIXES = (
    "sec:",
    "tbl:",
    "fig:",
    "eq:",
    "lst:",
    "def:",
    "prop:",
    "inv:",
    "conj:",
    "alg:",
    "thm:",
)


def _strip_markdown_code(text: str) -> str:
    """Remove fenced blocks and inline code before citation scanning."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.S)
    return re.sub(r"`[^`]*`", "", text)


def _iter_body_markdown(manuscript_dir: Path) -> list[Path]:
    return sorted(path for path in manuscript_dir.glob("*.md") if path.name not in SKIP_NAMES)


def _format_location(path: Path, lineno: int, manuscript_dir: Path) -> str:
    try:
        display = path.relative_to(ROOT)
    except ValueError:
        display = path.relative_to(manuscript_dir.parent)
    return f"{display}:{lineno}"


def collect_used_citations(manuscript_dir: Path) -> dict[str, list[str]]:
    """Return citation key -> manuscript locations where it appears."""
    locations: dict[str, list[str]] = {}
    for path in _iter_body_markdown(manuscript_dir):
        text = _strip_markdown_code(path.read_text(encoding="utf-8"))
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in CITATION_RE.finditer(line):
                key = match.group(1)
                if key.startswith(XREF_PREFIXES):
                    continue
                locations.setdefault(key, []).append(_format_location(path, lineno, manuscript_dir))
    return locations


def collect_bib_keys(bib_path: Path) -> tuple[set[str], list[str]]:
    """Return unique BibTeX keys and any duplicates."""
    if not bib_path.is_file():
        raise FileNotFoundError(f"BibTeX file not found: {bib_path}")
    keys: list[str] = []
    for line in bib_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("@comment"):
            continue
        match = BIB_KEY_RE.match(stripped)
        if match:
            keys.append(match.group(1))
    counts = Counter(keys)
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    return set(keys), duplicates


def audit(manuscript_dir: Path = MANUSCRIPT_DIR, bib_path: Path = BIB_PATH) -> tuple[list[str], list[str], list[str]]:
    used = collect_used_citations(manuscript_dir)
    bib_keys, duplicates = collect_bib_keys(bib_path)
    missing = sorted(key for key in used if key not in bib_keys)
    unused = sorted(bib_keys - set(used))
    return missing, duplicates, unused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript-dir", type=Path, default=MANUSCRIPT_DIR)
    parser.add_argument("--bib", type=Path, default=BIB_PATH)
    parser.add_argument("--fail-on-unused", action="store_true")
    args = parser.parse_args(argv)

    try:
        missing, duplicates, unused = audit(args.manuscript_dir, args.bib)
    except OSError as exc:
        print(f"citation audit failed: {exc}", file=sys.stderr)
        return 1

    if missing:
        print("Missing BibTeX keys:", file=sys.stderr)
        for key in missing:
            print(f"  {key}", file=sys.stderr)
    if duplicates:
        print("Duplicate BibTeX keys:", file=sys.stderr)
        for key in duplicates:
            print(f"  {key}", file=sys.stderr)
    if unused:
        print(f"Unused BibTeX keys: {len(unused)}", file=sys.stderr)
        if args.fail_on_unused:
            for key in unused:
                print(f"  {key}", file=sys.stderr)

    used_count = len(collect_used_citations(args.manuscript_dir))
    bib_count = len(collect_bib_keys(args.bib)[0])
    print(
        f"citation audit: {used_count} used key(s), {bib_count} BibTeX key(s), "
        f"{len(missing)} missing, {len(duplicates)} duplicate(s)"
    )

    if missing or duplicates or (args.fail_on_unused and unused):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
