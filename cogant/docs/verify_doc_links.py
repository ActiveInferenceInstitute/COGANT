"""Verify relative markdown links under ``docs/`` resolve to existing paths.

Walks every ``docs/**/*.md`` file, extracts inline markdown link targets,
and checks that each relative path (after resolution from the containing
file's directory) lives inside the package root and points to an existing
file or directory. External links (``http``/``https``/``mailto``/``tel``),
pure fragments (``#foo``), and angle-bracket wrapped paths are handled.

Invocation is directory-independent — all paths are anchored on
``__file__``. Run from anywhere::

    uv run python cogant/docs/verify_doc_links.py
    cd cogant && uv run python docs/verify_doc_links.py

Exit codes
----------
* ``0`` — all links resolved.
* ``1`` — at least one broken or escaping link was reported.

The summary line ("N files scanned, M links checked, K broken") is
printed to stdout even on success so the tool is self-documenting
in CI logs.
"""

from __future__ import annotations

import re
from pathlib import Path

_DOCS_DIR = Path(__file__).resolve().parent
# Package root: parent of ``docs/`` (contains ``py/``, ``tests/``, etc.).
_REPO_ROOT = _DOCS_DIR.parent

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _split_target(raw: str) -> tuple[str, str]:
    """Return (path_part, fragment) for a markdown link target."""
    if "#" in raw:
        path_part, frag = raw.split("#", 1)
        return path_part, frag
    return raw, ""


def verify_docs() -> list[str]:
    """Return human-readable errors for any broken relative links in ``docs/``.

    Also populates the module-level counters :data:`_LAST_FILES_SCANNED` and
    :data:`_LAST_LINKS_CHECKED` so :func:`main` can print a summary.
    """
    global _LAST_FILES_SCANNED, _LAST_LINKS_CHECKED
    _LAST_FILES_SCANNED = 0
    _LAST_LINKS_CHECKED = 0
    errors: list[str] = []
    for md_path in sorted(_DOCS_DIR.rglob("*.md")):
        if "__pycache__" in md_path.parts:
            continue
        _LAST_FILES_SCANNED += 1
        text = md_path.read_text(encoding="utf-8")
        base = md_path.parent
        for match in _LINK_RE.finditer(text):
            raw = match.group(1).strip()
            if not raw or raw.startswith(("#", "mailto:", "tel:")):
                continue
            if raw.startswith(("http://", "https://")):
                continue
            path_part, _frag = _split_target(raw)
            if not path_part:
                continue
            # Angle-bracket wrapped paths: <path>
            if path_part.startswith("<") and path_part.endswith(">"):
                path_part = path_part[1:-1]
            _LAST_LINKS_CHECKED += 1
            resolved = (base / path_part).resolve()
            try:
                resolved.relative_to(_REPO_ROOT)
            except ValueError:
                errors.append(f"{md_path.relative_to(_REPO_ROOT)}: link escapes repo root: {raw!r}")
                continue
            if resolved.is_file():
                continue
            if resolved.is_dir():
                continue
            errors.append(
                f"{md_path.relative_to(_REPO_ROOT)}: missing target {raw!r} "
                f"(resolved {resolved.relative_to(_REPO_ROOT)})"
            )
    return errors


# Summary counters populated by :func:`verify_docs` for :func:`main` to print.
_LAST_FILES_SCANNED: int = 0
_LAST_LINKS_CHECKED: int = 0


def main() -> int:
    errs = verify_docs()
    if errs:
        print("\n".join(errs))
        print(
            f"\nverify_doc_links: {_LAST_FILES_SCANNED} file(s) scanned, "
            f"{_LAST_LINKS_CHECKED} link(s) checked, {len(errs)} broken"
        )
        return 1
    print(
        f"verify_doc_links: {_LAST_FILES_SCANNED} file(s) scanned, "
        f"{_LAST_LINKS_CHECKED} link(s) checked, 0 broken"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
