## Concurrency & Parallelism

### Stage parallelization

The default `PipelineRunner` executes **10** runner stages (see `cogant/evaluation/METRICS.yaml` `pipeline.runner_stages` and [`docs/reference/pipeline_stages.md`](../reference/pipeline_stages.md)). Typical parallelization patterns:

- **Static / graph**: per-file work can be parallelized where the implementation fans out over files before merging into a single program graph.
- **Translate**: rule matching may process disjoint graph regions concurrently when the engine batches work safely.
- **Export**: writing multiple artifact formats can overlap I/O when the builder supports it.

Exact parallelism is implementation-dependent; treat this page as architectural intent, not a guarantee for every release.

### Thread safety

- Rust crates are `Send + Sync`
- Python GIL released in PyO3 functions
- No mutable sharing across threads
- Lock-free data structures where possible
