#!/usr/bin/env python3
"""Extract Python code blocks from docs/*.md and classify runnable ones."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
OUT = ROOT / "_rnd" / "sweep_2026_04" / "blocks"
OUT.mkdir(parents=True, exist_ok=True)

# Match ```python ... ``` blocks
PATTERN = re.compile(r"```python\n(.*?)```", re.DOTALL)

# A block is "runnable" if it imports from cogant and looks self-contained
def is_runnable(block: str) -> bool:
    has_cogant_import = bool(
        re.search(r"^\s*(import\s+cogant|from\s+cogant(\.|\s+import))", block, re.MULTILINE)
    )
    if not has_cogant_import:
        return False
    # Skip blocks that are obviously snippet-only (start with `...` or have undefined refs)
    stripped = block.strip()
    if stripped.startswith("..."):
        return False
    # Skip blocks that include `# doctest: +SKIP`
    if "# doctest: +SKIP" in block:
        return False
    return True


def main() -> None:
    catalog: list[dict] = []
    n_files = 0
    n_blocks = 0
    n_runnable = 0
    for md in sorted(DOCS.rglob("*.md")):
        if "manuscript" in md.parts:
            continue
        text = md.read_text()
        blocks = PATTERN.findall(text)
        if not blocks:
            continue
        n_files += 1
        for i, block in enumerate(blocks):
            n_blocks += 1
            runnable = is_runnable(block)
            entry = {
                "file": str(md.relative_to(ROOT)),
                "index": i,
                "lines": block.count("\n") + 1,
                "runnable": runnable,
                "preview": block[:120].replace("\n", " "),
            }
            if runnable:
                n_runnable += 1
                # Write block to disk
                stem = md.stem.replace(".", "_")
                fp = OUT / f"{stem}__{i:02d}.py"
                fp.write_text(block)
                entry["block_file"] = str(fp.relative_to(ROOT))
            catalog.append(entry)
    summary = {
        "files_with_python": n_files,
        "total_blocks": n_blocks,
        "runnable_blocks": n_runnable,
        "blocks": catalog,
    }
    out_json = ROOT / "_rnd" / "sweep_2026_04" / "block_catalog.json"
    out_json.write_text(json.dumps(summary, indent=2))
    print(f"files_with_python={n_files}")
    print(f"total_blocks={n_blocks}")
    print(f"runnable_blocks={n_runnable}")
    print(f"catalog={out_json}")


if __name__ == "__main__":
    main()
