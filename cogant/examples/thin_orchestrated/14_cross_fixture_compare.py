#!/usr/bin/env python3
"""Thin example: cross-fixture comparison.

Runs the ingest -> graph -> translate -> statespace -> process pipeline
across all three control-positive fixtures (calculator, flask_mini,
event_pipeline) and prints a side-by-side comparison table. Useful for
sanity-checking that the pipeline scales sensibly with repo complexity.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/14_cross_fixture_compare.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging  # noqa: E402

from cogant.process.extractor import ProcessExtractor  # noqa: E402
from cogant.statespace.compiler import StateSpaceCompiler  # noqa: E402
from cogant.translate.confidence import ConfidenceModel  # noqa: E402
from cogant.translate.engine import TranslationEngine  # noqa: E402
from cogant.translate.rules import (  # noqa: E402
    MutatingSubsystemRule,
    OrchestratorRule,
    ReadOnlyInputRule,
    TestAssertionRule,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ["calculator", "flask_mini", "event_pipeline"]


def _run_fixture(fixture: str) -> dict:
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
    mappings_list = engine.translate(pg)
    ConfidenceModel().score_batch(mappings_list)
    mappings = {m.id: m for m in mappings_list}

    ss = StateSpaceCompiler(pg, schema_name=fixture).compile(mappings)
    pm = ProcessExtractor(pg, schema_name=fixture).extract()

    return {
        "fixture": fixture,
        "nodes": pg.node_count(),
        "edges": pg.edge_count(),
        "mappings": len(mappings),
        "state_vars": len(ss.variables),
        "observations": len(ss.observations),
        "actions": len(ss.actions),
        "transitions": len(ss.transitions),
        "likelihoods": len(ss.likelihoods),
        "preferences": len(ss.preferences),
        "process_stages": len(pm.stages),
        "process_connections": len(pm.connections),
    }


def main() -> int:
    configure_logging()
    banner("Higher-order: cross-fixture comparison")

    results = []
    for fixture in FIXTURES:
        print(f"\n  running: {fixture}")
        results.append(_run_fixture(fixture))

    cols = [
        ("fixture", "fixture"),
        ("nodes", "nodes"),
        ("edges", "edges"),
        ("mappings", "maps"),
        ("state_vars", "vars"),
        ("observations", "obs"),
        ("actions", "acts"),
        ("transitions", "trns"),
        ("likelihoods", "lkh"),
        ("preferences", "pref"),
        ("process_stages", "stgs"),
        ("process_connections", "conn"),
    ]

    widths = {key: max(len(label), max(len(str(r[key])) for r in results)) for key, label in cols}

    header = "  " + "  ".join(f"{label:<{widths[key]}}" for key, label in cols)
    sep = "  " + "  ".join("-" * widths[key] for key, _ in cols)
    print(f"\n{header}\n{sep}")
    for r in results:
        row = "  " + "  ".join(f"{str(r[key]):<{widths[key]}}" for key, _ in cols)
        print(row)

    out_dir = REPO_ROOT / "output" / "thin" / "cross_fixture_compare"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "compare.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  wrote: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
