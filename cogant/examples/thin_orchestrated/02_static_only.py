#!/usr/bin/env python3
"""Thin example: static analysis stage only.

Parses every Python file in the target with ``PythonASTParser`` and prints
per-module function/class/import counts.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/02_static_only.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, configure_logging, make_bundle, parse_args  # noqa: E402

from cogant.api.orchestration import run_ingest, run_static  # noqa: E402


def main() -> int:
    args = parse_args("static")
    configure_logging()
    banner("Stage 2: static analysis")

    target = args.target.expanduser().resolve()
    bundle = make_bundle(target)
    run_ingest(str(target), bundle)
    result = run_static(bundle)

    modules = result["modules"]
    print(f"  modules parsed   : {len(modules)}")
    total_fns = sum(m["functions"] for m in modules)
    total_cls = sum(m["classes"] for m in modules)
    total_imp = sum(m["imports"] for m in modules)
    print(f"  total functions  : {total_fns}")
    print(f"  total classes    : {total_cls}")
    print(f"  total imports    : {total_imp}")
    print(f"  parse errors     : {sum(len(m['errors']) for m in modules)}")

    print("\n  per-module breakdown:")
    for m in modules:
        print(
            f"    {m['relative_path']:<40} fns={m['functions']:>3}  "
            f"cls={m['classes']:>2}  imp={m['imports']:>3}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "static_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  wrote: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
