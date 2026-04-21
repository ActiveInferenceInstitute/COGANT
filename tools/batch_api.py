"""In-process wrappers for COGANT Python APIs that are stub-only at the CLI.

The CLI commands ``cogant analyze-graph``, ``cogant analyze-static``,
``cogant export`` (multi-format), and ``cogant visualize`` are stubs in
v0.5.0 — they print "Not yet fully implemented" and emit no files.
This module exposes the real computations by calling the Python API
classes those stubs reference, so the batch runner can produce real
artifacts today.

Each public function writes files under ``run_dir`` and prints its
outputs to stdout (absolute paths, one per line) so a subprocess caller
can parse them.

Typical usage::

    python tools/batch_api.py graph-analysis  --run-dir <path> --bundle <json>
    python tools/batch_api.py static-analysis --run-dir <path> --target  <src>
    python tools/batch_api.py multi-export    --run-dir <path> --bundle <json>
    python tools/batch_api.py visualize       --run-dir <path> --target  <src>

Exit 0 on success. Non-zero if an API is unavailable or inputs are bad.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("batch_api")


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def _to_jsonable(obj: Any) -> Any:
    """Recursively coerce dataclasses / sets / Paths to JSON-native types."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        try:
            return sorted(_to_jsonable(v) for v in obj)
        except TypeError:
            return [_to_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        # Covers simple objects; fall back to str if that fails.
        try:
            return {k: _to_jsonable(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
        except Exception:
            return str(obj)
    return obj


def _write_json(out: Path, data: Any) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_to_jsonable(data), indent=2, default=str), encoding="utf-8")
    print(str(out))


# ---------------------------------------------------------------------------
# Graph analysis (cogant.graph.GraphAnalyzer)
# ---------------------------------------------------------------------------


def _load_program_graph(target: Path) -> Any:
    """Build a fresh ProgramGraph from a source directory via the orchestration
    pipeline. We intentionally do NOT round-trip the bundle.json because there
    is no public ProgramGraph deserializer; the cost of re-ingest on a single
    target is small (~50ms on control_positive)."""
    from cogant.api.bundle import Bundle
    from cogant.api import orchestration

    bundle = Bundle(target=str(target))
    orchestration.run_ingest(str(target), bundle)
    orchestration.run_static(bundle)
    orchestration.run_normalize(bundle)
    orchestration.run_graph(bundle, str(target))
    pg = bundle.artifacts.get("_program_graph")
    if pg is None:
        raise RuntimeError(f"failed to build ProgramGraph for {target}")
    return pg


def run_graph_analysis(run_dir: Path, target: Path) -> int:
    from cogant.graph import GraphAnalyzer

    graph = _load_program_graph(target)
    analyzer = GraphAnalyzer(graph)
    metrics = analyzer.compute_metrics()
    centrality = analyzer.compute_centrality()
    cycles = analyzer.find_cycles()
    hotspots = analyzer.find_hotspots(top_n=10)

    out_dir = run_dir / "analysis"
    _write_json(out_dir / "graph_metrics.json", metrics)
    _write_json(out_dir / "graph_centrality.json", centrality)
    _write_json(out_dir / "graph_cycles.json", cycles)
    _write_json(out_dir / "graph_hotspots.json", hotspots)
    return 0


# ---------------------------------------------------------------------------
# Static analysis (cogant.static.*)
# ---------------------------------------------------------------------------


def run_static_analysis(run_dir: Path, target: Path) -> int:
    from cogant.static import (
        ComplexityAnalyzer,
        DeadCodeAnalyzer,
        MetricsAnalyzer,
    )

    python_files = sorted(p for p in target.rglob("*.py") if p.is_file())
    if not python_files:
        logger.warning("no .py files under %s — skipping static analysis", target)
        return 0

    c_ana = ComplexityAnalyzer()
    d_ana = DeadCodeAnalyzer()
    m_ana = MetricsAnalyzer()

    per_file: list[dict[str, Any]] = []
    total_complexity = 0
    total_dead = 0
    total_loc = 0

    for p in python_files:
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("skip %s: %s", p, exc)
            continue
        try:
            cxr = c_ana.analyze(src, p)
            dcr = d_ana.analyze(src, p)
            code_metrics = m_ana.compute(src)
            halstead = m_ana.halstead(src)
        except Exception as exc:
            logger.warning("analyzer error on %s: %s", p, exc)
            continue

        hotspots = cxr.get_hotspots(10) if hasattr(cxr, "get_hotspots") else []
        total_complexity += getattr(cxr, "max_cyclomatic", 0) or 0
        total_dead += len(getattr(dcr, "entries", []))
        total_loc += getattr(code_metrics, "lines_of_code", 0) or 0
        per_file.append(
            {
                "path": str(p.relative_to(target)),
                "complexity": _to_jsonable(cxr),
                "dead_code": _to_jsonable(dcr),
                "metrics": _to_jsonable(code_metrics),
                "halstead": _to_jsonable(halstead),
                "hotspot_count": len(hotspots),
            }
        )

    out = run_dir / "analysis" / "static_report.json"
    _write_json(
        out,
        {
            "target": str(target),
            "file_count": len(per_file),
            "total_lines_of_code": total_loc,
            "cumulative_max_cyclomatic": total_complexity,
            "total_dead_entries": total_dead,
            "per_file": per_file,
        },
    )
    return 0


# ---------------------------------------------------------------------------
# Multi-format export (cogant.export.MultiFormatExporter)
# ---------------------------------------------------------------------------


def run_multi_export(run_dir: Path, bundle_path: Path) -> int:
    from cogant.export import ExportConfig, ExportFormat, MultiFormatExporter

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    out_dir = run_dir / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    config = ExportConfig(
        formats=[ExportFormat.JSON, ExportFormat.GRAPHML, ExportFormat.JSONLINES],
        output_dir=str(out_dir),
        prefix="cogant",
        overwrite=True,
    )
    exporter = MultiFormatExporter()
    results = exporter.export_gnn_bundle(bundle, config)
    manifest = {fmt.value: str(path) for fmt, path in results.items()}
    _write_json(out_dir / "exports_manifest.json", manifest)
    return 0


# ---------------------------------------------------------------------------
# Visualization (cogant.viz.MermaidGenerator + png_export)
# ---------------------------------------------------------------------------


def run_visualize(run_dir: Path, target: Path) -> int:
    from cogant.viz import MermaidGenerator

    graph = _load_program_graph(target)
    gen = MermaidGenerator()

    out_dir = run_dir / "diagrams"
    out_dir.mkdir(parents=True, exist_ok=True)

    diagrams: dict[str, str] = {}
    for name, fn in (
        ("class_diagram.mmd", lambda: gen.generate_class_diagram(graph)),
        ("dependency_graph.mmd", lambda: gen.generate_dependency_graph(graph)),
        ("sequence_diagram.mmd", lambda: gen.generate_sequence_diagram(graph=graph)),
    ):
        try:
            text = fn()
        except Exception as exc:
            logger.warning("mermaid %s failed: %s", name, exc)
            continue
        dest = out_dir / name
        dest.write_text(text, encoding="utf-8")
        diagrams[name] = str(dest)
        print(str(dest))

    _write_json(out_dir / "diagrams_manifest.json", diagrams)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ga = sub.add_parser("graph-analysis")
    p_ga.add_argument("--run-dir", type=Path, required=True)
    p_ga.add_argument("--target", type=Path, required=True)

    p_sa = sub.add_parser("static-analysis")
    p_sa.add_argument("--run-dir", type=Path, required=True)
    p_sa.add_argument("--target", type=Path, required=True)

    p_me = sub.add_parser("multi-export")
    p_me.add_argument("--run-dir", type=Path, required=True)
    p_me.add_argument("--bundle", type=Path, required=True)

    p_vz = sub.add_parser("visualize")
    p_vz.add_argument("--run-dir", type=Path, required=True)
    p_vz.add_argument("--target", type=Path, required=True)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.cmd == "graph-analysis":
        return run_graph_analysis(args.run_dir, args.target)
    if args.cmd == "static-analysis":
        return run_static_analysis(args.run_dir, args.target)
    if args.cmd == "multi-export":
        return run_multi_export(args.run_dir, args.bundle)
    if args.cmd == "visualize":
        return run_visualize(args.run_dir, args.target)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
