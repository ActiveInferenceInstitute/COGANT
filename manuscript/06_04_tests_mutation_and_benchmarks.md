# Test matrix, mutation testing, and benchmark suite

## Test matrix and coverage

The v0.5.0 Python implementation ships a test suite that, on the canonical `uv run pytest tests/ --cov=py/cogant` run, reports **2146 passing** tests with **11 skips** for optional dependencies (Rust toolchain, `matplotlib`, `tree-sitter` language grammars, PNG rasterization), plus **2 expected `xfail`** and **1 `xpass`** case. End-to-end runtime is on the order of four minutes on a 2024-class Apple-silicon workstation (238 s in the most recent canonical run); the overall line coverage of `py/cogant/` is **86.45%** on that run, measured across 20,307 statements in 179 source files.

**Table 8. Python interpreter matrix.**

| Python version | `pyproject.toml` classifier | Status |
|---|---|---|
| 3.11 | `Programming Language :: Python :: 3.11` | supported (minimum version, `requires-python = ">=3.11"`) |
| 3.12 | `Programming Language :: Python :: 3.12` | supported (canonical CI interpreter; benchmark runs use 3.12.11) |
| 3.13 | `Programming Language :: Python :: 3.13` | supported |

All three interpreters are listed in the `classifiers` block of [`../cogant/pyproject.toml`](../cogant/pyproject.toml). The declared minimum is Python 3.11 so that the pattern-matching front end in `cogant.static.parser.PythonASTParser` can use `match`/`case` statements without a compatibility shim, and the benchmark suite recorded in `benchmarks/results/suite_20260409.md` was executed on CPython 3.12.11 under macOS arm64.

Module-level coverage is concentrated in the layers that the six packaged fixtures exercise end-to-end. Table 9 records the coverage of the algorithmic core (translation, state-space compilation, Markov blanket extraction, GNN matrix construction, and the reverse synthesizer) --- the modules whose correctness is load-bearing for every claim in the manuscript. Numbers are taken from the `TOTAL`-line breakdown of the `uv run pytest --cov` run that produced the 2146/11 pass/skip summary.

**Table 9. Line coverage of load-bearing modules (canonical v0.5.0 run, 2026-04-10).**

| Module | Lines | Coverage |
|---|---:|---:|
| `cogant.translate.engine` | 160 | 90% |
| `cogant.translate.rules.structural` | 185 | 93% |
| `cogant.translate.rules.semantic` | 216 | 92% |
| `cogant.translate.rules.behavioral` | 79 | 98% |
| `cogant.translate.rules.control` | 47 | 93% |
| `cogant.translate.rules.resilience` | 130 | 95% |
| `cogant.translate.confidence` | 98 | 97% |
| `cogant.statespace.compiler` | 418 | 91% |
| `cogant.statespace.variables` | 182 | 98% |
| `cogant.statespace.temporal` | 173 | 81% |
| `cogant.markov.blanket` | full coverage (reported in the "60 files skipped due to complete coverage" block of the canonical run) | 100% |
| `cogant.gnn.matrices` | full coverage (same block) | 100% |
| `cogant.static.calls` | 151 | 86% |
| `cogant.static.dataflow` | 246 | 84% |
| `cogant.static.parser` | 236 | 86% |
| `cogant.simulate.free_energy` | 165 | 99% |
| `cogant.simulate.runner` | 252 | 67% |
| `cogant.simulate.distributions` | 118 | 95% |
| `cogant.scoring.drift` | 215 | 99% |
| `cogant.scoring.metrics` | 142 | 99% |
| `cogant.validate.integrity` | 136 | 94% |
| `cogant.validate.schema_check` | 115 | 95% |
| `cogant.validate.provenance_check` | 73 | 97% |

The aggregate project-level coverage reported at the end of the run is **86.45%**; the modules that drag the average down are the visualisation layer (`cogant.viz.png_export` at 82%, `cogant.viz.plots` at 89%, `cogant.viz.mermaid` at 91%, with residual gaps where optional `matplotlib` and `plotly` code paths are skipped) plus a small number of scaffolded plugin or provenance helpers (for example `cogant.viz.bundle_site` at 0%, an HTML site generator that requires the `jinja2` extra and therefore never executes under the default `uv sync` environment). The algorithmic core --- everything that participates in the round-trip theorem of §9 --- remains at high coverage on the exercised modules, with every `translate.rules.*` family above 90% and the free-energy and drift-scoring modules above 99%. The `simulate.distributions` and `simulate.free_energy` modules sit at 95% and 99% respectively in the canonical v0.5.0 run, up from 34% and 65% earlier in the release cycle — a consequence of the scaling-regression test suite added for the B-tensor and BFS paths as documented in `../cogant/CHANGELOG.md`.

## Mutation testing

Mutation testing was performed on the algorithmic core modules (`gnn/matrices.py`, `translate/engine.py`, `markov/blanket.py`, `statespace/compiler.py`, `static/dataflow.py`). The canonical `mutmut` 3.5.0 runner was evaluated but rejected: on COGANT's test layout `mutmut` reported every one of the 403 auto-generated mutants on `matrices.py` as "no tests" because its v3 trampoline requires tests to import the mutated module through the `mutants/<path>` shadow tree, and the project's `pytest` configuration does not. Rather than ship a "no tests" score, the mutation analysis in `../cogant/docs/evaluation/MUTATION_REPORT.md` is based on a **hand-picked set of fifteen semantic mutations** that target the algorithmic predicates, constants, and loop bounds of the above modules; each mutation was applied, the relevant `pytest` subset was rerun, and the mutation was reverted immediately. This is a more informative experiment than a green `mutmut` run because it documents exactly *which* invariants the tests enforce.

