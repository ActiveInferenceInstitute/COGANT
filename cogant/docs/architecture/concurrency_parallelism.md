## Concurrency & Parallelism

### Stage Parallelization

The current 8-stage pipeline (`ingest → parse → graph → translate → statespace → markov → gnn → reverse`; see `cogant/evaluation/METRICS.yaml`) parallelizes as follows:

- **Stage 2 (Parse)**: Parallel per-file (independent parsers; absorbs the legacy `static` and `normalize` stages)
- **Stage 3 (Graph)**: Parallel per-file + reduce on the merge step
- **Stage 4 (Translate)**: Parallel over the 19-rule fixpoint set
- **Stage 7 (GNN)**: Parallel per export format (JSON / Markdown / matrices)
- **Stage 8 (Reverse)**: Parallel per `PackagePlan` module during synthesis

### Thread Safety

- Rust crates are `Send + Sync`
- Python GIL released in PyO3 functions
- No mutable sharing across threads
- Lock-free data structures where possible

