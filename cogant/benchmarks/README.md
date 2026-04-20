# Benchmarks — Performance Testing

Performance benchmarks for COGANT critical path and components.

## Structure

```
benchmarks/
├── AGENTS.md                   # Lane ownership and benchmark strategy
├── README.md                   # This file
├── bench_ingest.py             # File discovery and ingestion
├── bench_graph_build.py        # ProgramGraph construction throughput
├── bench_suite.py              # End-to-end pipeline benchmark suite
├── bench_perf_regression.py    # Regression guard against `perf_baseline.json`
├── rust_vs_python.py           # Rust FFI vs pure-Python backend comparison
├── perf_baseline.json          # Recorded performance baseline
└── results/                    # Run artefacts (gitignored)
```

Stage coverage is partial — parse, translate, and export benchmarks are not yet wired; add each
missing `bench_*.py` as the corresponding pipeline stage stabilizes. See the targets table below
for the expected budget per stage.

## Running benchmarks

```bash
uv run python benchmarks/bench_ingest.py           # direct execution
uv run python benchmarks/bench_suite.py            # end-to-end suite
uv run python benchmarks/bench_perf_regression.py  # regression guard vs perf_baseline.json
uv run pytest benchmarks/ --benchmark-only         # once pytest-benchmark is a dev dep
```

## Performance targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Ingest (10K files) | < 1s | File discovery and filtering |
| Parse Python (10K LOC) | < 100ms | AST extraction |
| Parse Rust (10K LOC) | < 500ms | Tree-sitter parsing |
| Graph build (100K nodes) | < 1s | In-memory graph construction |
| Queries (reachability) | < 50ms | BFS from single node |
| Translate (10K rules) | < 1s | Rule evaluation |
| Export JSON (100K nodes) | < 2s | Serialization |
| Export Parquet (100K nodes) | < 3s | Arrow serialization |

## Benchmark strategy

- Measure wall-clock time on CI hardware
- Use pytest-benchmark for statistical rigor
- Track regression across versions
- Profile critical paths monthly

## Optimization guidelines

- Don't optimize prematurely (measure first)
- Prefer Rust for hot paths (>100ms per operation)
- Parallelize graph algorithms (rayon)
- Profile with cProfile and flamegraph
