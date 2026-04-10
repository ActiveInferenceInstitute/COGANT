"""Verify relative markdown links under ``docs/`` resolve to existing paths.

Run from the package root (directory containing ``docs/``):

    uv run python docs/verify_doc_links.py
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
    """Return human-readable errors for any broken relative links in ``docs/``."""
    errors: list[str] = []
    for md_path in sorted(_DOCS_DIR.rglob("*.md")):
        if "__pycache__" in md_path.parts:
            continue
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
            resolved = (base / path_part).resolve()
            try:
                resolved.relative_to(_REPO_ROOT)
            except ValueError:
                errors.append(
                    f"{md_path.relative_to(_REPO_ROOT)}: link escapes repo root: {raw!r}"
                )
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


def main() -> int:
    errs = verify_docs()
    if errs:
        print("\n".join(errs))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
