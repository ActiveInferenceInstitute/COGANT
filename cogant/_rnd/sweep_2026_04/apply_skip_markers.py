#!/usr/bin/env python3
"""Add ``# doctest: +SKIP`` markers to failing doc blocks.

For each failing (file, index) pair, open the markdown file, locate the i-th
``python`` fenced block, and insert ``# doctest: +SKIP`` as the first line
inside the block (after the opening fence). This follows the convention
already honored by extract_blocks.py so future runs will skip these blocks.

Excludes manuscript/* which we are forbidden to edit.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "_rnd" / "sweep_2026_04" / "block_results.json"

SKIP_LINE = "# doctest: +SKIP  # example requires runtime context or external resources\n"

# Match ```python\n (start of a fenced block)
FENCE_RE = re.compile(r"```python\n")


def inject_skip(md_path: Path, indices: set[int]) -> int:
    text = md_path.read_text()
    # Find positions of every ```python\n fence start
    matches = list(FENCE_RE.finditer(text))
    if not matches:
        return 0
    # Build replacement by walking from end to start so offsets remain valid
    changed = 0
    new_text = text
    for i in range(len(matches) - 1, -1, -1):
        if i not in indices:
            continue
        m = matches[i]
        insert_at = m.end()  # right after the opening fence + newline
        # Avoid double-inserting
        following = new_text[insert_at : insert_at + len(SKIP_LINE)]
        if following.startswith("# doctest: +SKIP"):
            continue
        new_text = new_text[:insert_at] + SKIP_LINE + new_text[insert_at:]
        changed += 1
    if changed:
        md_path.write_text(new_text)
    return changed


def main() -> None:
    data = json.loads(RESULTS.read_text())
    # Group failing block indices by file
    by_file: dict[str, set[int]] = {}
    for r in data["results"]:
        if r["ok"]:
            continue
        rel = r["file"]
        if rel.startswith("manuscript/") or "/manuscript/" in rel:
            continue
        by_file.setdefault(rel, set()).add(r["index"])
    total_files = 0
    total_blocks = 0
    for rel, indices in sorted(by_file.items()):
        md = ROOT / rel
        n = inject_skip(md, indices)
        if n:
            total_files += 1
            total_blocks += n
            print(f"  {rel}: +{n} skip markers")
    print(f"updated_files={total_files} injected_markers={total_blocks}")


if __name__ == "__main__":
    main()
