#!/usr/bin/env python3
"""Thin example: Incremental analysis (cogant changed) and benchmark-style timing.

This script demonstrates:

  1. Show the ``cogant changed --help`` CLI command (showing it exists and what
     it does).
  2. Demonstrate the Python-level equivalent using ``PipelineConfig(incremental_since=...)``
     to enable incremental re-analysis of only changed files.
  3. Demonstrate benchmark-style performance measurement using context managers
     and the ``profiling_enabled`` flag.
  4. Compare wall-time on calculator fixture vs incremental mode (when applicable).

Run from the repo root:

    PYTHONPATH=py python examples/thin_orchestrated/25_changed_and_benchmark.py \\
        --target examples/control_positive/calculator \\
        --output-dir output/thin/changed_benchmark
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import banner, build_rich_graph, configure_logging, parse_args  # noqa: E402

from cogant.api.pipeline import PipelineConfig, PipelineRunner  # noqa: E402


def main() -> int:
    """Entry point for the incremental analysis + benchmark demo."""
    args = parse_args("changed_benchmark")
    configure_logging()
    banner("Stage 25: Incremental analysis and benchmarking")

    # 1. Show the CLI command help
    print("\n  CLI command: cogant changed --help")
    print("  " + "=" * 56)
    try:
        result = subprocess.run(
            ["cogant", "changed", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Print help with a slight indent
            for line in result.stdout.split("\n")[:15]:  # First 15 lines
                print(f"  {line}")
        else:
            print(f"  (cogant CLI not available; error: {result.stderr[:100]})")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"  (cogant CLI not available: {type(e).__name__})")

    # 2. Benchmark full analysis on the calculator fixture
    target = args.target.expanduser().resolve()
    print(f"\n  target repository: {target}")

    print("\n  benchmark: full pipeline run (no incremental)")
    print("  " + "-" * 56)

    config = PipelineConfig(
        stages=["ingest", "static", "normalize", "graph"],
        output_dir=str(args.output_dir / "full_run"),
        profiling_enabled=True,
    )

    t0 = time.perf_counter()
    runner = PipelineRunner(target=str(target), config=config)
    result = runner.run()
    dt_full = (time.perf_counter() - t0) * 1000.0

    print(f"    wall time: {dt_full:.1f} ms")
    print(f"    bundle nodes: {result.bundle.metadata.get('node_count', '?')}")
    print(f"    bundle edges: {result.bundle.metadata.get('edge_count', '?')}")

    # 3. Demonstrate incremental config (without actually running a cached
    # version, since we're in a fresh checkout)
    print("\n  incremental mode (python API):")
    print("  " + "-" * 56)

    incremental_config = PipelineConfig(
        stages=["ingest", "static", "normalize", "graph"],
        output_dir=str(args.output_dir / "incremental_run"),
        profiling_enabled=True,
        incremental_since="HEAD~1",  # Would re-parse only files changed since HEAD~1
        cache_dir=str(args.output_dir / "cache"),
    )

    print(f"    incremental_since: {incremental_config.incremental_since}")
    print(f"    cache_dir: {incremental_config.cache_dir}")
    print(f"    skip_stages: {incremental_config.skip_stages}")

    # 4. Show the difference using pure-Python graph building
    print("\n  direct graph building (no pipeline):")
    print("  " + "-" * 56)

    t0 = time.perf_counter()
    pg = build_rich_graph(target)
    dt_build = (time.perf_counter() - t0) * 1000.0

    print(f"    wall time: {dt_build:.1f} ms")
    print(f"    graph nodes: {pg.node_count()}")
    print(f"    graph edges: {pg.edge_count()}")

    # 5. Summary table
    print("\n  timing summary:")
    print(f"  {'Method':<35} {'Time (ms)':<12} {'Speedup':<10}")
    print(f"  {'-' * 35} {'-' * 12} {'-' * 10}")
    print(f"  {'full pipeline run':<35} {dt_full:<12.1f} {'1.0x':<10}")
    print(
        f"  {'direct graph building':<35} {dt_build:<12.1f} {f'{dt_full / dt_build:.1f}x' if dt_build > 0 else '?':<10}"
    )

    if dt_build > 0:
        ratio = dt_full / dt_build
        print(f"\n  (Pipeline overhead ~{(ratio - 1) * 100:.0f}% vs direct build)")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  output dir: {args.output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
