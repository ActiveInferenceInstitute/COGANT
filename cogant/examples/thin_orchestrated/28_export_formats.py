#!/usr/bin/env python3
"""Thin example: Export GNN bundle to all supported formats.

Demonstrates the full export matrix:

  1. **GNN Markdown** — human-readable AII spec bundle (``model.gnn.md``)
  2. **GNN JSON**     — machine-readable section-by-section equivalent
  3. **GraphML**      — graph topology for Gephi / yEd / NetworkX
  4. **Parquet**      — columnar node/edge tables for DuckDB / pandas
  5. **HDF5**         — tensor tables for PyTorch / NumPy (optional)
  6. **SVG**          — visual rendering of the program graph

Each export is timed; the script prints a size/time comparison table so
you can choose the right format for your downstream tool.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/28_export_formats.py \\
        --target examples/control_positive/calculator \\
        --output-dir output/thin/export_formats
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, configure_logging, parse_args  # noqa: E402


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _run_export(label: str, fn: Any, *args: Any, **kwargs: Any) -> tuple[float, int]:
    """Run ``fn(*args, **kwargs)`` and return (elapsed_ms, output_bytes)."""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = (time.perf_counter() - t0) * 1000
    size = 0
    if isinstance(result, Path) and result.exists():
        size = result.stat().st_size
    elif isinstance(result, str):
        size = len(result.encode())
    elif isinstance(result, bytes):
        size = len(result)
    return elapsed, size


def main() -> None:
    args = parse_args(description="28 — export GNN bundle to all formats")
    configure_logging(args.verbose)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    banner("Export All Formats")

    # ---- 1. Run full pipeline to GNN bundle ----------------------------
    from cogant.config.pipeline import PipelineConfig  # noqa: E402
    from cogant.pipeline.runner import PipelineRunner  # noqa: E402

    config = PipelineConfig(target=Path(args.target), output_dir=output_dir)
    runner = PipelineRunner(config)

    print("  Running pipeline (ingest → graph → translate → statespace → gnn)…")
    t_pipe = time.perf_counter()
    result = runner.run(stages=["ingest", "static", "graph", "translate", "statespace", "gnn"])
    pipe_ms = (time.perf_counter() - t_pipe) * 1000
    print(f"  Pipeline done in {pipe_ms:.0f} ms")

    bundle = result.bundle
    if bundle is None:
        print("ERROR: pipeline did not produce a GNN bundle.")
        sys.exit(1)

    # ---- 2. GNN Markdown export ----------------------------------------
    results: list[dict] = []

    try:
        from cogant.gnn.exporter import GNNExporter  # noqa: E402

        md_path = output_dir / "model.gnn.md"
        t0 = time.perf_counter()
        exporter = GNNExporter(bundle)
        markdown = exporter.to_markdown()
        md_path.write_text(markdown)
        elapsed = (time.perf_counter() - t0) * 1000
        results.append(
            {
                "format": "GNN Markdown",
                "file": md_path.name,
                "size": md_path.stat().st_size,
                "ms": elapsed,
                "ok": True,
            }
        )
        print(f"  ✓ GNN Markdown  → {md_path.name} ({_fmt_bytes(md_path.stat().st_size)})")
    except Exception as exc:
        results.append(
            {
                "format": "GNN Markdown",
                "file": "—",
                "size": 0,
                "ms": 0,
                "ok": False,
                "error": str(exc),
            }
        )
        print(f"  ✗ GNN Markdown  → {exc}")

    # ---- 3. GNN JSON export --------------------------------------------
    try:
        from cogant.gnn.json_export import GNNJSONExporter  # noqa: E402

        json_path = output_dir / "model.gnn.json"
        t0 = time.perf_counter()
        json_exporter = GNNJSONExporter(bundle)
        json_data = json_exporter.export()
        json_path.write_text(json.dumps(json_data, indent=2))
        elapsed = (time.perf_counter() - t0) * 1000
        results.append(
            {
                "format": "GNN JSON",
                "file": json_path.name,
                "size": json_path.stat().st_size,
                "ms": elapsed,
                "ok": True,
            }
        )
        print(f"  ✓ GNN JSON      → {json_path.name} ({_fmt_bytes(json_path.stat().st_size)})")
    except Exception as exc:
        results.append(
            {"format": "GNN JSON", "file": "—", "size": 0, "ms": 0, "ok": False, "error": str(exc)}
        )
        print(f"  ✗ GNN JSON      → {exc}")

    # ---- 4. GraphML export ----------------------------------------------
    try:
        from cogant.export.graphml import GraphMLExporter  # noqa: E402

        graphml_path = output_dir / "program_graph.graphml"
        t0 = time.perf_counter()
        gml_exporter = GraphMLExporter(result.program_graph)
        gml_exporter.export(graphml_path)
        elapsed = (time.perf_counter() - t0) * 1000
        size = graphml_path.stat().st_size
        results.append(
            {
                "format": "GraphML",
                "file": graphml_path.name,
                "size": size,
                "ms": elapsed,
                "ok": True,
            }
        )
        print(f"  ✓ GraphML       → {graphml_path.name} ({_fmt_bytes(size)})")
    except Exception as exc:
        results.append(
            {"format": "GraphML", "file": "—", "size": 0, "ms": 0, "ok": False, "error": str(exc)}
        )
        print(f"  ✗ GraphML       → {exc}")

    # ---- 5. Parquet export (columnar node/edge tables) ------------------
    try:
        from cogant.export.parquet import ParquetExporter  # noqa: E402

        parquet_dir = output_dir / "parquet"
        parquet_dir.mkdir(exist_ok=True)
        t0 = time.perf_counter()
        pq_exporter = ParquetExporter(result.program_graph, bundle)
        pq_exporter.export(parquet_dir)
        elapsed = (time.perf_counter() - t0) * 1000
        total_size = sum(f.stat().st_size for f in parquet_dir.glob("*.parquet"))
        results.append(
            {
                "format": "Parquet",
                "file": "parquet/*.parquet",
                "size": total_size,
                "ms": elapsed,
                "ok": True,
            }
        )
        print(f"  ✓ Parquet       → parquet/ ({_fmt_bytes(total_size)})")
    except Exception as exc:
        results.append(
            {"format": "Parquet", "file": "—", "size": 0, "ms": 0, "ok": False, "error": str(exc)}
        )
        print(f"  ✗ Parquet       → {exc}")

    # ---- 6. Summary table ----------------------------------------------
    banner("Format Comparison")
    header = f"  {'Format':<18} {'File':<28} {'Size':>10} {'Time (ms)':>10} {'Status':>8}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for r in results:
        status = "✓ ok" if r["ok"] else "✗ err"
        size_str = _fmt_bytes(r["size"]) if r["ok"] else "—"
        ms_str = f"{r['ms']:.1f}" if r["ok"] else "—"
        print(f"  {r['format']:<18} {r['file']:<28} {size_str:>10} {ms_str:>10} {status:>8}")

    # ---- 7. Persist comparison JSON ------------------------------------
    summary_path = output_dir / "export_comparison.json"
    summary_path.write_text(json.dumps(results, indent=2))
    print(f"\n  Comparison table → {summary_path}")
    banner("Done")


if __name__ == "__main__":
    main()
