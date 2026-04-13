"""Verify relative markdown links from ``manuscript/*.md``.

Walks every ``manuscript/**/*.md`` file next to this package root, extracts
inline markdown link targets, and checks that each relative path resolves
inside the git work tree. Links beginning with ``../../../`` are skipped:
they target the parent template checkout that sits outside this
(sub-)repository when COGANT is a standalone git root.

Invocation is directory-independent — all paths are anchored on
``__file__``. Run from anywhere::

    uv run python cogant/docs/verify_manuscript_links.py
    cd cogant && uv run python docs/verify_manuscript_links.py

Exit codes
----------
* ``0`` — all checked links resolved (summary printed to stdout).
* ``1`` — at least one broken or escaping link was reported, or the
          ``manuscript/`` directory was missing.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_DOCS_DIR = Path(__file__).resolve().parent
# Package root: parent of ``docs/`` (``py/``, ``tests/``, …).
_PKG_ROOT = _DOCS_DIR.parent
# Staging root: parent of package root (contains ``manuscript/`` next to ``cogant/``).
_STAGING_ROOT = _PKG_ROOT.parent
_MANUSCRIPT_DIR = _STAGING_ROOT / "manuscript"


def _git_root(start: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()).resolve()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return _STAGING_ROOT.resolve()


_REPO_ROOT = _git_root(_STAGING_ROOT)

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _split_target(raw: str) -> tuple[str, str]:
    """Return (path_part, fragment) for a markdown link target."""
    if "#" in raw:
        path_part, frag = raw.split("#", 1)
        return path_part, frag
    return raw, ""


def verify_manuscript() -> list[str]:
    """Return human-readable errors for broken relative links in ``manuscript/``.

    Populates the module-level counters :data:`_LAST_FILES_SCANNED`,
    :data:`_LAST_LINKS_CHECKED`, and :data:`_LAST_LINKS_SKIPPED` so
    :func:`main` can emit a summary line in both success and failure.
    """
    global _LAST_FILES_SCANNED, _LAST_LINKS_CHECKED, _LAST_LINKS_SKIPPED
    _LAST_FILES_SCANNED = 0
    _LAST_LINKS_CHECKED = 0
    _LAST_LINKS_SKIPPED = 0
    errors: list[str] = []
    if not _MANUSCRIPT_DIR.is_dir():
        return [
            f"Manuscript directory not found: {_MANUSCRIPT_DIR} "
            "(expected next to the package root)."
        ]
    for md_path in sorted(_MANUSCRIPT_DIR.rglob("*.md")):
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
            if path_part.startswith("<") and path_part.endswith(">"):
                path_part = path_part[1:-1]
            # Links to the parent template checkout (infrastructure/, projects/) live outside
            # this repository when COGANT is a standalone git root — skip those targets.
            if path_part.startswith("../../../"):
                _LAST_LINKS_SKIPPED += 1
                continue
            _LAST_LINKS_CHECKED += 1
            resolved = (base / path_part).resolve()
            try:
                resolved.relative_to(_REPO_ROOT)
            except ValueError:
                errors.append(
                    f"{md_path.relative_to(_STAGING_ROOT)}: link escapes git root: {raw!r}"
                )
                continue
            if resolved.is_file():
                continue
            if resolved.is_dir():
                continue
            errors.append(
                f"{md_path.relative_to(_STAGING_ROOT)}: missing target {raw!r} "
                f"(resolved {resolved.relative_to(_REPO_ROOT)})"
            )
    return errors


# Summary counters populated by :func:`verify_manuscript` for :func:`main`.
_LAST_FILES_SCANNED: int = 0
_LAST_LINKS_CHECKED: int = 0
_LAST_LINKS_SKIPPED: int = 0


def main() -> int:
    errs = verify_manuscript()
    summary = (
        f"verify_manuscript_links: {_LAST_FILES_SCANNED} file(s) scanned, "
        f"{_LAST_LINKS_CHECKED} link(s) checked, {_LAST_LINKS_SKIPPED} skipped "
        f"(../../../...), {len(errs)} broken"
    )
    if errs:
        print("\n".join(errs))
        print("\n" + summary)
        return 1
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
