#!/usr/bin/env python3
"""Thin example: state-space compilation only.

Compiles a ``StateSpaceModel`` from the program graph + semantic mappings
and prints variable, observation, action, and preference summaries.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/06_statespace_only.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.statespace.compiler import StateSpaceCompiler  # noqa: E402
from cogant.translate.engine import TranslationEngine  # noqa: E402
from cogant.translate.rules import (  # noqa: E402
    MutatingSubsystemRule,
    OrchestratorRule,
    ReadOnlyInputRule,
    TestAssertionRule,
)


def main() -> int:
    args = parse_args("statespace")
    configure_logging()
    banner("Stage 6: state-space compilation")

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
    mappings = {m.id: m for m in engine.translate(pg)}

    compiler = StateSpaceCompiler(pg, schema_name=target.name)
    model = compiler.compile(mappings)

    print(f"  schema name     : {model.schema_name}")
    print(f"  kind            : {getattr(model, 'kind', 'discrete')}")
    print(f"  state variables : {len(model.variables)}")
    print(f"  observations    : {len(model.observations)}")
    print(f"  actions         : {len(model.actions)}")
    print(f"  transitions     : {len(model.transitions)}")
    print(f"  likelihoods     : {len(model.likelihoods)}")
    print(f"  preferences     : {len(model.preferences)}")

    if model.variables:
        print("\n  state variables (first 5):")
        for var in list(model.variables.values())[:5]:
            card = getattr(var, "cardinality", None)
            print(f"    {var.name:<28}  cardinality={card}")

    if model.observations:
        print("\n  observation modalities (first 5):")
        for obs in list(model.observations.values())[:5]:
            vals = getattr(obs, "values", []) or []
            print(f"    {obs.name:<28}  values={len(vals)}")

    if model.actions:
        print("\n  actions (first 5):")
        for act in list(model.actions.values())[:5]:
            effects = getattr(act, "effects", []) or []
            print(f"    {act.name:<28}  effects={len(effects)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "statespace_summary.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "schema_name": model.schema_name,
                "variables": len(model.variables),
                "observations": len(model.observations),
                "actions": len(model.actions),
                "transitions": len(model.transitions),
                "likelihoods": len(model.likelihoods),
                "preferences": len(model.preferences),
            },
            f,
            indent=2,
            default=str,
        )

    full = args.output_dir / "state_space_model.json"
    try:
        with open(full, "w", encoding="utf-8") as f:
            json.dump(asdict(model), f, indent=2, default=str)
    except (TypeError, ValueError):
        with open(full, "w", encoding="utf-8") as f:
            json.dump({"id": model.id, "schema_name": model.schema_name}, f, indent=2)

    print(f"\n  wrote: {out}")
    print(f"  wrote: {full}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
