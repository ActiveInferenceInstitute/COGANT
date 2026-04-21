# COGANT — Codebase-to-GNN Translation Engine

> **Translate software repositories into Active Inference generative models.**

COGANT converts Python, JavaScript, and TypeScript codebases into
[Active Inference Institute](https://activeinference.org/) **Generalized Notation Notation (GNN)**
state-space models — complete with A/B/C/D probabilistic matrices, Markov blanket
partitions, and principled free-energy derivations.

Current release: **v0.5.0** (2026-04-10). **Tests:** run `uv run pytest tests/ -q` from this directory for the live count (thousands of tests; skips/xfails vary by environment). **Coverage:** line gate in `pyproject.toml` (`--cov-fail-under=89`, `branch = false`, `omit` for `tools/` and `static/treesitter_parser.py`); reported total is typically ~90% on measured lines. **`cogant/evaluation/METRICS.yaml`** (regenerated via `../tools/regenerate_metrics.py`) holds manuscript-facing numbers and may lag the live suite — see `mypy_strict_errors`, `ruff_violations`, and `python_source_files` there for current counts; run `uv run mypy py/cogant/` and `uv run ruff check py/cogant/` for a live read. **Round-trip: 23/23 ISOMORPHIC** on the canonical eval set (see `docs/evaluation/`).

---

## What it does

```text
repo/ ──[ingest]──► ProgramGraph ──[translate]──► SemanticMappings ──[statespace]──► GNN
  V=nodes            22 declarative rules             HIDDEN_STATE,                A/B/C/D
  E=typed edges      fixpoint to convergence          OBSERVATION,                 matrices
                                                      ACTION, POLICY, ...
```

- **Forward path**: source code → program dependence graph → fixpoint translation → semantic
  mappings → compiled state space → GNN markdown bundle (AII-spec compliant).
- **Reverse path**: `py/cogant/reverse/` synthesizes a runnable Python package from any GNN
  bundle and is exposed through the top-level `cogant reverse` and `cogant roundtrip` CLI
  subcommands. The v0.5.0 POLICY / CONTEXT stub-emission fix attains **23 / 23 ISOMORPHIC**
  ($\varepsilon \geq 0.8$) on the canonical roundtrip evaluation set — see
  [`docs/evaluation/ROUNDTRIP_IMPROVEMENT.md`](docs/evaluation/ROUNDTRIP_IMPROVEMENT.md) and
  [`docs/evaluation/ROUNDTRIP_EVAL.md`](docs/evaluation/ROUNDTRIP_EVAL.md).
- **Incremental mode**: `cogant analyze --incremental <git-ref>` (or
  `PipelineConfig.incremental_since`) re-uses the previous run's program graph for unchanged
  source paths, measuring **19.6× no-change** and **5.6× single-file** speedups on the Flask
  benchmark.
- **Production server**: `cogant.server.app` exposes `/health` and `/translate` endpoints; a
  packaged `Dockerfile` (python:3.12-slim + uv, `EXPOSE 8080`) and `docker-compose.yml` turn
  the pipeline into a deployable microservice.

## Third-party GNN reference implementation

COGANT depends on the Active Inference Institute **generalized-notation-notation**
package (Python import `src.gnn`) as a **core** dependency for parsing and validating
against the upstream GNN toolchain. That package is licensed **CC-BY-NC-SA-4.0**;
see [`LICENSES.md`](LICENSES.md). COGANT itself remains MIT.

In addition to single-file `validate_gnn` checks, COGANT can drive the upstream
**25-step pipeline** (`src.main.execute_pipeline_step`, scripts `0_template.py`
through `24_intelligent_analysis.py`) over the produced `gnn_package/`. The pass
is opt-in (`--upstream-gnn-pipeline` on `analyze` / `translate` / `validate`,
or the standalone `cogant upstream-gnn <package_dir>` command) and skips
`11_render` and `12_execute` by default — those are framework-specific
(PyMDP / RxInfer / JAX / DisCoPy) code-generation and simulation steps that
typically require additional optional dependencies. See
[`py/cogant/gnn/upstream_bridge/AGENTS.md`](py/cogant/gnn/upstream_bridge/AGENTS.md)
for the full step catalogue, `UpstreamPipelineConfig` surface, and
`COGANT_RUN_UPSTREAM_PIPELINE=1` slow-test gate.

## Quick start

```bash
uv sync --extra all
uv run cogant translate examples/control_positive/calculator \
    --output output/calculator \
    --layout-output
uv run cogant validate output/calculator/gnn_package
```

Expected: a populated `output/calculator/` tree with `bundle.json`, `gnn_package/model.gnn.md`,
and a validator report scoring **100.0 / 100** on the calculator fixture.

**Batch / all formats (staging tree):** from the parent `projects_in_progress/cogant/` directory,
[`run_all.sh`](../run_all.sh) runs `translate`, `scan`, `graph`, `export-gnn`, `render`, `viz`, and
`validate` for each target in `run_all.json` (see [`run_all.example.json`](../run_all.example.json)).
Each target has its own folder under `output/runs/<id>/`; defaults include all `control_positive`
examples plus shallow-cloned public repos (`git_url`). You can run `../run_all.sh` from this
directory (inner package) or from the staging root.

## Features (v0.5.0)

- **Language front ends** — Python via CPython `ast`; JavaScript / TypeScript via `tree-sitter` with
  JS-grammar fallback for `.ts` files on mixed repositories.
- **22 translation rules** across five families (structural, semantic, control, behavioral,
  resilience; 5+5+3+4+5) — see `py/cogant/translate/rules/` — assigning 7 core Active Inference roles:
  HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONSTRAINT, CONTEXT, PARAMETER.
- **GNN A/B/C/D matrices** derived from program graph edges (READS → A matrix, WRITES/MUTATES/CALLS → B matrix, CONSTRAINT → C matrix, CONFIGURATION → D matrix). AII
  validator at **100 / 100** on all six shipped fixtures.
- **Principled state-space semantics** — Markov blanket partition, variational free energy
  computation, expected free energy optimization — not keyword heuristics.
- **Incremental analysis mode** — `cogant analyze --incremental <git-ref>` or
  `PipelineConfig.incremental_since` — 19.6× no-change (cached graph), 5.6× single-file
  (partial re-run) speedups on Flask. Complements `cogant changed` git-diff helper for CI.
- **Multi-episode Bayesian learning**: `AgentRuntime.run_multi_episode`, `run_episode`,
  `update_D_from_posterior`, `update_A_from_counts`.
- **Production FastAPI server**: `cogant.server.app` with `/health` and `/translate`
  endpoints, integration test suite, and Docker / docker-compose packaging.
- **Forward-reverse-forward round-trip**: 23 / 23 ISOMORPHIC across 12 zoo fixtures,
  3 real-world-example fixtures, and 8 uncurated third-party libraries; see
  [`docs/evaluation/ROUNDTRIP_EVAL.md`](docs/evaluation/ROUNDTRIP_EVAL.md) and
  [`docs/evaluation/ROUNDTRIP_IMPROVEMENT.md`](docs/evaluation/ROUNDTRIP_IMPROVEMENT.md).
- **Cross-language roundtrip**: `examples/zoo/13_js_observer` demonstrates a JavaScript
  observer round-trip with `role_match_score = 1.0`.
- **Rust acceleration** (optional, feature-gated: `COGANT_USE_RUST=1`): PyO3
  `connected_components` FFI for graph construction; pure-Python fallback elsewhere.
- Reverse synthesis: `cogant reverse` and `cogant roundtrip` subcommands synthesize a
  runnable Python package from any GNN bundle and verify forward-reverse-forward
  isomorphism.
- **Large test suite** (unit, integration, property, golden, fuzz); run `uv run pytest tests/ -q` for counts. Coverage policy is in **`pyproject.toml`** (line gate; optional paths omitted from measurement). Type stubs (`.pyi`) and `py.typed` ship with the package.
- `cogant doctor` — environment diagnostics extended in v0.5.0 with tree-sitter grammar
  checks, uv lockfile parity, and optional-dependency audit.

## CLI surface

`cogant --help` is ground truth. The Typer app in
[`py/cogant/cli/main.py`](py/cogant/cli/main.py) currently registers **26 help rows / 27 leaf commands** (22 `@app.command()` + 2 `app.command(name=...)` + `plugin` + `migrate` sub-typers — `plugin` exposes one extra leaf via `add_typer`):

| Command | Purpose |
| --- | --- |
| `init` | Initialize a new COGANT project (guided first-time setup). |
| `doctor` | Diagnose the COGANT runtime environment (Python, uv, tree-sitter, Rust, disk). |
| `scan` | Scan a repository and print a quick summary. |
| `extract-static` | Run static analysis only (AST, type inference, symbol tables). |
| `extract-dynamic` | Run dynamic analysis (coverage databases, runtime traces). |
| `graph` | Build and summarise the program dependency graph. |
| `translate` | Full pipeline: ingest → graph → translate → statespace → export. |
| `analyze` | Alias for `translate`; accepts `--incremental <git-ref>` for per-commit CI re-runs. |
| `statespace` | Compile an Active Inference state-space model (S, O, A, π). |
| `process` | Extract the pipeline / execution process model from a repository. |
| `export-gnn` | Re-export a previously generated GNN bundle in a different format. |
| `render` | Render an interactive HTML site from a bundle. |
| `viz` | Generate PNGs for every Mermaid / SVG / dot / network artifact in a run. |
| `validate` | Run validation checks on a bundle, run directory, or GNN package. |
| `diff` | Compare two bundles or output directories and report drift. |
| `changed` | List files changed since a git ref (incremental analysis helper). |
| `explain` | Explain why a node was assigned its Active Inference role. |
| `benchmark` | Benchmark pipeline wall-clock performance over several runs. |
| `analyze-static` | Run only the static-analysis stages and report findings. |
| `analyze-graph` | Run the graph-construction stage and print adjacency summary. |
| `visualize` | Render interactive SVG/HTML visualizations of program graph and matrices. |
| `export` | Export GNN bundle to a specified format (json, jsonl, parquet, graphml). |
| `reverse` | Synthesize a Python package from a GNN markdown file. |
| `roundtrip` | Verify forward-reverse-forward round-trip isomorphism. |

The `analyze` / `translate` subcommand accepts `--incremental <git-ref>` (equivalent to
`PipelineConfig.incremental_since`) for per-commit CI re-runs over a Git diff.

## Architecture

The pipeline executes 10 ordered stages, each optional and reorderable via `PipelineConfig.stages`:

```
Source Code
    ↓
1.  ingest      — enumerate files
2.  static      — extract AST / symbols / types
3.  normalize   — canonicalize representations
4.  graph       — build ProgramGraph (V=nodes, E=typed edges)
5.  dynamic     — optional: merge coverage/traces
6.  translate   — apply 22 rules → SemanticMappings (HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONSTRAINT, CONTEXT)
7.  statespace  — compile state-space model
8.  process     — extract process / execution model
9.  export      — emit GNN markdown (19 sections), JSON, companion artifacts
10. validate    — integrity checks, score bundle 0–100
    ↓
GNN Bundle (A/B/C/D matrices, role assignments, provenance)
    ↓ (optional reverse path)
Synthesized Python Package
    ↓ (verification)
Re-forward for Isomorphism Check
```

**Forward-reverse-forward round-trip:** v0.5.0 achieves **23/23 ISOMORPHIC** (ε=1.0) across 12 zoo fixtures, 3 curated real-world examples, and 8 uncurated libraries. The reverse synthesizer emits POLICY and CONTEXT stubs proportional to origin GNN role counts, ensuring semantic preservation.

See [docs/architecture/](docs/architecture/) for per-module deep dives and [docs/theory/roundtrip.md](docs/theory/roundtrip.md) for round-trip validation details.

## Documentation

- **Getting started**
  - [Installation](docs/getting-started/installation.md)
  - [Quickstart](docs/getting-started/quickstart.md)
- **Tutorials (numbered, in order)**
  - [1. Quickstart — 5 minute end-to-end](docs/tutorials/01_quickstart.md)
  - [2. Small repo walkthrough — `calculator`](docs/tutorials/02_small_repo_walkthrough.md)
  - [3. Flask app walkthrough](docs/tutorials/03_flask_walkthrough.md)
  - [4. Writing a custom translation rule](docs/tutorials/04_custom_rules.md)
  - [5. Reading A / B / C / D matrices](docs/tutorials/05_gnn_interpretation.md)
  - [6. Reverse mode — GNN → code](docs/tutorials/06_reverse_mode.md)
  - [7. Authoring a language plugin](docs/tutorials/07_plugin_authoring.md)
- **Theory**
  - [Code as a generative model](docs/theory/code_as_generative_model.md)
  - [Active Inference primer](docs/theory/active_inference_primer.md)
  - [Active Inference mapping (deep)](docs/theory/active_inference.md)
  - [GNN format reference](docs/theory/gnn_format_reference.md)
- **Reference**
  - [CLI reference](docs/cli.md)
  - [Glossary](docs/reference/glossary.md)
  - [API reference](docs/api/)
- [R&D log](docs/evaluation/R&D_LOG.md)

## Development

```bash
uv sync --extra all            # install everything (python + viz + tree-sitter + rust bindings)
uv run cogant doctor            # verify the environment
uv run pytest tests/ -q         # full suite; coverage gate per pyproject.toml (~90% on measured lines)
uv run mypy py/cogant/          # strict type check; see `evaluation/METRICS.yaml` (`mypy_strict_errors`, `python_source_files`)
uv run ruff check py/cogant/    # lint; see `evaluation/METRICS.yaml` (`ruff_violations`)
make build-rust                 # optional: compile the rust backend
```

Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md). Code of conduct:
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Honest scope

COGANT prioritizes **transparent, reproducible graphs** over **complete semantics**. Whole-program
soundness is not the goal; provenance, deterministic output, and explicit uncertainty are. When
the pipeline lacks evidence for a rule or matrix entry, it emits a **validation finding** and a
documented fallback rather than silently guessing. Known limitations — identity-biased A matrix
fill, identity-fallback B tensor, uniform C/D when no constraint/configuration evidence exists —
are tracked in [`docs/theory/active_inference.md § Known limitations`](docs/theory/active_inference.md#known-limitations).

## License

MIT — see [`LICENSE`](LICENSE).

## Citation

```bibtex
@software{cogant2026,
  title  = {COGANT: Codebase-to-GNN Translation Engine},
  author = {{COGANT contributors}},
  year   = {2026},
  url    = {https://github.com/cogant/cogant},
  version = {0.5.0}
}
```
