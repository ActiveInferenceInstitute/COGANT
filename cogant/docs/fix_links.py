"""Rewrite links from old monolithic guide filenames to ``../<module>/README.md``.

Run from the package root (directory containing ``docs/``):

    uv run python docs/fix_links.py
"""

from __future__ import annotations

import re
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


def update_links(filepath: Path, *, at_docs_root: bool) -> bool:
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
    if content != original:
        filepath.write_text(content, encoding="utf-8")
        return True
    return False


def main() -> None:
    for folder in FILE_TO_FOLDER.values():
        folder_path = DOCS_DIR / folder
        if not folder_path.is_dir():
            continue

        agents_path = folder_path / "AGENTS.md"
        if not agents_path.is_file():
            agents_path.write_text(
                f"# AGENTS.md — {folder.title()} Module\n\n"
                f"This directory houses the deeply modularized documentation for the **{folder.title()}** "
                "aspects of the COGANT translation engine.\n\n"
                "## Maintenance Rules\n\n"
                "*   **Granularity**: Keep articles focused. Do not reintroduce monolithic, multi-context files.\n"
                "*   **Cross-Linking**: When referencing other modules, link to their respective "
                "`../module_name/README.md` indexes.\n",
                encoding="utf-8",
            )

        for path in sorted(folder_path.glob("*.md")):
            if update_links(path, at_docs_root=False):
                print(f"Fixed links in {path}")

    for r_file in ("README.md", "AGENTS.md"):
        fp = DOCS_DIR / r_file
        if not fp.is_file():
            continue
        if update_links(fp, at_docs_root=True):
            print(f"Fixed links in {fp}")


if __name__ == "__main__":
    main()
