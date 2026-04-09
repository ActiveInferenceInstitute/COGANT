#!/usr/bin/env python3
"""Thin example: ingest stage only.

Discovers files in a repository, classifies them by language, and dumps
the resulting ``RepoSnapshot`` summary to disk.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/01_ingest_only.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running directly from the examples folder
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, configure_logging, make_bundle, parse_args  # noqa: E402

from cogant.api.orchestration import run_ingest  # noqa: E402


def main() -> int:
    args = parse_args("ingest")
    configure_logging()
    banner("Stage 1: ingest")

    target = args.target.expanduser().resolve()
    if not target.exists():
        print(f"ERROR: target does not exist: {target}")
        return 1

    bundle = make_bundle(target)
    result = run_ingest(str(target), bundle)

    print(f"  files discovered : {result['file_count']}")
    print(f"  languages        : {sorted(result['language_distribution'].keys())}")
    print(f"  language counts  : {result['language_distribution']}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "ingest_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  wrote: {out}")

    snapshot = bundle.artifacts.get("repo_snapshot")
    if snapshot is not None:
        files_out = args.output_dir / "files.json"
        files_dump = [
            {
                "relative_path": fi.relative_path,
                "language": fi.language,
                "size": getattr(fi, "size", None),
            }
            for fi in snapshot.files
        ]
        with open(files_out, "w", encoding="utf-8") as f:
            json.dump(files_dump, f, indent=2)
        print(f"  wrote: {files_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
