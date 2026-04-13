#!/usr/bin/env python3
"""Thin example: Graph diff (DriftAnalyzer) via Python API.

Demonstrates detecting architectural and semantic drift between two
versions of a codebase *without* the CLI wrapper:

1. Run the full pipeline on a "baseline" fixture.
2. Mutate the fixture to simulate a change (add a node, remove an edge).
3. Run the full pipeline on the "modified" version.
4. Use ``DriftAnalyzer`` to compute drift metrics:
   - Structural drift (node/edge Jaccard distance)
   - Semantic drift (mapping-kind shift)
   - State-space drift (hidden-state / observation count delta)
   - Architectural drift score (0–100; 0 = identical)
   - Semantic churn score (0–100; 0 = identical)
5. Generate and persist the markdown drift report.

Useful for CI: fail the build when ``architectural_drift > 20`` or
``semantic_churn > 30``.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/30_graph_diff_api.py \\
        --target examples/control_positive/calculator \\
        --output-dir output/thin/graph_diff
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, configure_logging, parse_args  # noqa: E402

# CI thresholds for drift gating
DRIFT_WARN_THRESHOLD = 20.0     # architectural drift score
CHURN_WARN_THRESHOLD = 30.0     # semantic churn score


def main() -> None:
    args = parse_args(description="30 — graph diff / DriftAnalyzer API")
    configure_logging(args.verbose)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    banner("Graph Diff — DriftAnalyzer API")

    # ---- 1. Baseline pipeline run --------------------------------------
    from cogant.config.pipeline import PipelineConfig  # noqa: E402
    from cogant.pipeline.runner import PipelineRunner  # noqa: E402

    target = Path(args.target)
    stages = ["ingest", "static", "graph", "translate", "statespace", "gnn"]

    print("  Running BASELINE pipeline…")
    baseline_dir = output_dir / "baseline"
    baseline_dir.mkdir(exist_ok=True)
    baseline_cfg = PipelineConfig(target=target, output_dir=baseline_dir)
    baseline_result = PipelineRunner(baseline_cfg).run(stages=stages)

    baseline_graph = baseline_result.program_graph
    baseline_bundle = baseline_result.bundle
    if baseline_graph is None or baseline_bundle is None:
        print("ERROR: baseline pipeline failed.")
        sys.exit(1)

    b_nodes = len(baseline_graph.nodes)
    b_edges = len(baseline_graph.edges)
    b_mappings = len(baseline_bundle.semantic_mappings or [])
    print(f"  Baseline: {b_nodes} nodes, {b_edges} edges, {b_mappings} mappings")

    # ---- 2. Simulate a modification (deep-copy + mutation) -------------
    # In real usage you'd point to a different git worktree or repo path.
    # Here we mutate the baseline graph in-memory to keep the example
    # self-contained and not require two separate codebases.

    print("\n  Simulating a code change (adding one synthetic node)…")
    modified_graph = copy.deepcopy(baseline_graph)

    # Add a synthetic "new_service" method node
    from cogant.schemas.core import EdgeKind, NodeKind, ProgramNode  # noqa: E402

    new_id = "synthetic::new_service"
    new_node = ProgramNode(
        id=new_id,
        name="new_service",
        kind=NodeKind.FUNCTION,
        module="synthetic",
        metadata={"decorators": ["staticmethod"]},
    )
    modified_graph.nodes[new_id] = new_node

    # Wire it to the first existing node
    if baseline_graph.nodes:
        first_id = next(iter(baseline_graph.nodes))
        from cogant.schemas.core import ProgramEdge  # noqa: E402

        synthetic_edge = ProgramEdge(
            id=f"edge_{new_id}_to_{first_id}",
            source=new_id,
            target=first_id,
            kind=EdgeKind.CALLS,
        )
        modified_graph.edges[synthetic_edge.id] = synthetic_edge

    m_nodes = len(modified_graph.nodes)
    m_edges = len(modified_graph.edges)
    print(f"  Modified: {m_nodes} nodes (+{m_nodes - b_nodes}), "
          f"{m_edges} edges (+{m_edges - b_edges})")

    # ---- 3. Re-run translate + statespace + gnn on modified graph ------
    print("\n  Re-running translate → statespace → gnn on modified graph…")
    from cogant.translate.engine import TranslationEngine  # noqa: E402
    from cogant.translate.rules import (  # noqa: E402
        ActionRule, MutatingSubsystemRule, ObservationRule, ReadOnlyInputRule,
    )
    from cogant.statespace.compiler import StateSpaceCompiler  # noqa: E402
    from cogant.gnn.bundle import GNNBundle  # noqa: E402

    engine = TranslationEngine()
    for rule in [ReadOnlyInputRule(), MutatingSubsystemRule(), ObservationRule(), ActionRule()]:
        engine.register_rule(rule)

    modified_mappings = engine.translate(modified_graph)
    compiler = StateSpaceCompiler()
    modified_state_space = compiler.compile(modified_graph, {m.id: m for m in modified_mappings})
    modified_bundle = GNNBundle(
        program_graph=modified_graph,
        semantic_mappings={m.id: m for m in modified_mappings},
        state_space=modified_state_space,
    )

    # ---- 4. Run DriftAnalyzer ------------------------------------------
    from cogant.export.drift import DriftAnalyzer  # noqa: E402

    banner("DriftAnalyzer Results")
    analyzer = DriftAnalyzer(baseline_bundle, modified_bundle)
    drift_report = analyzer.analyze()

    arch_score = drift_report.architectural_drift_score
    churn_score = drift_report.semantic_churn_score

    print(f"  Architectural drift score : {arch_score:.1f} / 100")
    print(f"  Semantic churn score      : {churn_score:.1f} / 100")

    if hasattr(drift_report, "structural_drift"):
        print(f"  Structural drift (Jaccard) : {drift_report.structural_drift:.4f}")
    if hasattr(drift_report, "mapping_delta"):
        delta = drift_report.mapping_delta
        print(f"  Mapping delta             : {delta:+d} mappings")

    # ---- 5. Markdown report --------------------------------------------
    if hasattr(analyzer, "to_markdown"):
        md = analyzer.to_markdown()
        md_path = output_dir / "drift_report.md"
        md_path.write_text(md)
        print(f"\n  Drift report (Markdown) → {md_path}")

    # ---- 6. CI gate ----------------------------------------------------
    banner("CI Gate")
    issues: list[str] = []
    if arch_score > DRIFT_WARN_THRESHOLD:
        issues.append(f"Architectural drift {arch_score:.1f} > threshold {DRIFT_WARN_THRESHOLD}")
    if churn_score > CHURN_WARN_THRESHOLD:
        issues.append(f"Semantic churn {churn_score:.1f} > threshold {CHURN_WARN_THRESHOLD}")

    if issues:
        for issue in issues:
            print(f"  ⚠ {issue}")
        print("\n  Result: WARN — drift metrics exceeded; review before merging.")
    else:
        print(f"  ✓ Architectural drift {arch_score:.1f} ≤ {DRIFT_WARN_THRESHOLD}")
        print(f"  ✓ Semantic churn      {churn_score:.1f} ≤ {CHURN_WARN_THRESHOLD}")
        print("\n  Result: PASS — within acceptable drift bounds.")

    # ---- 7. Persist JSON summary ---------------------------------------
    summary = {
        "baseline_nodes": b_nodes,
        "baseline_edges": b_edges,
        "baseline_mappings": b_mappings,
        "modified_nodes": m_nodes,
        "modified_edges": m_edges,
        "architectural_drift_score": arch_score,
        "semantic_churn_score": churn_score,
        "ci_pass": len(issues) == 0,
    }
    summary_path = output_dir / "drift_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"  JSON summary → {summary_path}")

    banner("Done")
    sys.exit(0 if not issues else 1)


if __name__ == "__main__":
    main()
