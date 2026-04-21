#!/usr/bin/env python3
"""Thin example: visualization export only.

Exercises the ``cogant.viz`` package end-to-end by producing artifacts
from every visualizer class: program graph (D3/SVG), semantic graph,
Gantt/timeline, Mermaid diagrams, diff view scaffolding, dashboard.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/18_viz_export_only.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.process.extractor import ProcessExtractor  # noqa: E402
from cogant.statespace.compiler import StateSpaceCompiler  # noqa: E402
from cogant.translate.engine import TranslationEngine  # noqa: E402
from cogant.translate.rules import (  # noqa: E402
    MutatingSubsystemRule,
    OrchestratorRule,
    ReadOnlyInputRule,
    TestAssertionRule,
)
from cogant.viz.graph_view import GraphVisualizer  # noqa: E402
from cogant.viz.mermaid import MermaidGenerator  # noqa: E402


def _try(label: str, fn, results: dict):
    try:
        out = fn()
        results[label] = {"ok": True, "result": str(out) if out else "ok"}
        print(f"  [OK]    {label}")
    except Exception as exc:
        results[label] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        print(f"  [SKIP]  {label}  ({type(exc).__name__}: {exc})")


def main() -> int:
    args = parse_args("viz_export")
    configure_logging()
    banner("Higher-order: visualization export")

    target = args.target.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    pg = build_rich_graph(target)
    print(f"  graph nodes : {pg.node_count()}")
    print(f"  graph edges : {pg.edge_count()}")

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

    results: dict[str, dict] = {}

    # Program graph: D3 HTML and SVG export
    gv = GraphVisualizer()
    gv.from_typed_graph(pg).cluster_by_kind()
    _try(
        "graph_view.html",
        lambda: gv.render_html(str(args.output_dir / "graph_view.html")),
        results,
    )
    _try(
        "graph_view.svg",
        lambda: gv.render_svg(str(args.output_dir / "graph_view.svg")),
        results,
    )
    _try(
        "graph_view.d3.json",
        lambda: (args.output_dir / "graph_view.d3.json").write_text(
            json.dumps(gv.to_d3_json(), indent=2, default=str)
        ),
        results,
    )

    # Mermaid diagrams
    mg = MermaidGenerator()
    _try(
        "mermaid.class_diagram",
        lambda: (args.output_dir / "class_diagram.mmd").write_text(mg.generate_class_diagram(pg)),
        results,
    )
    _try(
        "mermaid.dependency_graph",
        lambda: (args.output_dir / "dependency_graph.mmd").write_text(
            mg.generate_dependency_graph(pg)
        ),
        results,
    )
    _try(
        "mermaid.state_diagram",
        lambda: (args.output_dir / "state_diagram.mmd").write_text(
            mg.generate_state_diagram(state_space)
        ),
        results,
    )
    _try(
        "mermaid.sequence_diagram",
        lambda: (args.output_dir / "sequence_diagram.mmd").write_text(
            mg.generate_sequence_diagram(process_model=process_model, graph=pg)
        ),
        results,
    )
    _try(
        "mermaid.active_inference_diagram",
        lambda: (args.output_dir / "active_inference.mmd").write_text(
            mg.generate_active_inference_diagram(state_space)
        ),
        results,
    )

    # Try optional visualizers; report cleanly if their APIs require
    # shapes the thin example doesn't produce.
    try:
        from cogant.viz.semantic_view import SemanticVisualizer

        def _coerce(items, kind_label):
            out = []
            for item in items or []:
                if hasattr(item, "name"):
                    out.append(
                        {
                            "name": item.name,
                            "description": f"{kind_label}",
                            "type": kind_label,
                        }
                    )
                else:
                    out.append(
                        {
                            "name": str(item),
                            "description": f"{kind_label} ({item})",
                            "type": kind_label,
                        }
                    )
            return out

        sv = SemanticVisualizer()
        _try(
            "semantic_view.html",
            lambda: sv.from_state_space(
                {
                    "states": _coerce(state_space.variables, "state variable"),
                    "observations": _coerce(state_space.observations, "observation"),
                    "actions": _coerce(state_space.actions, "action"),
                    "policies": [],
                    "transitions": [],
                }
            ).render_html(str(args.output_dir / "semantic_view.html")),
            results,
        )
    except Exception as exc:
        results["semantic_view.html"] = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(f"  [SKIP]  semantic_view.html  ({type(exc).__name__}: {exc})")

    try:
        from cogant.viz.gantt import GanttRenderer

        gr = GanttRenderer()
        stage_list = [
            {
                "id": s.id,
                "name": s.name,
                "duration": 1.0,
                "pattern": getattr(s, "pattern_type", "sequential"),
            }
            for s in process_model.stages.values()
        ]
        _try(
            "gantt.html",
            lambda: gr.from_process_model(
                {
                    "stages": stage_list,
                    "timeline": {"start": 0, "end": max(1, len(stage_list))},
                }
            ).render_html(str(args.output_dir / "gantt.html")),
            results,
        )
    except Exception as exc:
        results["gantt.html"] = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(f"  [SKIP]  gantt.html  ({type(exc).__name__}: {exc})")

    # Summary
    ok = sum(1 for r in results.values() if r.get("ok"))
    total = len(results)
    print(f"\n  visualizers ok : {ok}/{total}")
    on_disk = sorted(p.name for p in args.output_dir.iterdir() if p.is_file())
    print(f"  files written  : {len(on_disk)}")
    for n in on_disk[:12]:
        print(f"    - {n}")
    if len(on_disk) > 12:
        print(f"    ... and {len(on_disk) - 12} more")

    out = args.output_dir / "viz_export_summary.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(
            {"ok": ok, "total": total, "results": results, "files": on_disk},
            f,
            indent=2,
            default=str,
        )
    print(f"\n  wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
