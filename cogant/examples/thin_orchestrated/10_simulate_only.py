#!/usr/bin/env python3
"""Thin example: Active Inference simulation only.

Loads an existing GNN package, runs the ``GNNModelRunner`` for N steps
under the Active Inference loop (Bayesian belief update + EFE-based
policy selection), and prints free-energy and reward summaries.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/10_simulate_only.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.gnn.package import GNNPackageBuilder  # noqa: E402
from cogant.gnn.runner import GNNModelRunner  # noqa: E402
from cogant.process.extractor import ProcessExtractor  # noqa: E402
from cogant.statespace.compiler import StateSpaceCompiler  # noqa: E402
from cogant.translate.engine import TranslationEngine  # noqa: E402
from cogant.translate.rules import (  # noqa: E402
    MutatingSubsystemRule,
    OrchestratorRule,
    ReadOnlyInputRule,
    TestAssertionRule,
)

STEPS = 20


def _build_package(target: Path, package_dir: Path) -> None:
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
    state_space = StateSpaceCompiler(pg, schema_name=target.name).compile(mappings)
    process_model = ProcessExtractor(pg, schema_name=target.name).extract()
    GNNPackageBuilder(
        graph=pg,
        state_space=state_space,
        process_model=process_model,
        mappings=mappings,
        config={"repo_name": target.name},
    ).build(str(package_dir))


def main() -> int:
    args = parse_args("simulate")
    configure_logging()
    banner(f"Stage 10: Active Inference simulation ({STEPS} steps)")

    target = args.target.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = args.output_dir / "gnn_package"

    if not package_dir.exists():
        print("  no GNN package present, building one first...")
        _build_package(target, package_dir)

    runner = GNNModelRunner()
    runner.load_package(str(package_dir))
    trace = runner.run(steps=STEPS)

    print(f"  steps completed   : {trace['steps_completed']}")
    print(f"  total reward      : {trace['total_reward']:.4f}")
    print(f"  avg reward        : {trace['avg_reward']:.4f}")

    fe = trace.get("free_energy_trajectory") or []
    if fe:
        print(f"  initial VFE       : {fe[0]:.4f}")
        print(f"  final VFE         : {fe[-1]:.4f}")
        print(f"  VFE delta         : {fe[-1] - fe[0]:+.4f}")

    print("\n  action distribution:")
    for act, count in sorted(trace.get("action_distribution", {}).items(), key=lambda kv: -kv[1]):
        print(f"    {act:<28} {count}")

    out = args.output_dir / "execution_trace.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, default=str)
    print(f"\n  wrote: {out}")

    report = runner.generate_execution_report(trace)
    report_path = args.output_dir / "execution_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  wrote: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
