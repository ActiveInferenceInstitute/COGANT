## Concurrency & Parallelism

### Stage Parallelization

- **Stage 2 (Static)**: Parallel per-file (independent parsers)
- **Stage 3 (Normalize)**: Parallel per-file + reduce
- **Stage 5 (Dynamic)**: Parallel per-file (independent trace loading)
- **Stage 6 (Translate)**: Parallel over rule set
- **Stage 9 (Export)**: Parallel per format

### Thread Safety

- Rust crates are `Send + Sync`
- Python GIL released in PyO3 functions
- No mutable sharing across threads
- Lock-free data structures where possible

