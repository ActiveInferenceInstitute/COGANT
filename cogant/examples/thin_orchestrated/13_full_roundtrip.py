#!/usr/bin/env python3
"""Thin example: complete round-trip in a single script.

Wires stages 1-10 together manually, without using the
``RoundtripOrchestrator``. This script is the reference implementation for
"what does the thin API look like end-to-end?" and prints per-stage timings
alongside the key output metrics.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/13_full_roundtrip.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.gnn.package import GNNPackageBuilder  # noqa: E402
from cogant.gnn.runner import GNNModelRunner  # noqa: E402
from cogant.gnn.validator import GNNValidator  # noqa: E402
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

STEPS = 20


def _timed(label: str, fn, stats: dict[str, float]):
    t0 = time.perf_counter()
    result = fn()
    dt = (time.perf_counter() - t0) * 1000.0
    stats[label] = dt
    print(f"  {label:<22} {dt:7.1f} ms")
    return result


def main() -> int:
    args = parse_args("full_roundtrip")
    configure_logging()
    banner("Higher-order: end-to-end thin round-trip")

    target = args.target.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = args.output_dir / "gnn_package"

    stats: dict[str, float] = {}

    pg = _timed(
        "graph (rich)",
        lambda: build_rich_graph(target),
        stats,
    )
    print(f"    nodes={pg.node_count()}  edges={pg.edge_count()}")

    def _translate():
        engine = TranslationEngine()
        for rule in (
            ReadOnlyInputRule(),
            MutatingSubsystemRule(),
            OrchestratorRule(),
            TestAssertionRule(),
        ):
            engine.register_rule(rule)
        out = engine.translate(pg)
        ConfidenceModel().score_batch(out)
        return out

    mappings_list = _timed("translate", _translate, stats)
    mappings = {m.id: m for m in mappings_list}
    print(f"    mappings={len(mappings)}")

    state_space = _timed(
        "statespace",
        lambda: StateSpaceCompiler(pg, schema_name=target.name).compile(mappings),
        stats,
    )
    print(
        f"    vars={len(state_space.variables)} "
        f"obs={len(state_space.observations)} "
        f"acts={len(state_space.actions)}"
    )

    process_model = _timed(
        "process",
        lambda: ProcessExtractor(pg, schema_name=target.name).extract(),
        stats,
    )
    print(f"    stages={len(process_model.stages)} connections={len(process_model.connections)}")

    def _export():
        builder = GNNPackageBuilder(
            graph=pg,
            state_space=state_space,
            process_model=process_model,
            mappings=mappings,
            config={"repo_name": target.name},
        )
        return builder.build(str(package_dir))

    _timed("export (gnn)", _export, stats)
    print(f"    package={package_dir}")

    def _validate():
        return GNNValidator().validate_package(str(package_dir))

    result = _timed("validate", _validate, stats)
    print(f"    score={result.score:.1f}%  errors={len(result.errors)}")

    def _simulate():
        runner = GNNModelRunner()
        runner.load_package(str(package_dir))
        return runner.run(steps=STEPS)

    trace = _timed("simulate", _simulate, stats)
    fe = trace.get("free_energy_trajectory") or []
    print(
        f"    steps={trace['steps_completed']} "
        f"vfe_delta={(fe[-1] - fe[0]) if fe else 0:+.4f} "
        f"avg_reward={trace['avg_reward']:.4f}"
    )

    total = sum(stats.values())
    print(f"\n  total wall time        : {total:7.1f} ms")

    summary = {
        "target": str(target),
        "stages_ms": stats,
        "total_ms": total,
        "graph": {"nodes": pg.node_count(), "edges": pg.edge_count()},
        "translate": {"mapping_count": len(mappings)},
        "statespace": {
            "variables": len(state_space.variables),
            "observations": len(state_space.observations),
            "actions": len(state_space.actions),
        },
        "process": {
            "stages": len(process_model.stages),
            "connections": len(process_model.connections),
        },
        "validate": {
            "score": result.score,
            "errors": len(result.errors),
            "warnings": len(result.warnings),
        },
        "simulate": {
            "steps": trace["steps_completed"],
            "avg_reward": trace["avg_reward"],
            "vfe_delta": (fe[-1] - fe[0]) if fe else 0.0,
        },
    }
    out = args.output_dir / "roundtrip_summary.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n  wrote: {out}")

    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
