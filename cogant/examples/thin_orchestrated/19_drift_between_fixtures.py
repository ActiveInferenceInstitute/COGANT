#!/usr/bin/env python3
"""Thin example: drift analysis between two fixtures.

Uses ``DriftAnalyzer`` to compare the bundles produced from two
control-positive fixtures (treated as "before" and "after" snapshots).
This is the smallest end-to-end demo of the drift scoring surface:
architectural drift, semantic churn, and per-component deltas.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/19_drift_between_fixtures.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging  # noqa: E402

from cogant.process.extractor import ProcessExtractor  # noqa: E402
from cogant.scoring.drift import DriftAnalyzer  # noqa: E402
from cogant.statespace.compiler import StateSpaceCompiler  # noqa: E402
from cogant.translate.engine import TranslationEngine  # noqa: E402
from cogant.translate.rules import (  # noqa: E402
    MutatingSubsystemRule,
    OrchestratorRule,
    ReadOnlyInputRule,
    TestAssertionRule,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _bundle_for(fixture: str) -> dict:
    target = REPO_ROOT / "examples" / "control_positive" / fixture
    pg = build_rich_graph(target)

    engine = TranslationEngine()
    for rule in (
        ReadOnlyInputRule(),
        MutatingSubsystemRule(),
        OrchestratorRule(),
        TestAssertionRule(),
    ):
        engine.register_rule(rule)
    mappings = {m.id: m for m in engine.translate(pg)}

    state_space = StateSpaceCompiler(pg, schema_name=fixture).compile(mappings)
    process_model = ProcessExtractor(pg, schema_name=fixture).extract()

    return {
        "graph": {
            "nodes": [
                {"id": n.id, "kind": str(n.kind), "name": n.name}
                for n in pg.nodes.values()
            ],
            "edges": [
                {"source": e.source_id, "target": e.target_id, "kind": str(e.kind)}
                for e in pg.edges.values()
            ],
        },
        "state_space": {
            "variables": list(state_space.variables),
            "observations": list(state_space.observations),
            "actions": list(state_space.actions),
            "transitions": list(state_space.transitions),
            "likelihoods": list(state_space.likelihoods),
            "preferences": list(state_space.preferences),
        },
        "mappings": {
            mid: {
                "id": m.id,
                "kind": m.kind.value if hasattr(m.kind, "value") else str(m.kind),
                "semantic_label": getattr(m, "semantic_label", ""),
            }
            for mid, m in mappings.items()
        },
        "process": {
            "stage_count": len(process_model.stages),
            "connection_count": len(process_model.connections),
        },
    }


def main() -> int:
    configure_logging()
    banner("Higher-order: drift analysis between fixtures")

    print("\n  building baseline bundle (calculator)...")
    bundle_a = _bundle_for("calculator")
    print(
        f"    nodes={len(bundle_a['graph']['nodes'])}  "
        f"edges={len(bundle_a['graph']['edges'])}  "
        f"mappings={len(bundle_a['mappings'])}"
    )

    print("\n  building current bundle (event_pipeline)...")
    bundle_b = _bundle_for("event_pipeline")
    print(
        f"    nodes={len(bundle_b['graph']['nodes'])}  "
        f"edges={len(bundle_b['graph']['edges'])}  "
        f"mappings={len(bundle_b['mappings'])}"
    )

    analyzer = DriftAnalyzer(bundle_a, bundle_b)
    score = analyzer._compute_drift_score()

    print("\n  drift scores:")
    print(f"    total           : {score.total_score:.3f}")
    print(f"    architectural   : {score.architectural_score:.3f}")
    print(f"    semantic churn  : {score.semantic_churn_score:.3f}")

    print("\n  per-component details:")
    for key, value in (score.details or {}).items():
        if isinstance(value, dict):
            sub = ", ".join(
                f"{k}={len(v) if isinstance(v, (list, dict, set)) else v}"
                for k, v in list(value.items())[:6]
            )
            print(f"    {key:<22} {sub}")
        else:
            print(f"    {key:<22} {value}")

    out_dir = REPO_ROOT / "output" / "thin" / "drift_between_fixtures"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "drift_summary.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(asdict(score), f, indent=2, default=str)
    print(f"\n  wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
