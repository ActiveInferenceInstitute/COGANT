#!/usr/bin/env python3
"""Thin example: deep dive into translation rules.

Instead of running the four-rule default set, this script registers
**every** translation rule available and reports per-rule match counts.
Useful when authoring or debugging a new rule.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/11_translate_rules_only.py
"""

from __future__ import annotations

import inspect
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.translate import rules as rule_mod  # noqa: E402
from cogant.translate.confidence import ConfidenceModel  # noqa: E402
from cogant.translate.engine import TranslationEngine  # noqa: E402
from cogant.translate.rules import TranslationRule  # noqa: E402


def _discover_rule_classes() -> list[type[TranslationRule]]:
    classes: list[type[TranslationRule]] = []
    for _, obj in inspect.getmembers(rule_mod, inspect.isclass):
        if obj is TranslationRule:
            continue
        if not issubclass(obj, TranslationRule):
            continue
        if inspect.isabstract(obj):
            continue
        classes.append(obj)
    return classes


def main() -> int:
    args = parse_args("translate_rules")
    configure_logging()
    banner("Stage 5 (deep): every translation rule")

    target = args.target.expanduser().resolve()
    pg = build_rich_graph(target)
    print(f"  graph nodes : {pg.node_count()}")
    print(f"  graph edges : {pg.edge_count()}")

    rule_classes = _discover_rule_classes()
    print(f"  rule count  : {len(rule_classes)}")

    engine = TranslationEngine()
    skipped: list[str] = []
    for cls in rule_classes:
        try:
            engine.register_rule(cls())
        except Exception as exc:
            skipped.append(f"{cls.__name__}: {exc}")

    if skipped:
        print(f"\n  skipped (could not instantiate): {len(skipped)}")
        for s in skipped[:5]:
            print(f"    - {s}")

    mappings = engine.translate(pg)
    confidence_model = ConfidenceModel()
    confidence_model.score_batch(mappings)

    by_role = Counter(m.kind.value if hasattr(m.kind, "value") else str(m.kind) for m in mappings)
    by_prefix = Counter((m.id.split("_", 1)[0] if "_" in m.id else m.id) for m in mappings)

    print(f"\n  total mappings : {len(mappings)}")
    print("\n  by id prefix (rule family, descending):")
    for prefix, count in by_prefix.most_common():
        print(f"    {prefix:<12} {count}")

    print("\n  by role (MappingKind):")
    for role, count in sorted(by_role.items(), key=lambda kv: -kv[1]):
        print(f"    {role:<18} {count}")

    confidences = [
        float(m.confidence_score)
        for m in mappings
        if getattr(m, "confidence_score", None) is not None
    ]
    if confidences:
        avg = sum(confidences) / len(confidences)
        print(f"\n  mean confidence : {avg:.3f}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "all_rules_summary.json"
    payload = {
        "rule_count": len(rule_classes),
        "rules": [cls.__name__ for cls in rule_classes],
        "skipped": skipped,
        "by_id_prefix": dict(by_prefix),
        "by_role": dict(by_role),
        "total_mappings": len(mappings),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\n  wrote: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
