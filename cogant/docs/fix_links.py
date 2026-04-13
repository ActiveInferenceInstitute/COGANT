"""Rewrite links from old monolithic guide filenames to ``../<module>/README.md``.

This one-shot migration tool rewrites legacy ``SPEC.md``-style links that
survived the April-2026 modularisation refactor, pointing them at the new
``../<module>/README.md`` indexes. It also writes a *minimal-stub*
``AGENTS.md`` into any module folder that doesn't yet have one — stubs
should be replaced with a real module index the first time that directory
is edited.

Exit codes
----------
* ``0`` — default mode: finished successfully (files may have been
          rewritten). ``--check`` mode: no legacy links remained and no
          stub AGENTS.md files were needed.
* ``1`` — ``--check`` mode only: at least one legacy link or missing
          AGENTS.md was found; use the default mode to fix them.

Invocation is directory-independent — all paths are anchored on
``__file__``. Run from anywhere::

    uv run python cogant/docs/fix_links.py                # rewrite in place
    uv run python cogant/docs/fix_links.py --check        # CI gate, no writes
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent

FILE_TO_FOLDER = {
    "API_GUIDE.md": "api",
    "ARCHITECTURE.md": "architecture",
    "CLI_GUIDE.md": "cli",
    "GNN_EXPORT.md": "export",
    "PLUGIN_API.md": "plugins",
    "ROADMAP.md": "roadmap",
    "SECURITY.md": "security",
    "SPEC.md": "reference",
    "TRANSLATION_RULES.md": "rules",
    "VALIDATION.md": "validation",
}


def _stub_agents_body(folder: str) -> str:
    return (
        f"# AGENTS.md — {folder.title()} Module\n\n"
        f"This directory houses the deeply modularized documentation for the **{folder.title()}** "
        "aspects of the COGANT translation engine.\n\n"
        "## Maintenance Rules\n\n"
        "*   **Granularity**: Keep articles focused. Do not reintroduce monolithic, multi-context files.\n"
        "*   **Cross-Linking**: When referencing other modules, link to their respective "
        "`../module_name/README.md` indexes.\n"
    )


# Sentinel header the stub writer uses; :func:`is_stub_agents` looks for it.
_STUB_MARKER = "## Maintenance Rules\n\n*   **Granularity**"


def is_stub_agents(text: str) -> bool:
    """Return ``True`` if *text* matches the minimal-stub AGENTS.md template.

    Used by ``--check`` mode to flag module folders whose AGENTS.md has
    never been replaced with a real index.
    """
    return _STUB_MARKER in text and len(text.strip().splitlines()) <= 12


def update_links(filepath: Path, *, at_docs_root: bool, check_only: bool = False) -> bool:
    """Rewrite legacy links in *filepath*; return ``True`` if it changed.

    When ``check_only`` is set, no file is written — the return value simply
    indicates whether a rewrite *would* have occurred.
    """
    content = filepath.read_text(encoding="utf-8")
    original = content
    for old_file, new_folder in FILE_TO_FOLDER.items():
        pattern = r"\(\.?/?" + re.escape(old_file) + r"(#[^\)]*)?\)"
        repl = (
            f"({new_folder}/README.md)"
            if at_docs_root
            else f"(../{new_folder}/README.md)"
        )
        content = re.sub(pattern, repl, content)
    if content == original:
        return False
    if not check_only:
        filepath.write_text(content, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rewrite legacy monolith link targets to ../<module>/README.md "
            "and backfill missing AGENTS.md stubs. Use --check in CI to "
            "flag issues without modifying any files."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Do not modify any files. Exit 1 if legacy links or stub "
            "AGENTS.md files are found."
        ),
    )
    args = parser.parse_args(argv)
    check_only = args.check

    issues: list[str] = []
    rewrites: list[Path] = []

    for folder in FILE_TO_FOLDER.values():
        folder_path = DOCS_DIR / folder
        if not folder_path.is_dir():
            continue

        agents_path = folder_path / "AGENTS.md"
        if not agents_path.is_file():
            if check_only:
                issues.append(f"missing AGENTS.md: {agents_path.relative_to(DOCS_DIR)}")
            else:
                agents_path.write_text(_stub_agents_body(folder), encoding="utf-8")
                print(f"Wrote stub AGENTS.md in {agents_path}")
        else:
            if check_only and is_stub_agents(agents_path.read_text(encoding="utf-8")):
                issues.append(
                    f"stub AGENTS.md (replace with real module index): "
                    f"{agents_path.relative_to(DOCS_DIR)}"
                )

        for path in sorted(folder_path.glob("*.md")):
            changed = update_links(path, at_docs_root=False, check_only=check_only)
            if changed:
                if check_only:
                    issues.append(f"legacy link: {path.relative_to(DOCS_DIR)}")
                else:
                    rewrites.append(path)
                    print(f"Fixed links in {path}")

    for r_file in ("README.md", "AGENTS.md"):
        fp = DOCS_DIR / r_file
        if not fp.is_file():
            continue
        changed = update_links(fp, at_docs_root=True, check_only=check_only)
        if changed:
            if check_only:
                issues.append(f"legacy link: {fp.relative_to(DOCS_DIR)}")
            else:
                rewrites.append(fp)
                print(f"Fixed links in {fp}")

    if check_only:
        if issues:
            print("fix_links --check found issues:", file=sys.stderr)
            for i in issues:
                print(f"  - {i}", file=sys.stderr)
            print(
                f"\nTotal: {len(issues)} issue(s). Run without --check to fix.",
                file=sys.stderr,
            )
            return 1
        print("fix_links --check: no legacy links or stub AGENTS.md files found")
        return 0

    print(f"fix_links: rewrote {len(rewrites)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
