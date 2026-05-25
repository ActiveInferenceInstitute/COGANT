"""Verify relative markdown links from ``manuscript/*.md``.

Walks every ``manuscript/**/*.md`` file next to this package root, extracts
inline markdown link targets, and checks that each relative path resolves
inside the git work tree. Links beginning with ``../../../`` are checked when
they resolve inside the current checkout and skipped only when COGANT is being
validated as a standalone subrepository. Links beginning with ``../figures/``
are resolved against the generated ``output/figures`` directory and must have
matching figure sidecars.

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

import json
import subprocess
from pathlib import Path
import re
from urllib.parse import unquote

_DOCS_DIR = Path(__file__).resolve().parent
# Package root: parent of ``docs/`` (``py/``, ``tests/``, …).
_PKG_ROOT = _DOCS_DIR.parent
# Staging root: parent of package root (contains ``manuscript/`` next to ``cogant/``).
_STAGING_ROOT = _PKG_ROOT.parent
_MANUSCRIPT_DIR = _STAGING_ROOT / "manuscript"
_FIGURES_DIR = _STAGING_ROOT / "output" / "figures"
_FIGURE_MANIFEST = _FIGURES_DIR / "manifest.json"


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
_EXPLICIT_ID_RE = re.compile(r"\{#([A-Za-z0-9_.:-]+)\}")
_HTML_ID_RE = re.compile(r"\b(?:id|name)=['\"]([^'\"]+)['\"]")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*(?:\{#([A-Za-z0-9_.:-]+)\})?\s*$")
_INLINE_MARKUP_RE = re.compile(r"[`*_~\[\]()]")
_NON_SLUG_RE = re.compile(r"[^a-z0-9 _-]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _split_target(raw: str) -> tuple[str, str]:
    """Return (path_part, fragment) for a markdown link target."""
    if "#" in raw:
        path_part, frag = raw.split("#", 1)
        return path_part, unquote(frag)
    return raw, ""


def _slugify_heading(text: str) -> str:
    """Approximate the heading slug used by Markdown renderers."""
    text = _EXPLICIT_ID_RE.sub("", text)
    text = _INLINE_MARKUP_RE.sub("", text)
    text = _NON_SLUG_RE.sub("", text.lower())
    return _WHITESPACE_RE.sub("-", text.strip())


def _anchors_for(path: Path) -> set[str]:
    """Return explicit and heading-derived anchors from a Markdown file."""
    anchors: set[str] = set()
    if path.suffix.lower() != ".md" or not path.is_file():
        return anchors
    text = path.read_text(encoding="utf-8")
    anchors.update(_EXPLICIT_ID_RE.findall(text))
    anchors.update(_HTML_ID_RE.findall(text))
    for line in text.splitlines():
        match = _HEADING_RE.match(line.strip())
        if not match:
            continue
        explicit = match.group(3)
        if explicit:
            anchors.add(explicit)
        slug = _slugify_heading(match.group(2))
        if slug:
            anchors.add(slug)
    return anchors


def _check_fragment(errors: list[str], md_path: Path, raw: str, resolved: Path, fragment: str) -> None:
    """Append an error if ``fragment`` is absent from a resolved Markdown file."""
    if not fragment or resolved.suffix.lower() != ".md":
        return
    if fragment not in _anchors_for(resolved):
        errors.append(
            f"{md_path.relative_to(_STAGING_ROOT)}: missing anchor #{fragment!r} in {raw!r}"
        )


def _manifest_destinations() -> set[str]:
    if not _FIGURE_MANIFEST.is_file():
        return set()
    try:
        manifest = json.loads(_FIGURE_MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    figures = manifest.get("figures", [])
    if not isinstance(figures, list):
        return set()
    destinations: set[str] = set()
    for figure in figures:
        if isinstance(figure, dict) and isinstance(figure.get("destination"), str):
            destination = figure["destination"]
            destinations.add(destination)
            destinations.add(Path(destination).name)
            try:
                destinations.add(str(Path(destination).relative_to("output/figures")))
            except ValueError:
                pass
    return destinations


def _check_figure_link(errors: list[str], md_path: Path, raw: str, path_part: str) -> bool:
    """Validate generated manuscript figure targets and sidecars."""
    if not path_part.startswith("../figures/"):
        return False
    figure_name = path_part.removeprefix("../figures/")
    resolved = (_FIGURES_DIR / figure_name).resolve()
    if not resolved.is_file():
        errors.append(
            f"{md_path.relative_to(_STAGING_ROOT)}: missing generated figure {raw!r} "
            f"(resolved {resolved})"
        )
        return True
    sidecar = resolved.with_suffix(".figure.json")
    if not sidecar.is_file():
        errors.append(
            f"{md_path.relative_to(_STAGING_ROOT)}: missing figure sidecar for {raw!r} "
            f"(expected {sidecar})"
        )
    manifest_destinations = _manifest_destinations()
    if manifest_destinations and figure_name not in manifest_destinations:
        errors.append(
            f"{md_path.relative_to(_STAGING_ROOT)}: figure {raw!r} is absent from "
            f"{_FIGURE_MANIFEST.relative_to(_STAGING_ROOT)}"
        )
    return True


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
            path_part, frag = _split_target(raw)
            if not path_part:
                continue
            if path_part.startswith("<") and path_part.endswith(">"):
                path_part = path_part[1:-1]
            if _check_figure_link(errors, md_path, raw, path_part):
                _LAST_LINKS_CHECKED += 1
                continue
            _LAST_LINKS_CHECKED += 1
            resolved = (base / path_part).resolve()
            try:
                resolved.relative_to(_REPO_ROOT)
            except ValueError:
                if path_part.startswith("../../../"):
                    _LAST_LINKS_SKIPPED += 1
                    continue
                errors.append(
                    f"{md_path.relative_to(_STAGING_ROOT)}: link escapes git root: {raw!r}"
                )
                continue
            if resolved.is_file():
                _check_fragment(errors, md_path, raw, resolved, frag)
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
        f"(external template outside this checkout), {len(errs)} broken"
    )
    if errs:
        print("\n".join(errs))
        print("\n" + summary)
        return 1
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
