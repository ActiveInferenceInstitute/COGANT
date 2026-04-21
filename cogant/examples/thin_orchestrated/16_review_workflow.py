#!/usr/bin/env python3
"""Thin example: human review workflow.

Demonstrates ``ReviewManager`` curating a set of semantic mappings
(accept / reject / edit), and shows how the resulting review history
layers onto the auto-generated mappings as first-class provenance.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/16_review_workflow.py
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
from cogant.translate.review import ReviewManager  # noqa: E402
from cogant.translate.rules import TranslationRule  # noqa: E402


def _all_rules() -> list[type[TranslationRule]]:
    out = []
    for _, obj in inspect.getmembers(rule_mod, inspect.isclass):
        if obj is TranslationRule:
            continue
        if issubclass(obj, TranslationRule) and not inspect.isabstract(obj):
            out.append(obj)
    return out


def main() -> int:
    args = parse_args("review_workflow")
    configure_logging()
    banner("Higher-order: human review workflow")

    target = args.target.expanduser().resolve()
    pg = build_rich_graph(target)

    engine = TranslationEngine()
    for cls in _all_rules():
        try:
            engine.register_rule(cls())
        except Exception:
            pass

    mappings = engine.translate(pg)
    ConfidenceModel().score_batch(mappings)
    print(f"  auto mappings : {len(mappings)}")

    reviewer = ReviewManager()
    for m in mappings:
        reviewer.add_mapping(m)

    # Synthetic review policy:
    # - accept the top-3 highest-confidence mappings
    # - reject anything below 0.70
    # - edit any MutatingSubsystem (hs_) mapping to add a clarifying description
    sorted_by_conf = sorted(
        mappings,
        key=lambda m: float(getattr(m, "confidence_score", 0) or 0),
        reverse=True,
    )

    accepted = 0
    rejected = 0
    edited = 0

    for m in sorted_by_conf[:3]:
        if reviewer.accept_mapping(m.id, reviewer="alice", feedback="top-conf sample"):
            accepted += 1

    for m in mappings:
        conf = float(getattr(m, "confidence_score", 0) or 0)
        if conf < 0.70 and m.status == "auto_proposed":
            if reviewer.reject_mapping(m.id, reviewer="bob", reason="low confidence"):
                rejected += 1

    for m in mappings:
        if m.id.startswith("hs_") and m.status == "auto_proposed":
            if reviewer.edit_mapping(
                m.id,
                reviewer="carol",
                updates={"description": "Manually clarified hidden-state subsystem"},
            ):
                edited += 1

    summary = reviewer.get_review_summary()
    history = reviewer.get_review_history()

    print("\n  review actions:")
    print(f"    accepted : {accepted}")
    print(f"    rejected : {rejected}")
    print(f"    edited   : {edited}")

    print("\n  status distribution after review:")
    statuses = Counter(m.status for m in reviewer.mappings.values())
    for st, count in statuses.most_common():
        print(f"    {st:<18} {count}")

    print("\n  summary:")
    for k, v in summary.items():
        print(f"    {k:<24} {v}")

    print(f"\n  history entries: {len(history)}")
    for entry in history[:3]:
        print(
            f"    - {entry.get('action', '?'):<8} "
            f"mapping={entry.get('mapping_id', '?')} "
            f"reviewer={entry.get('reviewer', '?')}"
        )

    # Upgraded confidence check
    human = [
        m
        for m in reviewer.mappings.values()
        if getattr(m, "confidence_tier", None)
        and (
            m.confidence_tier.value
            if hasattr(m.confidence_tier, "value")
            else str(m.confidence_tier)
        )
        == "human_reviewed"
    ]
    print(f"\n  mappings promoted to HUMAN_REVIEWED tier: {len(human)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "review_workflow.json"
    payload = {
        "auto_mapping_count": len(mappings),
        "accepted": accepted,
        "rejected": rejected,
        "edited": edited,
        "status_distribution": dict(statuses),
        "summary": summary,
        "history_length": len(history),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\n  wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
