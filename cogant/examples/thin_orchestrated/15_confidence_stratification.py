#!/usr/bin/env python3
"""Thin example: confidence stratification.

Registers every available translation rule, scores the resulting mappings
with ``ConfidenceModel``, and groups them by ``ConfidenceTier``. Prints
distributions, tier means, and a sampled mapping from each tier so you
can see what the confidence model considers weak vs. strong evidence.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/15_confidence_stratification.py
"""

from __future__ import annotations

import inspect
import json
import sys
from collections import Counter, defaultdict
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


def _tier_str(mapping) -> str:
    tier = getattr(mapping, "confidence_tier", None)
    if tier is None:
        return "unscored"
    return tier.value if hasattr(tier, "value") else str(tier)


def main() -> int:
    args = parse_args("confidence_stratification")
    configure_logging()
    banner("Higher-order: confidence stratification")

    target = args.target.expanduser().resolve()
    pg = build_rich_graph(target)
    print(f"  graph nodes : {pg.node_count()}")
    print(f"  graph edges : {pg.edge_count()}")

    engine = TranslationEngine()
    for cls in _discover_rule_classes():
        try:
            engine.register_rule(cls())
        except Exception:
            pass

    mappings = engine.translate(pg)
    ConfidenceModel().score_batch(mappings)
    print(f"  total mappings : {len(mappings)}")

    by_tier: dict[str, list] = defaultdict(list)
    for m in mappings:
        by_tier[_tier_str(m)].append(m)

    print("\n  by confidence tier (count / mean / min / max):")
    tier_summary: dict[str, dict] = {}
    for tier, ms in sorted(by_tier.items(), key=lambda kv: -len(kv[1])):
        scores = [float(m.confidence_score) for m in ms if getattr(m, "confidence_score", None) is not None]
        mean = sum(scores) / len(scores) if scores else 0.0
        lo = min(scores) if scores else 0.0
        hi = max(scores) if scores else 0.0
        print(f"    {tier:<22} n={len(ms):<3} mean={mean:.3f}  range=[{lo:.3f}, {hi:.3f}]")
        tier_summary[tier] = {
            "count": len(ms),
            "mean": mean,
            "min": lo,
            "max": hi,
        }

    # Per-tier sample with rule family and role
    print("\n  sample mapping per tier:")
    for tier, ms in sorted(by_tier.items()):
        if not ms:
            continue
        best = max(ms, key=lambda m: float(getattr(m, "confidence_score", 0) or 0))
        kind = best.kind.value if hasattr(best.kind, "value") else str(best.kind)
        prefix = best.id.split("_", 1)[0] if "_" in best.id else best.id
        print(
            f"    [{tier}] id={best.id} kind={kind} "
            f"prefix={prefix} score={float(best.confidence_score or 0):.3f} "
            f"evidence_count={getattr(best, 'evidence_count', 0)} "
            f"diversity={getattr(best, 'evidence_diversity', 0):.2f}"
        )

    # Per-rule family breakdown
    family = Counter(
        (m.id.split("_", 1)[0] if "_" in m.id else m.id) for m in mappings
    )
    print("\n  rule family distribution (by id prefix):")
    for prefix, count in family.most_common():
        print(f"    {prefix:<10} {count}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "confidence_stratification.json"
    payload = {
        "total_mappings": len(mappings),
        "by_tier": tier_summary,
        "by_id_prefix": dict(family),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\n  wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
