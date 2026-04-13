"""Python vs Rust backend benchmark for COGANT.

Runs the core pipeline (ingest -> static -> normalize -> graph -> translate)
with COGANT_USE_RUST=0 and COGANT_USE_RUST=1 on three fixtures and reports
wall-clock timings.

Thin-orchestrator: all pipeline logic lives in cogant.api.orchestration;
this script only drives timing and reporting.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Ensure package import works when run from repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "py"))

from cogant.api import orchestration  # noqa: E402
from cogant.api.bundle import Bundle  # noqa: E402
from cogant.rust_backend import RUST_AVAILABLE, rust_version  # noqa: E402

FIXTURES = [
    ("calculator", "examples/control_positive/calculator"),
    ("flask_app", "examples/real_world/flask_app"),
    ("requests_lib", "examples/real_world/requests_lib"),
]

SAMPLES = 3


def run_once(repo: str) -> tuple[float, int, int]:
    """Run the core pipeline once; return (elapsed_ms, nodes, edges)."""
    t0 = time.perf_counter()
    bundle = Bundle(target=repo)
    orchestration.run_ingest(repo, bundle)
    orchestration.run_static(bundle)
    orchestration.run_normalize(bundle)
    orchestration.run_graph(bundle, repo)
    orchestration.run_translate(bundle)
    elapsed = (time.perf_counter() - t0) * 1000.0

    pg = bundle.artifacts.get("_program_graph")
    nodes = len(pg.nodes) if pg is not None and hasattr(pg, "nodes") else 0
    edges = len(pg.edges) if pg is not None and hasattr(pg, "edges") else 0
    return elapsed, nodes, edges


def bench(label: str) -> dict[str, dict[str, float | int]]:
    """Run the benchmark on all fixtures with the current env."""
    print(f"--- {label} ---", flush=True)
    results: dict[str, dict[str, float | int]] = {}

    # Warm-up pass on the smallest fixture (primes imports + caches).
    run_once(FIXTURES[0][1])

    for name, repo in FIXTURES:
        samples = []
        nodes = edges = 0
        for _ in range(SAMPLES):
            elapsed, nodes, edges = run_once(repo)
            samples.append(elapsed)
        best = min(samples)
        mean = sum(samples) / len(samples)
        print(
            f"{name:<14} best={best:7.1f}ms mean={mean:7.1f}ms "
            f"nodes={nodes:4d} edges={edges:4d} samples={[round(s, 1) for s in samples]}",
            flush=True,
        )
        results[name] = {
            "best_ms": best,
            "mean_ms": mean,
            "nodes": nodes,
            "edges": edges,
            "samples_ms": samples,
        }
    return results


def main() -> int:
    print(f"RUST_AVAILABLE: {RUST_AVAILABLE}  version: {rust_version()}")

    os.environ["COGANT_USE_RUST"] = "0"
    py_results = bench("Python backend (COGANT_USE_RUST=0)")

    os.environ["COGANT_USE_RUST"] = "1"
    rust_results = bench("Rust backend (COGANT_USE_RUST=1)")

    print()
    print("| Fixture      | Python best (ms) | Rust best (ms) | Speedup |")
    print("|--------------|------------------|----------------|---------|")
    for name, _ in FIXTURES:
        p = py_results[name]["best_ms"]
        r = rust_results[name]["best_ms"]
        speedup = p / r if r else float("nan")
        print(f"| {name:<12} | {p:16.1f} | {r:14.1f} | {speedup:6.2f}x |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
