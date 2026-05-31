# Test matrix, mutation testing, and benchmark suite {#sec:06-04-tests-mutation-and-benchmarks}

## Test matrix and coverage

The v{{VERSION}} Python implementation ships a test suite that, on the canonical `uv run pytest tests/ --cov=py/cogant` run (the gate in [`../cogant/pyproject.toml`](../cogant/pyproject.toml) measures the `py/cogant/` source tree for the import package `cogant`), reports **{{TEST_COUNT_PASSING}} passing**, **{{TEST_COUNT_FAILING}} failing**, and **{{TEST_COUNT_SKIPPED}} skipped** tests, plus **{{TEST_COUNT_XFAILED}} expected `xfail`** and **{{TEST_COUNT_XPASSED}} `xpass`** case. Any non-zero failing count is a release-blocking evidence gap, not a hidden denominator; the pass/skip/coverage figures below must be read together with that failure count. End-to-end runtime is on the order of several minutes on a 2024-class Apple-silicon workstation (**{{SUITE_RUNTIME_S}}** s in the canonical run); the overall line coverage of the instrumented package is **{{COVERAGE_PCT}}%** on that run, measured across **{{PYTHON_LOC}}** executable lines in **{{PYTHON_SOURCE_FILES}}** source files (see `METRICS.yaml`, generated **{{METRICS_GENERATED_AT}}**). `mypy --strict` on `py/cogant/` reports **{{MYPY_STRICT_ERRORS}}** remaining
errors. As of 2026-05-19 this count is zero; the pydantic v2 mypy plugin is
enabled in `cogant/pyproject.toml:[tool.mypy].plugins = ["pydantic.mypy"]`
and PyYAML is in the `ignore_missing_imports` overrides, which together
resolve the residual stub-resolution diagnostics that previously generated
a 30-error count. The figure is still *errors among reported
diagnostics*, not a completeness certificate; `--strict` does not enable
`--disallow-any-unimported`, so consumers using unstubbed third-party
packages remain a separate audit class documented in the scope-of-record
[`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md).

| Python version | `pyproject.toml` classifier | Status |
|---|---|---|
| 3.11 | `Programming Language :: Python :: 3.11` | supported (minimum version, `requires-python = ">=3.11"`) |
| 3.12 | `Programming Language :: Python :: 3.12` | supported (canonical CI interpreter; benchmark runs use {{BENCHMARK_PYTHON_VERSION}}) |
| 3.13 | `Programming Language :: Python :: 3.13` | supported |

: Python interpreter matrix. {#tbl:python-interpreter-matrix}

All three interpreters are listed in the `classifiers` block of [`../cogant/pyproject.toml`](../cogant/pyproject.toml). The declared minimum is Python 3.11 so that the pattern-matching front end in `cogant.static.parser.PythonASTParser` can use `match`/`case` statements without a compatibility shim, and the benchmark suite recorded in `benchmarks/results/{{BENCHMARK_SUITE_FILE}}` was executed on CPython {{BENCHMARK_PYTHON_VERSION}} under {{BENCHMARK_OS}}.

Module-level coverage is concentrated in the layers that the **{{SHIPPED_FIXTURE_COUNT}}** packaged fixtures exercise end-to-end. @tbl:coverage-stmt-modules records statement coverage (`coverage.py` **Stmts** / **Cover**) for the algorithmic core (translation, state-space compilation, Markov blanket extraction, GNN matrix construction, validation, simulation helpers) --- the modules whose correctness is load-bearing for the claims in this manuscript. Figures match the `uv run pytest tests/ --cov=py/cogant` run that produced the {{TEST_COUNT}}/{{TEST_COUNT_SKIPPED}} pass/skip summary in `METRICS.yaml` (**{{METRICS_GENERATED_AT}}**).

| Module | Stmts | Cover |
|---|---:|---:|
| `cogant.translate.engine` | 250 | 96% |
| `cogant.translate.rules.structural` | 190 | 99% |
| `cogant.translate.rules.semantic` | 255 | 93% |
| `cogant.translate.rules.behavioral` | 108 | 100% |
| `cogant.translate.rules.control` | 79 | 100% |
| `cogant.translate.rules.resilience` | 164 | 93% |
| `cogant.translate.confidence` | 98 | 100% |
| `cogant.statespace.compiler` | 471 | 99% |
| `cogant.statespace.variables` | 263 | 99% |
| `cogant.statespace.temporal` | 217 | 100% |
| `cogant.markov.blanket` | 166 | 100% |
| `cogant.gnn.matrices` | 359 | 99% |
| `cogant.static.calls` | 151 | 89% |
| `cogant.static.dataflow` | 297 | 95% |
| `cogant.static.parser` | 236 | 89% |
| `cogant.simulate.free_energy` | 165 | 100% |
| `cogant.simulate.runner` | 252 | 99% |
| `cogant.simulate.distributions` | 118 | 100% |
| `cogant.scoring.drift` | 222 | 100% |
| `cogant.scoring.metrics` | 142 | 99% |
| `cogant.validate.integrity` | 140 | 96% |
| `cogant.validate.schema_check` | 103 | 96% |
| `cogant.validate.provenance_check` | 73 | 100% |
| `cogant.viz.png.mermaid` | 502 | 78% |
| `cogant.viz.png.program_graph` | 283 | 89% |
| `cogant.viz.png.state_space` | 215 | 97% |
| `cogant.viz.matrix_view` | 324 | 92% |
| `cogant.viz.network_view` | 227 | 91% |
| `cogant.viz.flow` | 251 | 99% |

: Statement coverage of load-bearing modules (canonical v{{VERSION}} run, {{METRICS_GENERATED_AT}}). {#tbl:coverage-stmt-modules}

The aggregate **{{COVERAGE_PCT}}%** in `METRICS.yaml` is measured with `[tool.coverage.run] source = ["py/cogant"]` and **omits** `cogant/static/treesitter_parser.py` (see [`../cogant/pyproject.toml`](../cogant/pyproject.toml)). The `viz/` package is instrumented and covered in v{{VERSION}} by a dedicated viz test suite because the rendered program graphs, matrix panels, Markov blanket views, and run overviews are part of the human interpretability surface rather than decorative output. Lower rows in @tbl:coverage-stmt-modules (for example `static.calls` and `static.parser`) highlight residual branch gaps, not omitted packages. See `../cogant/CHANGELOG.md` for release-cycle deltas.

## Mutation testing

Automated `mutmut` 3.5.0 is wired in [`../cogant/pyproject.toml`](../cogant/pyproject.toml) (`[tool.mutmut]`) to only `py/cogant/translate/engine.py` and `py/cogant/markov/blanket.py`; the broader hand-picked experiment below also targets `gnn/matrices.py`, `statespace/compiler.py`, and `static/dataflow.py`. The canonical `mutmut` runner was additionally evaluated on `matrices.py` but rejected: on COGANT's test layout `mutmut` reported every one of the 403 auto-generated mutants on that file as "no tests" because its v3 trampoline requires tests to import the mutated module through the `mutants/<path>` shadow tree, and the project's `pytest` configuration does not. Rather than ship a "no tests" score, the mutation analysis in `../cogant/docs/evaluation/MUTATION_REPORT.md` is based on a **hand-picked set of fifteen semantic mutations** across those modules; each mutation was applied, the relevant `pytest` subset was rerun, and the mutation was reverted immediately. This documents exactly *which* invariants the tests enforce.

**Statistical caveat.** The "66.7% mutation score" reported below is
arithmetically correct on the 15-mutant sample but is **not a
statistically meaningful mutation score** in the sense reported by an
unbiased mutmut run over hundreds of auto-generated mutants. A
15-mutant hand-picked sample is a *qualitative diagnostic* — a way
to enumerate which invariants the tests verify and which do not —
not an estimator of the package-wide mutation-survival rate. Readers
should treat the table as "fifteen targeted what-if probes,
ten killed, five surviving with documented follow-ups" rather than as
a coverage statistic. Fixing the mutmut v3 trampoline path so a full
auto-generated run on `matrices.py` reports a real score is tracked
as future work; until then the per-row 33%/50%/100%/etc. cells are
informative only as the killed/total ratio on the sample, not as
estimates over the full mutation space.

| Module | Mutants tested | Killed | Survived | Mutation score |
|---|---:|---:|---:|---:|
| `gnn/matrices.py` | 5 | 3 | 2 | 60% |
| `translate/engine.py` | 3 | 1 | 2 | 33% |
| `markov/blanket.py` | 2 | 1 | 1 | 50% |
| `statespace/compiler.py` | 2 | 1 | 1 | 50% |
| `static/dataflow.py` | 3 | 3 | 0 | 100% |
| **Total** | **15** | **10** | **5** | **66.7%** |

: Hand-curated mutation results on COGANT algorithmic core (mutation testing subsection). {#tbl:mutation-hand-curated}

The five surviving mutants are documented individually in `../cogant/docs/evaluation/MUTATION_REPORT.md` §"Surviving mutants --- action required" (aversive preference path in `compute_C`, sensory↔active boundary role swap in `markov/blanket.py`, `>=`→`>` boundary flip in `_map_confidence`, `CONFIGURATION` neighbour bias in `compute_D`, and the single-pass fixpoint iteration cap). Three of the five were closed by hardening tests in the same commit: `test_C_aversive_preference_produces_negative_log_pref` kills the aversive-preference survivor, `test_boundary_with_only_outgoing_edge_is_active` / `test_boundary_with_only_incoming_edge_is_sensory` kill the Markov-blanket swap, and `test_map_confidence_exact_boundary_values` kills the `>=`→`>` family. The remaining two survivors (CONFIGURATION-bias and single-pass fixpoint) are documented follow-ups that require non-trivial fixture extensions. The measured score on the hand-picked set is therefore **10 killed / 15 total = 66.7%** before hardening, and the documented target after the follow-ups is 80% or better.

The modules with the strongest mutation signal are `static/dataflow.py` (3 of 3 killed --- every edge-kind string mutation is caught by the dataflow-tuple-assertion tests) and the row/column normalisation paths in `gnn/matrices.py` (4 of 5 killed --- every arithmetic mutation to `_normalize_row`, `_DEFAULT_DIRECT_MASS`, the `compute_C` sign-flip, the `compute_B` axis swap, and the `compute_A` fallback branch is killed by the `A_rows_sum_to_one`, `B_columns_sum_to_one_per_action`, and `A_concentrates_mass_on_direct_reads` tests). The modules that drag the overall score down are those whose tests assert structural invariants (disjointness, normalisation, shape) but do not pin down the *direction* or *magnitude* of individual entries.

## Benchmark suite (shipped)

A reproducible benchmark harness lives at [`../cogant/benchmarks/bench_suite.py`](../cogant/benchmarks/bench_suite.py) and writes its canonical results to [`../cogant/benchmarks/results/`](../cogant/benchmarks/results/). The snapshot below is from `{{BENCHMARK_SUITE_FILE}}` (three iterations per fixture, CPython {{BENCHMARK_PYTHON_VERSION}} / {{BENCHMARK_OS}}) and should be regenerated after performance work.

| Fixture | Wall-clock median (ms) | Wall-clock p95 (ms) | Nodes | Edges | Mappings | Peak memory (MB) |
|---|---:|---:|---:|---:|---:|---:|
| `calculator` | 35 | 35 | 12 | 25 | 11 | 0.2 |
| `event_pipeline` | 41 | 43 | 23 | 36 | 21 | 0.2 |
| `flask_mini` | 38 | 38 | 26 | 40 | 25 | 0.1 |
| `flask_app` | 59 | 62 | 98 | 154 | 72 | 0.4 |
| `requests_lib` | 54 | 58 | 98 | 152 | 63 | 0.1 |
| `json_stdlib` | 47 | 49 | 29 | 34 | 19 | 0.0 |

: Benchmark suite results (`{{BENCHMARK_SUITE_FILE}}`, three iterations per fixture, CPython {{BENCHMARK_PYTHON_VERSION}}). {#tbl:benchmark-suite-results}

Node and mapping columns use the same fixture definitions as @tbl:repo-pipeline-metrics. The edge columns are pinned to the benchmark snapshot named in the caption, while the refreshed public API metric table can include newer import-edge extraction. The `mappings` count is from the same post-`statespace` in-memory `semantic_mappings` dict that `../cogant/evaluation/figures/metrics.json` uses (`pipeline_api_metrics` samples immediately after `run_statespace`); conflict resolution in `TranslationEngine` applies **sorted** iteration over colliding mapping pairs so this count is stable across `bench_suite` and `generate_figures` runs.

The benchmark harness times the pipeline up through `statespace` (no `process` / `export` / `validate`), so its wall-clock medians are much smaller than the end-to-end times in @tbl:repo-pipeline-metrics, which add process model extraction, GNN package build, and validation. For pure translation, every shipped fixture in this run finishes in under 100 ms median wall time; the stage breakdown in `suite_20260423.md` shows `ingest` and `graph` as the main contributors on the larger fixtures.

The manuscript therefore keeps two timing views separate: @tbl:benchmark-suite-results is a repeated harness measurement of the pre-export pipeline, while @fig:cogant-eval-pipeline-latency is a single-run provenance figure for the public API path that also builds and validates the GNN package.

Approximate stage breakdown from the same file: per-fixture `ingest` is on the order of 30--35 ms; `graph` reaches roughly 7--13 ms on the larger fixtures. The benchmark file records GNN tensor shapes from `GNNMatrices` on the post-`statespace` bundle; for example `flask_app` shows $A \in \mathbb{R}^{22 \times 13}$, $B \in \mathbb{R}^{13 \times 13 \times 31}$, $C \in \mathbb{R}^{22}$, $D \in \mathbb{R}^{13}$, which line up with the Markov structure implied by the observation and hidden-state rows in the summary section of `suite_20260423.md` (exported `gnn_package/` modalities in @tbl:state-space-compilation can still differ from the post-`statespace` GNN read when `run_process` refines the bundle).
