#!/usr/bin/env python3
"""Audit backticked ``cogant.*`` module/attribute references in the manuscript.

Motivation
----------
The number-, citation-, and cross-reference audits do not check that a dotted
Python name cited in prose still resolves. A real RedTeam finding: the
manuscript cited ``cogant.viz.png_export`` (coverage table + figure-provenance
table) after that module was deleted, and no gate caught it — a reader following
the reference lands on a module that no longer exists.

This tool closes that gap. It scans Markdown under ``manuscript/`` for backticked
dotted names rooted at ``cogant`` (e.g. ``cogant.viz.png``,
``cogant.schemas.semantic.MappingKind``) and verifies each resolves to a live
module, package, or module attribute in the installed ``cogant`` package.

Resolution strategy (no manuscript-specific allowlist):

1. ``importlib.util.find_spec(name)`` — if the full dotted name is an importable
   module or package, it is valid.
2. Otherwise treat the name as ``module.attr[.attr…]``: find the longest dotted
   prefix that is an importable module, import it, and walk the remaining
   components with ``getattr``. All must resolve.
3. If neither path resolves, the reference is reported as STALE with the first
   component that failed.

Names that are obviously prose rather than code (single segment ``cogant``, or a
dotted name whose leaf looks like a sentence word) are handled conservatively:
only names with at least one ``.`` are checked, and resolution failure is only
reported when *no* prefix resolves or an attribute is genuinely absent.

Exit codes
----------
* ``0`` — every checked reference resolves (warnings allowed).
* ``1`` — at least one stale reference, or (``--strict``) an import error.

Usage::

    uv run python tools/audit_manuscript_module_refs.py
    uv run python tools/audit_manuscript_module_refs.py --manuscript-dir manuscript/
    uv run python tools/audit_manuscript_module_refs.py --strict

Path layout is anchored on ``__file__`` at the COGANT project root (or
``projects/cogant/`` when vendored into the parent template). The inner package
``py/`` is added to ``sys.path`` so ``import cogant`` resolves from a source
checkout without an editable install.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import inspect
import re
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TOOLS_DIR.parent

# Helper docs whose snippets are tutorial prose, not body claims (mirror crossref audit).
_SKIP_NAMES = frozenset({"AGENTS.md", "README.md", "SYNTAX.md"})

# Backticked dotted name rooted at ``cogant`` with at least one dot, e.g.
# `cogant.viz.png` or `cogant.schemas.semantic.MappingKind`. A trailing ``()`` or
# ``(args)`` is stripped; surrounding backticks are required so prose like
# "the cogant. prefix" is not matched.
_REF_RE = re.compile(r"`(cogant(?:\.[A-Za-z_][A-Za-z0-9_]*)+)(?:\([^`]*\))?`")

# A dotted name whose leaf is one of these is a FILE reference (e.g.
# ``cogant.yaml`` is the config file ``cogant/cogant.yaml``), not a module path.
_FILE_LEAF_EXTS = frozenset(
    {
        "yaml", "yml", "json", "jsonl", "toml", "md", "txt", "lock", "cfg",
        "ini", "sh", "png", "pdf", "csv", "svg", "html", "rs", "lock",
    }
)


def _source_defines(text: str, attr: str) -> bool:
    """True if ``text`` (a class or module source) defines ``attr`` as a
    function, class, module-level/instance assignment, or dataclass-style
    annotation. Catches instance attributes (``self.x = ...``) and dataclass
    fields (``x: int``) that are invisible to class-level ``getattr``.
    """
    patterns = (
        rf"^\s*def\s+{re.escape(attr)}\b",
        rf"^\s*class\s+{re.escape(attr)}\b",
        rf"^\s*{re.escape(attr)}\s*[:=]",  # annotation or module/class-level assign
        rf"\bself\.{re.escape(attr)}\s*[:=]",  # instance attribute assignment
    )
    return any(re.search(p, text, re.MULTILINE) for p in patterns)


def _fs_resolve(name: str) -> tuple[bool, str] | None:
    """Filesystem fallback for dotted names that map to project-level ``.py``
    scripts not importable under the ``cogant`` package namespace (e.g.
    ``cogant.evaluation.figures.generate_figures.figure_graph_sizes`` →
    ``cogant/evaluation/figures/generate_figures.py``). Returns a verdict, or
    ``None`` if no backing file is found (caller continues with other strategies).
    """
    parts = name.split(".")
    for cut in range(len(parts), 1, -1):
        rel = Path(*parts[:cut])
        for candidate in (
            _REPO_ROOT / rel.with_suffix(".py"),
            _REPO_ROOT / rel / "__init__.py",
        ):
            if not candidate.exists():
                continue
            trailing = parts[cut:]
            if not trailing:
                return True, f"file {candidate.relative_to(_REPO_ROOT)}"
            text = candidate.read_text(encoding="utf-8", errors="replace")
            if _source_defines(text, trailing[0]):
                return True, f"symbol in {candidate.relative_to(_REPO_ROOT)}"
            return False, f"{candidate.relative_to(_REPO_ROOT)} has no '{trailing[0]}'"
    return None


def _candidate_package_root() -> Path:
    """Return the ``py/`` directory that contains the importable ``cogant`` pkg."""
    py_dir = _REPO_ROOT / "cogant" / "py"
    if (py_dir / "cogant" / "__init__.py").exists():
        return py_dir
    # When run from inside the package root (cogant/), ``py/`` is a sibling.
    alt = _REPO_ROOT / "py"
    if (alt / "cogant" / "__init__.py").exists():
        return alt
    return py_dir


def _module_exists(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def resolve_reference(name: str) -> tuple[bool, str]:
    """Return ``(ok, detail)`` for a dotted ``cogant.*`` reference.

    ``ok`` is True when the name resolves to a module, package, module
    attribute, instance/dataclass attribute, or a project-level ``.py`` symbol.
    ``detail`` explains a failure (or echoes how it resolved).
    """
    # 1. A fully-importable module/package is authoritative (e.g. cogant.viz.png).
    if _module_exists(name):
        return True, "module"

    # 2. File references (``cogant.yaml`` → cogant/cogant.yaml) are not modules.
    leaf = name.split(".")[-1]
    if leaf.lower() in _FILE_LEAF_EXTS:
        matches = list(_REPO_ROOT.rglob(name))
        return (bool(matches), "config/file" if matches else f"no file named '{name}'")

    # 3. Longest importable module prefix, then walk the rest. A failed getattr
    # falls back to a SOURCE check (instance attrs / dataclass fields are
    # invisible to class-level getattr but are still valid references).
    parts = name.split(".")
    module_failure: tuple[bool, str] | None = None
    for cut in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:cut])
        if not _module_exists(module_name):
            continue
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - import side effects
            module_failure = (False, f"import of '{module_name}' failed: {exc!r}")
            break
        obj = module
        parent_desc = module_name
        resolved = True
        for attr in parts[cut:]:
            if hasattr(obj, attr):
                obj = getattr(obj, attr)
                parent_desc = f"{parent_desc}.{attr}"
                continue
            try:
                src = inspect.getsource(
                    obj if (inspect.isclass(obj) or inspect.ismodule(obj)) else type(obj)
                )
            except (OSError, TypeError):
                src = ""
            if src and _source_defines(src, attr):
                return True, f"source-defined attribute '{attr}' on '{parent_desc}'"
            module_failure = (False, f"'{parent_desc}' has no attribute '{attr}'")
            resolved = False
            break
        if resolved:
            return True, f"attribute on '{module_name}'"
        # The longest importable prefix is authoritative for the module path;
        # stop probing shorter prefixes and fall through to the filesystem.
        break

    # 4. Not resolvable under the package namespace — try project-level files
    # (e.g. cogant.evaluation.figures.* live in cogant/evaluation/, not py/cogant/).
    fs = _fs_resolve(name)
    if fs is not None and fs[0]:
        return fs
    if module_failure is not None:
        return module_failure
    if fs is not None:
        return fs
    return False, f"no importable module prefix for '{name}'"


def iter_manuscript_files(manuscript_dir: Path):
    for path in sorted(manuscript_dir.glob("*.md")):
        if path.name in _SKIP_NAMES:
            continue
        yield path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manuscript-dir",
        type=Path,
        default=_REPO_ROOT / "manuscript",
        help="Directory of manuscript Markdown fragments (default: manuscript/).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on import errors in addition to stale references.",
    )
    args = parser.parse_args(argv)

    pkg_root = _candidate_package_root()
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))

    manuscript_dir: Path = args.manuscript_dir
    if not manuscript_dir.is_dir():
        print(f"module-ref audit: manuscript dir not found: {manuscript_dir}", file=sys.stderr)
        return 1

    stale: list[tuple[str, int, str, str]] = []
    import_errors: list[tuple[str, int, str, str]] = []
    checked = 0
    distinct: set[str] = set()

    for path in iter_manuscript_files(manuscript_dir):
        rel = path.relative_to(_REPO_ROOT) if path.is_relative_to(_REPO_ROOT) else path
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in _REF_RE.finditer(line):
                name = match.group(1)
                checked += 1
                distinct.add(name)
                ok, detail = resolve_reference(name)
                if ok:
                    continue
                if detail.startswith("import of"):
                    import_errors.append((str(rel), lineno, name, detail))
                else:
                    stale.append((str(rel), lineno, name, detail))

    print(
        f"module-ref audit: {checked} reference(s) ({len(distinct)} distinct) scanned in "
        f"{manuscript_dir.name}/; {len(stale)} stale, {len(import_errors)} import error(s)"
    )

    if stale:
        print("\nStale references (module/attribute does not exist):")
        for rel, lineno, name, detail in stale:
            print(f"  {rel}:{lineno}: `{name}` — {detail}")

    if import_errors:
        print("\nImport errors (could not verify):")
        for rel, lineno, name, detail in import_errors:
            print(f"  {rel}:{lineno}: `{name}` — {detail}")

    if stale:
        return 1
    if import_errors and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
