#!/usr/bin/env python3
"""Thin example: translate stage only.

Runs the four default translation rules over a freshly built program
graph and prints the resulting ``SemanticMapping`` summary, grouped by
role.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/05_translate_only.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.translate.confidence import ConfidenceModel  # noqa: E402
from cogant.translate.engine import TranslationEngine  # noqa: E402
from cogant.translate.rules import (  # noqa: E402
    MutatingSubsystemRule,
    OrchestratorRule,
    ReadOnlyInputRule,
    TestAssertionRule,
)


def main() -> int:
    args = parse_args("translate")
    configure_logging()
    banner("Stage 5: translate")

    target = args.target.expanduser().resolve()
    pg = build_rich_graph(target)
    print(f"  graph nodes : {pg.node_count()}")
    print(f"  graph edges : {pg.edge_count()}")

    engine = TranslationEngine()
    engine.register_rule(ReadOnlyInputRule())
    engine.register_rule(MutatingSubsystemRule())
    engine.register_rule(OrchestratorRule())
    engine.register_rule(TestAssertionRule())

    mappings = engine.translate(pg)
    confidence_model = ConfidenceModel()
    confidence_model.score_batch(mappings)

    print(f"\n  total mappings : {len(mappings)}")

    by_role: Counter[str] = Counter()
    by_id_prefix: Counter[str] = Counter()
    confidences: list[float] = []
    for m in mappings:
        role = m.kind.value if hasattr(m.kind, "value") else str(m.kind)
        by_role[role] += 1
        prefix = m.id.split("_", 1)[0] if "_" in m.id else m.id
        by_id_prefix[prefix] += 1
        if getattr(m, "confidence_score", None) is not None:
            confidences.append(float(m.confidence_score))

    print("\n  mappings by role (MappingKind):")
    for role, count in sorted(by_role.items(), key=lambda kv: -kv[1]):
        print(f"    {role:<18} {count}")

    print("\n  mappings by id prefix (rule family):")
    for prefix, count in sorted(by_id_prefix.items(), key=lambda kv: -kv[1]):
        print(f"    {prefix:<10} {count}")

    if confidences:
        avg = sum(confidences) / len(confidences)
        print(f"\n  mean confidence : {avg:.3f}")
        print(f"  min confidence  : {min(confidences):.3f}")
        print(f"  max confidence  : {max(confidences):.3f}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "translate_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "mapping_count": len(mappings),
                "by_role": dict(by_role),
                "by_id_prefix": dict(by_id_prefix),
            },
            f,
            indent=2,
            default=str,
        )
    print(f"\n  wrote: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
