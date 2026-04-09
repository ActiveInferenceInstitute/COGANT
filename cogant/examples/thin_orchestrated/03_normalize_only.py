#!/usr/bin/env python3
"""Thin example: normalize stage only.

Canonicalizes language-specific facts into ``NormalizedFact`` records,
each with a stable ``qualified_name``.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/03_normalize_only.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, configure_logging, make_bundle, parse_args  # noqa: E402

from cogant.api.orchestration import run_ingest, run_normalize  # noqa: E402


def main() -> int:
    args = parse_args("normalize")
    configure_logging()
    banner("Stage 3: normalize")

    target = args.target.expanduser().resolve()
    bundle = make_bundle(target)
    run_ingest(str(target), bundle)
    result = run_normalize(bundle)

    facts = result["nodes"]
    kinds = Counter(f["kind"] for f in facts)
    print(f"  total normalized facts : {len(facts)}")
    print("  by kind                :")
    for kind, count in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"    {kind:<24} {count}")

    print("\n  sample qualified names:")
    for f in facts[:10]:
        print(f"    [{f['kind']:<10}] {f['qualified_name']}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "normalize_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  wrote: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
