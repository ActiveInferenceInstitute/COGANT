#!/usr/bin/env python3
"""Audit pandoc-crossref-style identifiers across COGANT manuscript fragments.

Collects definitions ``{#sec:…}``, ``{#tbl:…}``, ``{#eq:…}``, ``{#fig:…}`` and
references ``@sec:…``, ``@tbl:…``, ``@eq:…``, ``@fig:…`` from Markdown files under
``manuscript/``. Reports duplicate definitions and references with no matching
definition.

Strict mode also scans manuscript source, injected Markdown, rendered HTML, and
the combined LaTeX file for unresolved cross-reference tokens, raw LaTeX
``\\ref`` usage, duplicate rendered captions, and hard-coded prose references
such as "Table 4" or "Appendix C".

Skips non-body helper files (``AGENTS.md``, ``README.md``, ``SYNTAX.md``) so
tutorial snippets do not pollute the source-body audit. ``supplementary.md`` is
included because manuscript discovery renders it when present.

Exit codes
----------
* ``0`` — no duplicate defs and no orphan references (warnings allowed).
* ``1`` — duplicate definitions or orphan references.

Usage::

    uv run python tools/audit_manuscript_crossrefs.py
    uv run python tools/audit_manuscript_crossrefs.py --manuscript-dir manuscript/
    uv run python tools/audit_manuscript_crossrefs.py --strict-rendered

Path layout is anchored on ``__file__`` at the COGANT project root (or
``projects/working/cogant/`` when linked into the parent template).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TOOLS_DIR.parent

# {#sec:id} or image/table attrs like {#fig:id width=95%}; allow hyphenated ids.
_DEF_RE = re.compile(r"\{#(sec|tbl|eq|fig):([A-Za-z0-9_-]+)(?:\s+[^}]*)?\}")
_REF_RE = re.compile(r"@(sec|tbl|eq|fig):([A-Za-z0-9_-]+)\b")

_SKIP_NAMES = frozenset({"AGENTS.md", "README.md", "SYNTAX.md"})

_RAW_LATEX_REF_RE = re.compile(r"\\(?:eq)?ref\{[^}]+\}|(?:Equation|Eq\.)\s+\\ref\{[^}]+\}")
_RAW_RENDERED_REF_RE = re.compile(r"@(sec|tbl|eq|fig):[A-Za-z0-9_-]+\b")
_DUP_RENDERED_CAPTION_RE = re.compile(
    r"\b(Table|Figure)\s+\d+[A-Za-z]?(?:\.\d+)?\s*:\s*\1\s+\d+[A-Za-z]?(?:\.\d+)?\b",
    re.IGNORECASE,
)
_HARDCODED_REF_RE = re.compile(
    r"\b("
    r"Table\s+\d+[A-Za-z]?(?:\.\d+)?(?:\s*[–-]\s*\d+[A-Za-z]?(?:\.\d+)?)?|"
    r"Figure\s+\d+[A-Za-z]?(?:\.\d+)?(?:\s*[–-]\s*\d+[A-Za-z]?(?:\.\d+)?)?|"
    r"Section\s+\d+[A-Za-z]?(?:\.\d+)?(?:\s*[–-]\s*\d+[A-Za-z]?(?:\.\d+)?)?|"
    r"Appendix\s+[A-Z](?:\.\d+)?(?:\s*[–-]\s*[A-Z](?:\.\d+)?)?|"
    r"Definition\s+\d+(?:\.\d+)?|"
    r"Theorem\s+\d+(?:\.\d+)?|"
    r"Algorithm\s+\d+(?:\.\d+)?|"
    r"Proposition\s+[A-Z]\.\d+"
    r")\b"
)
_RAW_FRAGMENT_RE = re.compile(r"\b0[1-9]_[0-9]{2}\b|\bS0[1-9]_[A-Za-z0-9_-]+\b")

_SOURCE_SCAN_EXTS = {".md"}
_RENDERED_SCAN_EXTS = {".html", ".tex"}


def _iter_manuscript_md(manuscript_dir: Path) -> list[Path]:
    paths = sorted(manuscript_dir.glob("*.md"))
    return [p for p in paths if p.name not in _SKIP_NAMES]


def _strip_fenced_code_lines(text: str) -> list[tuple[int, str]]:
    """Return non-fenced Markdown lines as ``(line_number, line)`` pairs."""

    out: list[tuple[int, str]] = []
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append((lineno, line))
    return out


def _is_allowed_heading_reference(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return False
    return bool(
        re.match(
            r"^#+\s+(Appendix\s+[A-Z]|Algorithm:|Definition:|Theorem:|Proposition:)\b",
            stripped,
        )
    )


def _finding(path: Path, lineno: int | None, message: str) -> str:
    location = str(path.relative_to(_REPO_ROOT) if path.is_relative_to(_REPO_ROOT) else path)
    if lineno is not None:
        location = f"{location}:{lineno}"
    return f"{location}: {message}"


def _scan_source_reference_hygiene(files: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for lineno, line in _strip_fenced_code_lines(text):
            if _is_allowed_heading_reference(line):
                continue
            if _RAW_LATEX_REF_RE.search(line):
                findings.append(_finding(path, lineno, "raw LaTeX reference; use @eq:/@sec:/@tbl:/@fig:"))
            match = _HARDCODED_REF_RE.search(line)
            if match:
                findings.append(
                    _finding(path, lineno, f"hard-coded prose reference `{match.group(0)}`; use pandoc-crossref")
                )
            match = _RAW_FRAGMENT_RE.search(line)
            if match and "{" not in line:
                findings.append(
                    _finding(
                        path,
                        lineno,
                        f"raw fragment filename reference `{match.group(0)}`; use a section cross-reference",
                    )
                )
    return findings


def _scan_rendered_reference_hygiene(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        scans = [
            (_RAW_RENDERED_REF_RE, "unresolved raw pandoc-crossref token"),
            (_DUP_RENDERED_CAPTION_RE, "duplicate rendered caption number"),
        ]
        if path.suffix.lower() != ".tex":
            scans.append((_RAW_LATEX_REF_RE, "raw LaTeX reference in rendered artifact"))
        for regex, message in scans:
            for match in regex.finditer(text):
                lineno = text.count("\n", 0, match.start()) + 1
                excerpt = match.group(0).replace("\n", " ")[:120]
                findings.append(_finding(path, lineno, f"{message}: `{excerpt}`"))
    return findings


def _rendered_paths(root: Path) -> list[Path]:
    return [
        root / "output" / "web" / "index.html",
        root / "output" / "pdf" / "_combined_manuscript.tex",
    ]


def audit(manuscript_dir: Path, *, strict_rendered: bool = False) -> int:
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

    source_hygiene = _scan_source_reference_hygiene(files)
    if source_hygiene:
        rc = 1
        print("### Source reference hygiene findings\n")
        for item in source_hygiene:
            print(f"- {item}")
        print()

    if strict_rendered:
        injected_dir = _REPO_ROOT / "output" / "manuscript"
        injected_files = _iter_manuscript_md(injected_dir) if injected_dir.is_dir() else []
        injected_hygiene = _scan_source_reference_hygiene(injected_files)
        rendered_hygiene = _scan_rendered_reference_hygiene(_rendered_paths(_REPO_ROOT))
        if injected_hygiene:
            rc = 1
            print("### Injected manuscript reference hygiene findings\n")
            for item in injected_hygiene:
                print(f"- {item}")
            print()
        if rendered_hygiene:
            rc = 1
            print("### Rendered reference hygiene findings\n")
            for item in rendered_hygiene:
                print(f"- {item}")
            print()

    if rc == 0:
        total_defs = sum(len(ids) for ids in defs_by_kind.values())
        total_refs = sum(len(ps) for k in refs_by_kind.values() for ps in k.values())
        rendered_note = " rendered artifacts scanned;" if strict_rendered else ""
        print(
            f"OK: {len(files)} source files scanned;{rendered_note} "
            f"{total_defs} ids defined; {total_refs} references."
        )

    return rc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manuscript-dir",
        type=Path,
        default=_REPO_ROOT / "manuscript",
        help="Directory containing manuscript *.md fragments",
    )
    parser.add_argument(
        "--strict-rendered",
        action="store_true",
        help="Also scan injected Markdown, combined HTML, and combined LaTeX for unresolved or duplicated references.",
    )
    args = parser.parse_args()
    manuscript_dir = args.manuscript_dir.resolve()
    if not manuscript_dir.is_dir():
        print(f"Not a directory: {manuscript_dir}", file=sys.stderr)
        sys.exit(1)
    sys.exit(audit(manuscript_dir, strict_rendered=args.strict_rendered))


if __name__ == "__main__":
    main()
