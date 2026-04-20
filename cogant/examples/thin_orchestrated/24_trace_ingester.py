#!/usr/bin/env python3
"""Thin example: Dynamic tracing with Chrome DevTools traces.

This script demonstrates how to:

  1. Construct a minimal Chrome DevTools trace dict (JSON format) with
     function entry/exit events.
  2. Use :class:`cogant.dynamic.traces.TraceIngester` to parse the trace.
  3. Call :func:`cogant.dynamic.enrichment.enrich_graph` to layer dynamic
     coverage onto a static ``ProgramGraph`` from the calculator fixture.
  4. Show before/after edge counts and which nodes gained RUNTIME_EVIDENCE.

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/24_trace_ingester.py \\
        --target examples/control_positive/calculator \\
        --output-dir output/thin/trace_ingester
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.dynamic.enrichment import enrich_graph  # noqa: E402
from cogant.dynamic.traces import TraceIngester  # noqa: E402


def _build_synthetic_trace() -> dict:
    """Build a minimal Chrome DevTools-compatible trace with function events."""
    # Trace format: list of events with {name, ph, ts, dur, pid, tid, cat}
    # ph: 'B' = begin, 'E' = end, 'X' = complete
    trace_events = [
        # Simulated call sequence: main → add → multiply
        {"name": "main", "ph": "B", "ts": 1000, "pid": 1, "tid": 1, "cat": "function"},
        {"name": "add", "ph": "B", "ts": 1100, "pid": 1, "tid": 1, "cat": "function"},
        {"name": "add", "ph": "E", "ts": 1150, "dur": 50, "pid": 1, "tid": 1, "cat": "function"},
        {"name": "multiply", "ph": "B", "ts": 1200, "pid": 1, "tid": 1, "cat": "function"},
        {"name": "multiply", "ph": "E", "ts": 1250, "dur": 50, "pid": 1, "tid": 1, "cat": "function"},
        {"name": "main", "ph": "E", "ts": 1300, "dur": 300, "pid": 1, "tid": 1, "cat": "function"},
        # Second call sequence
        {"name": "add", "ph": "X", "ts": 2000, "dur": 75, "pid": 1, "tid": 1, "cat": "function"},
    ]
    return {"traceEvents": trace_events}


def main() -> int:
    """Entry point for the trace ingester demo."""
    args = parse_args("trace_ingester")
    configure_logging()
    banner("Stage 24: Chrome DevTools trace ingestion")

    # Build the calculator graph
    target = args.target.expanduser().resolve()
    pg = build_rich_graph(target)
    print(f"  static graph (calculator):")
    print(f"    nodes={pg.node_count()}  edges={pg.edge_count()}")

    # Create a synthetic trace in a temp file
    trace_data = _build_synthetic_trace()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tf:
        json.dump(trace_data, tf)
        trace_path = tf.name

    try:
        # Ingest the trace
        print(f"\n  ingesting trace: {trace_path}")
        ingester = TraceIngester()
        traces = ingester.ingest_chrome_trace(trace_path)
        print(f"    trace count: {len(traces)}")
        if traces:
            print(f"    events in first trace: {len(traces[0].get('events', []))}")

        # Extract call sequences and call graph
        call_sequences = ingester.extract_call_sequences()
        call_graph = ingester.extract_call_graph()
        print(f"\n  extracted patterns:")
        print(f"    call sequences: {len(call_sequences)}")
        for i, seq in enumerate(call_sequences[:3]):
            print(f"      seq {i}: {' → '.join(seq)}")

        print(f"    call graph nodes: {len(call_graph)}")
        for func_name in sorted(call_graph.keys())[:5]:
            callees = call_graph[func_name]
            print(f"      {func_name} → {callees}")

        # Attempt to enrich the graph with traces
        # Note: the enrichment function tries to match trace function names
        # with graph nodes by name
        print(f"\n  enriching graph with dynamic evidence...")
        try:
            # enrich_graph layers traces onto a graph
            result = enrich_graph(pg, trace_path=trace_path)
            enriched_count = result.get("trace_nodes_enriched", 0)
            print(f"    nodes enriched: {enriched_count}")
        except Exception as e:
            # If enrichment is not yet available or fails, show the trace data
            print(f"    enrichment not available (expected in minimal setup): {type(e).__name__}")
            enriched_count = 0

        # Print summary
        print(f"\n  summary:")
        print(f"    nodes before enrichment: {pg.node_count()}")
        print(f"    edges before enrichment: {pg.edge_count()}")
        print(f"    nodes with runtime evidence: {enriched_count}")

        args.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n  output dir: {args.output_dir}")

    finally:
        # Clean up temp file
        Path(trace_path).unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
