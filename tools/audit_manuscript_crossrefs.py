#!/usr/bin/env python3
"""Audit pandoc-crossref-style identifiers across COGANT manuscript fragments.

Collects definitions ``{#sec:…}``, ``{#tbl:…}``, ``{#eq:…}``, ``{#fig:…}`` and
references ``@sec:…``, ``@tbl:…``, ``@eq:…``, ``@fig:…`` from Markdown files under
``manuscript/``. Reports duplicate definitions and references with no matching
definition.

Skips non-body helper files (``AGENTS.md``, ``README.md``, ``SYNTAX.md``,
``supplementary.md``) so tutorial snippets do not pollute the audit.

Exit codes
----------
* ``0`` — no duplicate defs and no orphan references (warnings allowed).
* ``1`` — duplicate definitions or orphan references.

Usage::

    uv run python tools/audit_manuscript_crossrefs.py
    uv run python tools/audit_manuscript_crossrefs.py --manuscript-dir manuscript/

Path layout is anchored on ``__file__`` (staging root =
``projects_in_progress/cogant/``).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TOOLS_DIR.parent

# {#sec:id} — allow hyphenated ids used throughout COGANT stems.
_DEF_RE = re.compile(r"\{#(sec|tbl|eq|fig):([A-Za-z0-9_-]+)\}")
_REF_RE = re.compile(r"@(sec|tbl|eq|fig):([A-Za-z0-9_-]+)\b")

_SKIP_NAMES = frozenset(
    {"AGENTS.md", "README.md", "SYNTAX.md", "supplementary.md"}
)


def _iter_manuscript_md(manuscript_dir: Path) -> list[Path]:
    paths = sorted(manuscript_dir.glob("*.md"))
    return [p for p in paths if p.name not in _SKIP_NAMES]


def audit(manuscript_dir: Path) -> int:
    defs_by_kind: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    refs_by_kind: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))

    files = _iter_manuscript_md(manuscript_dir)
    if not files:
        print(f"No Markdown files found under {manuscript_dir}", file=sys.stderr)
        return 1

    for path in files:
        text = path.read_text(encoding="utf-8")
        for kind, rid in _DEF_RE.findall(text):
            defs_by_kind[kind][rid].append(path)
        for kind, rid in _REF_RE.findall(text):
            refs_by_kind[kind][rid].append(path)

    rc = 0
    print("## Manuscript cross-reference audit\n")

    for kind in sorted(set(defs_by_kind) | set(refs_by_kind)):
        dupes = {
            rid: paths for rid, paths in defs_by_kind[kind].items() if len(paths) > 1
        }
        if dupes:
            rc = 1
            print(f"### Duplicate `{{#{kind}:…}}` definitions\n")
            for rid in sorted(dupes):
                locs = ", ".join(p.name for p in dupes[rid])
                print(f"- `{kind}:{rid}` → {locs}")
            print()

    orphans: list[tuple[str, str, Path]] = []
    for kind in refs_by_kind:
        for rid, paths in refs_by_kind[kind].items():
            if rid not in defs_by_kind[kind]:
                for p in paths:
                    orphans.append((kind, rid, p))

    if orphans:
        rc = 1
        print("### Orphan references (no `{#kind:id}` definition found)\n")
        for kind, rid, path in sorted(orphans, key=lambda x: (x[2].name, x[0], x[1])):
            print(f"- `{path.name}` → `@{kind}:{rid}`")
        print()

    if rc == 0:
        kinds = sorted(set(defs_by_kind) | set(refs_by_kind))
        total_defs = sum(len(r) for k in defs_by_kind.values() for r in k)
        total_refs = sum(len(ps) for k in refs_by_kind.values() for ps in k.values())
        print(f"OK: {len(files)} files scanned; {total_defs} ids defined; {total_refs} references.")

    return rc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manuscript-dir",
        type=Path,
        default=_REPO_ROOT / "manuscript",
        help="Directory containing manuscript *.md fragments",
    )
    args = parser.parse_args()
    manuscript_dir = args.manuscript_dir.resolve()
    if not manuscript_dir.is_dir():
        print(f"Not a directory: {manuscript_dir}", file=sys.stderr)
        sys.exit(1)
    sys.exit(audit(manuscript_dir))


if __name__ == "__main__":
    main()
