# Experimental setup {#sec:06-experimental-setup}

**Terminology.** **GNN** here and in @sec:06-01-environment-api-and-config / @sec:06-04-tests-mutation-and-benchmarks is **Generalized Notation Notation**, not graph neural networks; see @sec:01-introduction.

## Environment, API, exports, parser, and IR

Install paths, Session and Pipeline examples, YAML configuration, CLI usage, export targets, Python `ast` front-end coverage, and the staged IR progression (@tbl:progressive-ir-stages in @sec:06-02-exports-parser-and-ir-stages) are detailed in @sec:06-01-environment-api-and-config and @sec:06-02-exports-parser-and-ir-stages.

## Performance characteristics

The architecture targets the following benchmarks on a 4-core machine, as specified in `../cogant/docs/architecture/README.md`:

| Repository size | Target wall-clock time | Memory budget |
|----------------|----------------------|---------------|
| 10K functions | < 30 s | < 500 MB |
| 100K functions | < 5 min | < 2 GB |
| 1M functions | < 1 hr | < 2 GB (streaming) |

These are architecture targets, not benchmark claims from this manuscript. They assume the Python orchestration layer with Rust acceleration on critical paths (graph construction, rule matching, and Generalized Notation Notation section/tensor packing in `cogant-gnn`). In the current v0.5.x release, Rust acceleration is partially wired — `cogant._rust` exposes a PyO3 `connected_components` FFI for graph construction behind the `COGANT_USE_RUST` feature flag — and a pure-Python fallback handles the remaining code paths.

Current `PipelineRunner` behavior is stage-sequential with per-stage error capture and continuation. It does not currently expose built-in incremental checkpoint/resume in `cogant.api.pipeline`; treat checkpointing as a potential outer-orchestration feature rather than a guaranteed package-level runtime behavior.

## Measured runs on packaged fixtures

The following narrative matches @sec:06-03-performance-and-fixture-metrics. Measurements come from `../cogant/evaluation/figures/generate_figures.py`, which uses `cogant.api.orchestration` (same in-memory `ProgramGraph` and mapping counts as the benchmark harness) on every packaged fixture (three control-positive under `../cogant/examples/control_positive/`, three real-world under `../cogant/examples/real_world/`). Optional Rust acceleration is off for reproducibility unless you set `COGANT_USE_RUST=1`. All numbers for @tbl:repo-pipeline-metrics through @tbl:output-artifacts-per-run are written to `../cogant/evaluation/figures/metrics.json`. Those four captioned tables are in that section. (A separate `orchestrate_roundtrip.py` demo can emit a larger serialized graph and extra diagrams; the manuscript does not use that path for @tbl:repo-pipeline-metrics–@tbl:output-artifacts-per-run.)

## Test matrix, mutation testing, and benchmarks

The v{{VERSION}} Python implementation ships **{{TEST_COUNT}}** passing tests with **{{TEST_COUNT_SKIPPED}}** skips, **{{TEST_COUNT_XFAILED}}** expected `xfail`, and **{{TEST_COUNT_XPASSED}}** `xpass`; suite wall-clock **{{SUITE_RUNTIME_S}}** s; **{{COVERAGE_PCT}}%** line coverage on the canonical `uv run pytest tests/ --cov=cogant` run (**{{METRICS_GENERATED_AT}}**); **{{MYPY_STRICT_ERRORS}}** `mypy --strict` errors on `py/cogant/`. The interpreter matrix, per-module coverage table, hand-curated mutation summary, and benchmark harness results are in @sec:06-04-tests-mutation-and-benchmarks as @tbl:python-interpreter-matrix, @tbl:coverage-stmt-modules, @tbl:mutation-hand-curated, and @tbl:benchmark-suite-results. The algorithmic core load-bearing for the ε-isomorphism and forward--reverse guarantees in **Appendix C** ([`S03_appendix_galois_sketch.md`](S03_appendix_galois_sketch.md); [`../cogant/docs/evaluation/ISOMORPHISM_THEOREM.md`](../cogant/docs/evaluation/ISOMORPHISM_THEOREM.md)) is summarized in @tbl:coverage-stmt-modules; see @sec:06-04-tests-mutation-and-benchmarks for the full narrative on mutation testing and benchmarks. Automated `mutmut` is wired in [`../cogant/pyproject.toml`](../cogant/pyproject.toml) (`[tool.mutmut]`) to `translate/engine.py` and `markov/blanket.py` only; the hand-picked report in `../cogant/docs/evaluation/MUTATION_REPORT.md` also covers `gnn/matrices.py`, `statespace/compiler.py`, and `static/dataflow.py`.

The benchmark harness times the pipeline through `statespace` only, so its wall-clock medians are much smaller than the end-to-end runs in @tbl:repo-pipeline-metrics (which add `process`, `export`, and `validate` via `generate_figures.py`). For pure translation, every shipped fixture in the `suite_20260423` snapshot runs in under 100 ms median; see @tbl:benchmark-suite-results. Stage medians for that run are in `suite_20260423.md`. Tensor shapes in the benchmark sidecar use `GNNMatrices` on the post-`statespace` bundle; for `flask_app` they read $A \in \mathbb{R}^{22 \times 13}$, $B \in \mathbb{R}^{13 \times 13 \times 31}$, $C \in \mathbb{R}^{22}$, $D \in \mathbb{R}^{13}$, while @tbl:state-space-compilation counts observations and state variables from the **exported** `gnn_package/` after the full pipeline (on the current snapshot, 22 and 14 respectively for that fixture).

## What to record

For reproducible experiments, record: COGANT version or commit hash, interpreter version, list of stages executed, configuration file contents (redacted), input repository commit hash, and random seeds for any learned components **outside** COGANT that consume the exports.

## See also (MkDocs)

Full evaluation index: [`../cogant/docs/evaluation/README.md`](../cogant/docs/evaluation/README.md). FAQ: [`../cogant/docs/faq.md`](../cogant/docs/faq.md).
