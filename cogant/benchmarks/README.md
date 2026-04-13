# Benchmarks — Performance Testing

Performance benchmarks for COGANT critical path and components.

## Structure

```
benchmarks/
├── AGENTS.md            # Lane ownership and benchmark strategy
├── README.md            # This file
└── bench_ingest.py      # File discovery and ingestion
```

Only `bench_ingest.py` is implemented so far. The other stages (parse, graph, translate, export) have performance targets listed below and are planned but not yet wired. Add each missing `bench_*.py` as the corresponding pipeline stage stabilizes — see the targets table for the expected budget.

## Running benchmarks

```bash
python benchmarks/bench_ingest.py            # Direct execution
pytest benchmarks/ --benchmark-only          # Once pytest-benchmark is added to dev deps
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