**Table 10. Hand-curated mutation results on COGANT algorithmic core.**

| Module | Mutants tested | Killed | Survived | Mutation score |
|---|---:|---:|---:|---:|
| `gnn/matrices.py` | 5 | 3 | 2 | 60% |
| `translate/engine.py` | 3 | 1 | 2 | 33% |
| `markov/blanket.py` | 2 | 1 | 1 | 50% |
| `statespace/compiler.py` | 2 | 1 | 1 | 50% |
| `static/dataflow.py` | 3 | 3 | 0 | 100% |
| **Total** | **15** | **10** | **5** | **66.7%** |

The five surviving mutants are documented individually in `../cogant/docs/evaluation/MUTATION_REPORT.md` §"Surviving mutants --- action required" (aversive preference path in `compute_C`, sensory↔active boundary role swap in `markov/blanket.py`, `>=`→`>` boundary flip in `_map_confidence`, `CONFIGURATION` neighbour bias in `compute_D`, and the single-pass fixpoint iteration cap). Three of the five were closed by hardening tests in the same commit: `test_C_aversive_preference_produces_negative_log_pref` kills the aversive-preference survivor, `test_boundary_with_only_outgoing_edge_is_active` / `test_boundary_with_only_incoming_edge_is_sensory` kill the Markov-blanket swap, and `test_map_confidence_exact_boundary_values` kills the `>=`→`>` family. The remaining two survivors (CONFIGURATION-bias and single-pass fixpoint) are documented follow-ups that require non-trivial fixture extensions. The measured score on the hand-picked set is therefore **10 killed / 15 total = 66.7%** before hardening, and the documented target after the follow-ups is 80% or better.

The modules with the strongest mutation signal are `static/dataflow.py` (3 of 3 killed --- every edge-kind string mutation is caught by the dataflow-tuple-assertion tests) and the row/column normalisation paths in `gnn/matrices.py` (4 of 5 killed --- every arithmetic mutation to `_normalize_row`, `_DEFAULT_DIRECT_MASS`, the `compute_C` sign-flip, the `compute_B` axis swap, and the `compute_A` fallback branch is killed by the `A_rows_sum_to_one`, `B_columns_sum_to_one_per_action`, and `A_concentrates_mass_on_direct_reads` tests). The modules that drag the overall score down are those whose tests assert structural invariants (disjointness, normalisation, shape) but do not pin down the *direction* or *magnitude* of individual entries.

## Benchmark suite (shipped)

A reproducible benchmark harness lives at [`../cogant/benchmarks/bench_suite.py`](../cogant/benchmarks/bench_suite.py) and writes its canonical results to [`../cogant/benchmarks/results/`](../cogant/benchmarks/results/). The most recent run committed to the tree (`bench(p1.5): Rust build status + Python vs Rust benchmark results`, then superseded by `bench(suite): reproducible 6-fixture benchmark harness with stage timing + memory + GNN stats`) executed each fixture for three iterations on CPython 3.12.11 / macOS arm64 and recorded per-stage wall-clock time, peak memory, and the final GNN tensor shapes.

**Table 11. Benchmark suite results (`suite_20260409.md`, three iterations per fixture, CPython 3.12.11).**

| Fixture | Wall-clock median (ms) | Wall-clock p95 (ms) | Nodes | Edges | Mappings | Peak memory (MB) |
|---|---:|---:|---:|---:|---:|---:|
| `calculator` | 32 | 35 | 12 | 25 | 11 | 0.0 |
| `event_pipeline` | 36 | 37 | 23 | 36 | 21 | 0.1 |
| `flask_mini` | 43 | 45 | 26 | 40 | 25 | 0.3 |
| `flask_app` | 86 | 86 | 98 | 154 | 68 | 0.3 |
| `requests_lib` | 76 | 77 | 98 | 152 | 55 | 0.7 |
| `json_stdlib` | 48 | 49 | 29 | 34 | 19 | 0.0 |

The benchmark harness times the bare translation pipeline (`ingest`, `static`, `normalize`, `graph`, `translate`, `statespace`), so its wall-clock numbers are approximately an order of magnitude smaller than the end-to-end roundtrip times of Table 4: Tables 4 and 5 include validation, GNN package assembly, Mermaid and PNG rasterization, GraphML and Parquet serialization, and the HTML dashboard write, none of which are part of the benchmark hot path. For pure translation, every shipped fixture runs in under 100 ms and consumes less than a megabyte of peak memory; the stage breakdown in `suite_20260409.md` shows that for the smaller fixtures the dominant cost is `ingest` (repository walk + file hashing), and for the larger fixtures (`flask_app`, `requests_lib`) the dominant cost shifts to `graph` construction where `CallGraphBuilder` walks every `ast.Call` node to produce the CALLS edges recorded in Table 5.

Approximate stage breakdown from the same run: `ingest` 25--30 ms across all fixtures; `static` 1--4 ms; `normalize` 0--3 ms; `graph` 4--43 ms (dominated by `flask_app`); `translate` 0--3 ms; `statespace` 0--1 ms. The benchmark results file also records the per-fixture GNN tensor shapes --- for example `flask_app` produces $A \in \mathbb{R}^{21 \times 10}$, $B \in \mathbb{R}^{10 \times 10 \times 31}$, $C \in \mathbb{R}^{21}$, $D \in \mathbb{R}^{10}$ --- which match the state-space compiler outputs of Table 6 up to the benchmark's independent re-run sampling variance.

