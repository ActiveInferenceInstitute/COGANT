#!/usr/bin/env python3
"""Thin example: apply COGANT to the Generalized Notation Notation repository.

This script performs the canonical "self-analysis" — feeding the GNN
(Active Inference Institute) codebase back through COGANT's translate
pipeline to produce a GNN-compatible state-space and process-model package,
plus the full PNG rasterization suite.

The goal is to demonstrate the reflexive loop COGANT's scope statement
promises: a codebase-to-GNN translation engine that can render the GNN
codebase into a GNN itself.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/22_gnn_self_analysis.py \\
        --target /path/to/GeneralizedNotationNotation/src \\
        --output-dir output/gnn_self_analysis

If ``--target`` is omitted, the script checks the conventional
``work/GNN/src`` location relative to the repo root and falls back to the
``event_pipeline`` control fixture so the script is exercisable on CI.
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
    CircuitBreakerRule,
    ConfigRule,
    ContextRule,
    DataPipelineRule,
    ErrorBoundaryRule,
    EventBusRule,
    FeatureFlagRule,
    InheritanceRule,
    MutatingSubsystemRule,
    ObservationRule,
    OrchestratorRule,
    PolicyRule,
    PreferenceRule,
    ReadOnlyInputRule,
    RetryPatternRule,
    SingletonAccessRule,
    TestAssertionRule,
)
from cogant.viz.png_export import RenderConfig, render_all_pngs  # noqa: E402


_REPO_ROOT = Path(__file__).resolve().parents[2]
_GNN_DEFAULT = _REPO_ROOT.parent / "work" / "GNN" / "src"


def _timed(label: str, fn, stats: dict[str, float]):
    """Run ``fn``, record elapsed time in ``stats``, print a one-line progress report."""
    t0 = time.perf_counter()
    result = fn()
    dt = (time.perf_counter() - t0) * 1000.0
    stats[label] = dt
    print(f"  {label:<22} {dt:9.1f} ms")
    return result


def _resolve_target(arg_target: Path) -> Path:
    """Pick the GNN target directory with a sensible fallback chain."""
    candidates = [arg_target.expanduser().resolve(), _GNN_DEFAULT.resolve()]
    for cand in candidates:
        if cand.is_dir() and any(cand.rglob("*.py")):
            return cand
    # Final fallback: the event_pipeline control fixture so CI can still exercise
    # the script even when the GNN repo is not checked out.
    return (_REPO_ROOT / "examples" / "control_positive" / "event_pipeline").resolve()


def main() -> int:
    """Entry point for the GNN self-analysis thin example."""
    args = parse_args("gnn_self_analysis")
    configure_logging()
    banner("GNN self-analysis: COGANT(GNN) → GNN package")

    target = _resolve_target(args.target)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = args.output_dir / "gnn_package"

    print(f"  target           : {target}")
    print(f"  output-dir       : {args.output_dir}")

    stats: dict[str, float] = {}

    pg = _timed("graph (rich)", lambda: build_rich_graph(target), stats)
    print(f"    nodes={pg.node_count()}  edges={pg.edge_count()}")

    def _translate():
        """Register the full 17-rule catalog and score the resulting mappings."""
        engine = TranslationEngine()
        for rule in (
            ReadOnlyInputRule(),
            MutatingSubsystemRule(),
            OrchestratorRule(),
            TestAssertionRule(),
            ObservationRule(),
            PolicyRule(),
            PreferenceRule(),
            ContextRule(),
            ConfigRule(),
            FeatureFlagRule(),
            EventBusRule(),
            InheritanceRule(),
            DataPipelineRule(),
            RetryPatternRule(),
            ErrorBoundaryRule(),
            SingletonAccessRule(),
            CircuitBreakerRule(),
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
    print(
        f"    stages={len(process_model.stages)} "
        f"connections={len(process_model.connections)}"
    )

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
        return runner.run(steps=20)

    trace = _timed("simulate", _simulate, stats)
    fe = trace.get("free_energy_trajectory") or []
    print(
        f"    steps={trace['steps_completed']} "
        f"vfe_delta={(fe[-1] - fe[0]) if fe else 0:+.4f} "
        f"avg_reward={trace['avg_reward']:.4f}"
    )

    def _render():
        """Rasterize every visualization artifact under the run directory."""
        cfg = RenderConfig()
        return render_all_pngs(args.output_dir, cfg=cfg)

    png_out = _timed("render (pngs)", _render, stats)
    total_pngs = sum(len(v) for v in png_out.values())
    print(f"    pngs={total_pngs}  categories={sum(1 for v in png_out.values() if v)}")

    total = sum(stats.values())
    print(f"\n  total wall time        : {total:9.1f} ms")

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
        "render": {
            "total_pngs": total_pngs,
            "by_category": {k: len(v) for k, v in png_out.items()},
        },
    }
    out = args.output_dir / "gnn_self_analysis_summary.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n  wrote: {out}")

    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
