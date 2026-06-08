## COGANT Benchmarks

Performance targets, measurement methodology, and reference numbers for the COGANT translation pipeline. COGANT translates software repositories into **Generalized Notation Notation** (GNN) — the Active Inference Institute's structured state-space and process-model notation, not graph neural networks.

This document complements the lower-level benchmarks in `benchmarks/` and serves as the public contract for performance expectations.

### Scope

COGANT benchmarks cover three dimensions:

1. **Stage latency** — wall-clock time for each of the nine pipeline stages (ingest, static, normalize, graph, translate, statespace, process, export, validate).
2. **Throughput** — files per second, nodes per second, and edges per second on representative fixtures.
3. **End-to-end round-trip** — the full `RoundtripOrchestrator.run()` path against the three control-positive fixture repos.

Memory consumption and output-size regressions are tracked but are secondary targets.

### Reference fixtures

The canonical fixtures live in `examples/control_positive/` and are used for both golden tests and benchmarks.

| Fixture | Files | LOC | Functions | Classes | Purpose |
|---|---:|---:|---:|---:|---|
| `calculator` | 6 | ~250 | 18 | 3 | Minimal Python service with tests |
| `flask_mini` | 8 | ~400 | 22 | 2 | Small web service with routes and handlers |
| `event_pipeline` | 10 | ~600 | 35 | 5 | Event-driven worker with retries and policies |

All three achieve **100% GNN validation score** and emit **111 files** per run under the current orchestrator.

### Stage-level targets

Targets measured on a 2024 M-class laptop, warm cache, single process, no parallelism. Each target covers the per-stage cost during a full round-trip on `event_pipeline` unless noted.

| Stage | Target | Observed (v0.1.0) | Notes |
|---|---:|---:|---|
| ingest | < 50 ms | ~20 ms | File discovery + manifest load |
| static (Python AST) | < 200 ms / 10 files | ~90 ms | Per-file AST + dataflow pass |
| normalize | < 50 ms | ~15 ms | Canonical ID assignment |
| graph | < 100 ms | ~45 ms | Typed program graph construction |
| translate | < 150 ms | ~70 ms | 12 rule engine pass |
| statespace | < 100 ms | ~55 ms | Hidden state + observation + action compile |
| process | < 80 ms | ~40 ms | Stage extraction + policy inference |
| export | < 500 ms | ~280 ms | GNN markdown, JSON, GraphML, Parquet, HTML |
| validate | < 100 ms | ~60 ms | 18-section contract check |
| **Total (round-trip)** | **< 1.5 s** | **~900 ms** | Excluding simulate |
| simulate (20 steps) | < 500 ms | ~220 ms | VFE + EFE per step, 3-step horizon |

Large-repo targets (as COGANT gains Rust acceleration):

| Repo size | Target | Notes |
|---|---:|---|
| 10K files, 500K LOC | < 30 s | End-to-end minus simulate |
| 50K files, 2.5M LOC | < 3 min | Parallel static pass required |
| Monorepo, polyglot | < 10 min | Per-language worker pool |

### Throughput targets

| Operation | Target | Notes |
|---|---:|---|
| File discovery | > 5 000 files / s | Glob + filter |
| Python AST parse | > 50 files / s | Cold, no cache |
| Graph node insert | > 100 000 nodes / s | In-memory only |
| Edge insert | > 200 000 edges / s | Assumes node IDs exist |
| Translation rule eval | > 10 000 fragments / s | Per-rule cost depends on match breadth |
| GNN markdown emit | > 5 MB / s | String concat + formatting |
| Parquet export | > 50 000 rows / s | Via pyarrow |

### Memory targets

| Artifact | Target per 10 K nodes | Notes |
|---|---:|---|
| ProgramGraph (in-memory) | < 50 MB | Python dataclasses |
| StateSpaceModel | < 10 MB | Derived from graph |
| Exported GNN package | < 5 MB | On disk, JSON + Markdown |

Memory regressions greater than 10% between releases must ship with a written justification in the PR description.

### Running benchmarks

Fast subset (sub-second, runs in CI):

```bash
PYTHONPATH=py python -m pytest benchmarks/ -q
```

Full benchmark suite with statistical rigor:

```bash
PYTHONPATH=py python -m pytest benchmarks/ --benchmark-only \
    --benchmark-columns=mean,median,stddev,min,max,rounds
```

Compare against a saved baseline:

```bash
pytest benchmarks/ --benchmark-compare=0001 --benchmark-compare-fail=mean:10%
```

End-to-end round-trip timing on all three control-positive fixtures:

```bash
for repo in calculator flask_mini event_pipeline; do
    time PYTHONPATH=py python examples/orchestrate_roundtrip.py \
        examples/control_positive/$repo \
        --output-dir output/bench_$repo
done
```

### Measurement methodology

- **Wall clock, not CPU time.** COGANT is I/O-sensitive during ingest and export.
- **Warm cache.** Run the target once before measuring to fill the filesystem cache.
- **Median of 11 runs.** Discard the first and report the median of the remaining 10.
- **Single process, no parallelism** for baseline numbers. Parallel numbers are reported separately.
- **Absolute paths only.** Relative paths introduce CWD-dependent discovery costs.
- **Deterministic configs.** Benchmarks must pin the same config hash across runs.

### Regression policy

A PR introduces a regression if, on the reference fixture set, it causes:

- Any single stage to exceed its target by more than 20%.
- End-to-end round-trip on `event_pipeline` to exceed 1.5 s by more than 20% (1.8 s).
- Memory on any fixture to exceed the target by more than 10%.

Regressions require either (a) an accompanying optimization, (b) a raised target with stakeholder sign-off in the PR, or (c) an opt-in flag to preserve the previous behavior.

### Optimization priorities

1. **Profile first.** Use `cProfile` + `snakeviz` or `py-spy record` before changing code.
2. **Cache stable IDs.** Identity resolution is the single largest cost in `normalize`.
3. **Stream exports.** Avoid materializing the full graph twice when emitting GraphML + Parquet.
4. **Push hot paths to Rust.** Any operation exceeding 100 ms per call on the reference fixtures is a candidate for the `cogant-*` Rust crates via PyO3.
5. **Parallelize the static pass.** Parser calls are embarrassingly parallel; the pipeline is not yet parallel.

### Related documents

- [benchmarks/README.md](https://github.com/docxology/cogant/blob/main/cogant/benchmarks/README.md) — low-level benchmark layout and running guide
- [ARCHITECTURE.md](../architecture/README.md) — layered architecture and stage boundaries
- [Changelog](changelog.md#changelog) — performance notes per release
- [AGENTS.md](./AGENTS.md) — module maintenance rules and cross-linking expectations for roadmap docs

---
