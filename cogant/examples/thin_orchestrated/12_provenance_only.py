#!/usr/bin/env python3
"""Thin example: provenance walk.

Demonstrates that every node, edge, and semantic mapping in a COGANT
bundle carries provenance — and shows how to walk it.

Provenance is COGANT's first-class trust mechanism: every exported
element must trace back to a source span or a declared inference rule.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/12_provenance_only.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.translate.engine import TranslationEngine  # noqa: E402
from cogant.translate.rules import (  # noqa: E402
    MutatingSubsystemRule,
    OrchestratorRule,
    ReadOnlyInputRule,
    TestAssertionRule,
)


def main() -> int:
    args = parse_args("provenance")
    configure_logging()
    banner("Cross-cutting: provenance walk")

    target = args.target.expanduser().resolve()
    pg = build_rich_graph(target)

    engine = TranslationEngine()
    for rule in (
        ReadOnlyInputRule(),
        MutatingSubsystemRule(),
        OrchestratorRule(),
        TestAssertionRule(),
    ):
        engine.register_rule(rule)
    mappings_list = engine.translate(pg)
    mappings = {m.id: m for m in mappings_list}

    nodes_total = pg.node_count()
    nodes_with_prov = sum(
        1 for n in pg.nodes.values() if getattr(n, "provenance", None) or getattr(n, "metadata", None)
    )
    edges_total = pg.edge_count()
    edges_with_prov = sum(
        1
        for e in pg.edges.values()
        if getattr(e, "evidence_sources", None) or getattr(e, "metadata", None)
    )
    mappings_total = len(mappings)
    mappings_with_provenance = sum(
        1 for m in mappings.values() if getattr(m, "provenance", None)
    )

    print("  coverage:")
    print(f"    nodes    : {nodes_with_prov}/{nodes_total} have metadata or provenance")
    print(f"    edges    : {edges_with_prov}/{edges_total} have metadata or evidence sources")
    print(f"    mappings : {mappings_with_provenance}/{mappings_total} have provenance")

    prefix_counter: Counter[str] = Counter()
    role_counter: Counter[str] = Counter()
    for m in mappings.values():
        prefix = m.id.split("_", 1)[0] if "_" in m.id else m.id
        prefix_counter[prefix] += 1
        role = m.kind.value if hasattr(m.kind, "value") else str(m.kind)
        role_counter[role] += 1

    if prefix_counter:
        print("\n  mappings by id prefix (rule family):")
        for prefix, count in prefix_counter.most_common(10):
            print(f"    {prefix:<32} {count}")

    if role_counter:
        print("\n  mappings by semantic role (MappingKind):")
        for role, count in role_counter.most_common():
            print(f"    {role:<14} {count}")

    sample = next(iter(mappings.values()), None)
    if sample is not None:
        prov = getattr(sample, "provenance", []) or []
        kind = sample.kind.value if hasattr(sample.kind, "value") else str(sample.kind)
        print(f"\n  sample mapping: {sample.id}")
        print(f"    kind         : {kind}")
        print(f"    confidence   : {getattr(sample, 'confidence_score', '?')}")
        print(f"    provenance # : {len(prov)}")
        for pv in prov[:3]:
            print(
                f"      - source={getattr(pv, 'source', '?')} "
                f"confidence={getattr(pv, 'confidence', '?')} "
                f"metadata_keys={list((getattr(pv, 'metadata', {}) or {}).keys())}"
            )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "provenance_summary.json"
    payload = {
        "nodes_total": nodes_total,
        "nodes_with_provenance": nodes_with_prov,
        "edges_total": edges_total,
        "edges_with_provenance": edges_with_prov,
        "mappings_total": mappings_total,
        "mappings_with_provenance": mappings_with_provenance,
        "mappings_by_id_prefix": dict(prefix_counter),
        "mappings_by_role": dict(role_counter),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\n  wrote: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
