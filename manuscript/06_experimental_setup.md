# Experimental setup

## Environment

**Requirements**: Python 3.11 or newer (enforced in `pyproject.toml`), plus an optional Rust toolchain (`cargo`, stable 1.70+) when building native acceleration crates under `../cogant/rust/`.

From the COGANT package root [`../cogant/`](../cogant/) (where `pyproject.toml` and `py/cogant/` live), install with `uv sync --all-extras`, or `pip install -e ".[dev,viz]"` / `pip install -e ".[all]"` as in [GETTING_STARTED.md](../cogant/GETTING_STARTED.md). Run those commands from that directory when working inside this monorepo layout. Python sources live under [`../cogant/py/cogant/`](../cogant/py/cogant/); see the package [README.md](../cogant/README.md).

## Running the API

Minimal **Session** run:

```python
from cogant import Session

session = Session.from_target("./path/to/repo")
session.extract_static()
session.build_graph()
session.translate_to_gnn()
session.export_all("output/")
```

Minimal **Pipeline** run:

```python
from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/")
bundle = runner.run("./path/to/repo", config)
```

Adjust `PipelineConfig.stages`, `skip_stages`, and `plugins` to match the languages and tooling available on the machine.

## Configuration files

YAML configuration can drive pipeline behavior (paths, stages, plugin options). The architecture and SPEC documents describe the configuration surface; keep project-specific secrets out of version control.

A minimal pipeline configuration looks like this:

```yaml
# cogant.config.yaml
pipeline:
  stages:
    - ingest
    - static
    - normalize
    - graph
    - dynamic       # optional; skipped if no coverage/trace inputs
    - translate
    - statespace
    - process
    - export
    - validate

  skip_stages: []   # e.g. ["dynamic"] to force static-only runs

  plugins:
    dynamic:
      coverage_path: "./coverage.xml"
      trace_path: "./chrome_trace.json"

  output_dir: "./cogant_output/"
  verbose: true
  dry_run: false
```

Each stage key corresponds to a handler in `cogant.api.pipeline.PipelineRunner.stage_handlers`; plugin sub-dictionaries are passed through to the stage at invocation time. `cogant translate --config` accepts either a top-level `pipeline` object or a flat mapping and normalizes both forms into `PipelineConfig`.

## CLI

Use the `cogant` CLI for scripted batch runs—see `../cogant/docs/CLI_GUIDE.md` for the command list that matches the installed version.

## Export targets

The primary export targets are the **Generalized Notation Notation (GNN)** canonical Markdown (`model.gnn.md`) and the equivalent companion JSON files described in `../cogant/docs/GNN_EXPORT.md`. Optional interop targets (GraphML, Parquet) support analysis in Gephi/yEd and DuckDB, and optional tensor views for PyTorch Geometric, DGL, or HDF5 can be selected when downstream graph neural network training pipelines need to consume the program graph as a relational tensor. Ensure the Python environment includes optional dependencies for these tensor exports when those code paths are used.

## Python AST parser capabilities

The v0.1.x front end relies on `cogant.static.parser.PythonASTParser`, which processes Python source through the standard-library `ast` module at the CPython version available in the runtime (3.9+ recommended). The parser extracts the following construct categories:

- **Module-level entities**: module docstrings, `__all__` exports, top-level assignments.
- **Functions and methods**: `def` and `async def`, including signatures with positional, keyword, variadic (`*args`, `**kwargs`), and positional-only parameters. Default values are recorded as constant expressions where statically evaluable.
- **Classes**: class definitions, base classes, metaclasses, and the `__init__` / `__new__` boundary.
- **Decorators**: `@staticmethod`, `@classmethod`, `@property`, `@dataclass`, and arbitrary user-defined decorators. Decorator arguments are captured as attribute metadata.
- **Type annotations**: PEP 484 / 526 / 604 annotations on function parameters, return types, and variable assignments. Generic subscripts (`List[int]`, `Dict[str, Any]`) are preserved as type strings.
- **Comprehensions and generators**: list, set, dict comprehensions and generator expressions are represented as anonymous FUNCTION nodes with DATA_FLOW edges to their enclosing scope.
- **Control flow**: `if`/`elif`/`else`, `for`/`while`/`else`, `try`/`except`/`finally`, `with`/`async with`, and `match`/`case` (Python 3.10+) are mapped to CONTROLFLOW_NODE entities.
- **Imports**: `import` and `from ... import` statements produce MODULE_IMPORT roles with edges to the resolved module when discoverable on the file system.
- **Constants**: module-level and class-level assignments to `Final` or ALL_CAPS names are classified as CONSTANT nodes.

Constructs that require runtime evaluation (for example `exec`, `importlib.import_module`, or dynamic `__getattr__`) are recorded as EXTERNAL nodes with HEURISTIC provenance and correspondingly lower confidence.

## Progressive IR stages

Processing advances through six intermediate representations, each adding semantic detail atop its predecessor. Table 3 summarizes what each stage contributes.

**Table 3. Progressive IR stages and their contributions.**

| Stage | IR name | Key additions | Typical output size (10K-function repo) |
|-------|---------|---------------|----------------------------------------|
| 1 | Repo IR | Raw entities and relationships per file; deduplication; merged type info | ~15 MB JSON |
| 2 | Program Graph IR | Consolidated directed graph $G=(V,E)$; stable identifiers; confidence and provenance on every node and edge | ~20 MB JSON |
| 3 | Semantic Mapping IR | Translation rules applied; semantic roles assigned; confidence adjusted by rule engine | ~22 MB JSON (graph + mapping log) |
| 4 | State Space IR | Variables, actions, transitions, observations; dynamic traces integrated where available | ~5 MB JSON (behavioral model) |
| 5 | Process Model IR | Higher-level control patterns (request--response, producer--consumer, state machines) | ~2 MB JSON |
| 6 | Validation IR | Coverage metrics, confidence distribution, schema compliance, consistency checks, reproducibility hashes | ~1 MB JSON (report) |

Stages 4 and 5 are **partial** for many repositories: the state-space compiler requires either execution traces or sufficient static structure (for example annotated state machines) to produce meaningful output. Where dynamic evidence is available, COGANT's ingestion pipeline follows the established pattern of attaching runtime observations (coverage, call frequencies, traces) to static program elements --- dynamic instrumentation frameworks such as Pin [@luk2005pin] and invariant detectors such as Daikon [@ernst2007daikon] established this general approach of augmenting static program structure with execution-time evidence. The pipeline tolerates missing stages gracefully; the Validation IR records which stages completed and which were skipped.

## Performance characteristics

The architecture targets the following benchmarks on a 4-core machine, as specified in `../cogant/docs/ARCHITECTURE.md`:

| Repository size | Target wall-clock time | Memory budget |
|----------------|----------------------|---------------|
| 10K functions | < 30 s | < 500 MB |
| 100K functions | < 5 min | < 2 GB |
| 1M functions | < 1 hr | < 2 GB (streaming) |

These are architecture targets, not benchmark claims from this manuscript. They assume the Python orchestration layer with Rust acceleration on critical paths (graph construction, rule matching, and Generalized Notation Notation section/tensor packing in `cogant-gnn`). In the current v0.1.x release, where Rust bindings are staged rather than fully wired, Python fallback implementations handle most graph operations.

Current `PipelineRunner` behavior is stage-sequential with per-stage error capture and continuation. It does not currently expose built-in incremental checkpoint/resume in `cogant.api.pipeline`; treat checkpointing as a potential outer-orchestration feature rather than a guaranteed package-level runtime behavior.

## Measured runs on packaged fixtures

The following tables record measurements taken by running the shipped `RoundtripOrchestrator` (`../cogant/examples/orchestrate_roundtrip.py`) against every fixture distributed with the package. Three fixtures are the control-positive synthetic repositories under `../cogant/examples/control_positive/` (`calculator`, `event_pipeline`, `flask_mini`); the other three are real-world code under `../cogant/examples/real_world/` (`flask_app`, a six-module Flask service; `requests_lib`, a six-module reduction of the `requests` HTTP library; and `json_stdlib`, a four-module reduction of the CPython `json` package). Each run executes the full static pipeline (ingest, parse, symbols, imports, call graph, program graph, translation, state-space compilation, GNN package build, validation). Wall-clock times were measured on a single macOS workstation with the pure-Python fallback implementations --- Rust acceleration is not wired in v0.1.x, so these numbers correspond to the Python orchestration layer with no native crates loaded.

All numbers in Tables 4--7 are regenerated by `../_rnd/figures/generate_figures.py`, which re-runs the orchestrator over every fixture, re-reads the emitted JSON, and writes `../_rnd/figures/metrics.json` alongside the figure PNGs. Structural metrics (nodes, edges, edge-kind and node-kind breakdowns, LOC, file counts) are deterministic; rule-driven metrics (total mappings, state variables, observations, actions, transitions) vary by at most one or two units across runs because the extractor walks dictionaries whose ordering is process-local, and wall-clock times vary by a few seconds depending on whether the visualization pass rasterizes PNGs. The figures below match the canonical `metrics.json` committed under `../_rnd/figures/`.

**Table 4. Repository-level pipeline metrics (canonical run, COGANT v0.1.0).**

| Fixture | Files | LOC | Nodes | Edges | Mappings | State vars | Obs | Actions | Transitions | GNN sections | GNN score | Wall-clock (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `calculator` | 1 | 122 | 12 | 27 | 5 | 0 | 3 | 1 | 1 | 31 | 100.0 | 7.42 |
| `event_pipeline` | 1 | 147 | 23 | 66 | 20 | 1 | 9 | 10 | 10 | 31 | 100.0 | 8.58 |
| `flask_mini` | 1 | 168 | 26 | 51 | 19 | 3 | 2 | 14 | 14 | 31 | 100.0 | 8.80 |
| `flask_app` | 6 | 853 | 98 | 597 | 51 | 16 | 19 | 16 | 16 | 31 | 100.0 | 14.58 |
| `requests_lib` | 6 | 750 | 98 | 345 | 46 | 9 | 31 | 7 | 7 | 31 | 100.0 | 12.19 |
| `json_stdlib` | 4 | 1231 | 29 | 68 | 8 | 3 | 5 | 0 | 0 | 31 | 100.0 | 9.08 |

"GNN sections" counts the level-two Markdown headings emitted in `model.gnn.md`, which on every fixture sits at 31 (the 18 core Generalized Notation Notation sections plus section-specific subheadings for state space, observations, actions, and transitions). "GNN score" is the `score` field returned by `GNNValidator.validate()` on the compiled `gnn_package/` directory; every fixture validates at 100.0 with zero errors and zero warnings. The six fixtures together cover one-to-six file repositories and 122 to 1231 lines of code, exercising the pipeline on both minimal control positives and small real-world modules. Wall-clock times fall between roughly seven and fifteen seconds on a 2024-class Apple-silicon workstation; the bulk of the cost on the larger fixtures is the call-graph construction step in `CallGraphBuilder` plus the PNG rasterization pass in `cogant.viz.png_export`.

**Table 5. Program graph composition by fixture.**

Node kinds (MODULE / CLASS / METHOD / FUNCTION) and edge kinds (CONTAINS / WRITES / READS / CALLS / IMPORTS / INHERITS) are populated directly from the AST extractor and call-graph builder; all other kinds listed in `cogant.schemas.core.NodeKind` and `EdgeKind` remain unused on these fixtures because the Python front end currently focuses on the structural core. The counts below are taken verbatim from the `statistics` block of each fixture's `program_graph.json`.

| Fixture | MODULE | CLASS | METHOD | FUNCTION | CONTAINS | WRITES | READS | CALLS | IMPORTS | INHERITS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `calculator` | 1 | 1 | 10 | --- | 11 | 5 | 9 | 2 | --- | --- |
| `event_pipeline` | 1 | 6 | 16 | --- | 22 | 1 | 10 | 30 | --- | 3 |
| `flask_mini` | 1 | 7 | 18 | --- | 25 | 6 | 7 | 11 | --- | 2 |
| `flask_app` | 6 | 25 | 57 | 10 | 92 | 15 | 38 | 433 | 10 | 9 |
| `requests_lib` | 6 | 20 | 59 | 13 | 92 | 8 | 42 | 183 | 10 | 10 |
| `json_stdlib` | 4 | 3 | 9 | 13 | 25 | 3 | 6 | 32 | 2 | --- |

The distribution matches the intuitive shape of the fixtures: class-heavy repositories (`flask_app`, `requests_lib`, `flask_mini`) show METHOD-dominated node counts and INHERITS edges, while the functional `json_stdlib` shows a balanced METHOD/FUNCTION split and no INHERITS edges. CALLS edges dominate the large repositories (`flask_app` at 433, `requests_lib` at 183), confirming that the call-graph construction step in `CallGraphBuilder` is the primary source of edge density on real code.

**Table 6. State-space compilation outputs.**

For each fixture the `StateSpaceCompiler` emits a `StateSpaceModel` whose variables, observations, actions, and transitions are then packaged into `gnn_package/state_space.json`, `observations.json`, `actions.json`, and `transitions.json`. The counts reflect the end-to-end behavior of the compiler on these inputs, not the rule engine's raw mapping output.

| Fixture | State variables | Observations | Actions | Transitions | Policies |
|---|---:|---:|---:|---:|---:|
| `calculator` | 0 | 3 | 1 | 1 | 1 |
| `event_pipeline` | 1 | 9 | 10 | 10 | 4 |
| `flask_mini` | 3 | 2 | 14 | 14 | 6 |
| `flask_app` | 16 | 19 | 16 | 16 | 6 |
| `requests_lib` | 9 | 31 | 7 | 7 | 1 |
| `json_stdlib` | 3 | 5 | 0 | 0 | 1 |

`calculator` compiles zero hidden-state variables because the fixture exposes pure arithmetic methods whose WRITES-edge footprint does not cross the classifier threshold used by `StateVariableExtractor`; it still compiles a single action and a single transition, so the pipeline remains end-to-end valid and the GNN package still validates at 100.0. `json_stdlib` compiles zero actions because the reduced CPython `json` sources consist almost entirely of function-level utilities whose semantic role falls outside the ACTION-mapping rule set, but the pipeline still emits a compiled `actions.json` with an empty `actions` list and a single default policy --- downstream consumers see the same schema as for the action-bearing fixtures. The `requests_lib` fixture has the highest observation count in the table because its session/adapter classes expose a large number of read-only attributes that the rule engine matches as `OBSERVATION` mappings.

**Table 7. Output artifacts per run.**

Every fixture emits the same `gnn_package/` directory layout with 19 canonical files: `model.gnn.md`, `model.gnn.json`, the section JSONs (`state_space`, `observations`, `actions`, `actions_policies`, `transitions`, `preferences`, `preferences_constraints`, `factors`, `connections`, `ontology`, `provenance`), the `program_graph.json` and `process_model.json` snapshots, the `markov_blanket.json` and `markov_network.json` extracts, and the `manifest.json` index. The `RoundtripOrchestrator` additionally writes diagnostic artifacts at the top level of `output_dir`: six Mermaid diagrams (class, state, sequence, dependency, boundary, semantic flow), typed graph and Cytoscape exports, a GraphML file, a Parquet table, a dashboard HTML site, simulation traces, and a GNN execution report.

| Fixture | `gnn_package/` files | Validation errors | Validation warnings |
|---|---:|---:|---:|
| `calculator` | 19 | 0 | 0 |
| `event_pipeline` | 19 | 0 | 0 |
| `flask_mini` | 19 | 0 | 0 |
| `flask_app` | 19 | 0 | 0 |
| `requests_lib` | 19 | 0 | 0 |
| `json_stdlib` | 19 | 0 | 0 |

These numbers were collected by the reproducible script `../_rnd/figures/generate_figures.py`, which re-runs the orchestrator over every fixture, re-reads the emitted JSON, and writes both the summary table and the figures used in this manuscript into `../_rnd/figures/` (namely `fig1_graph_sizes.png`, `fig2_node_kinds.png`, `fig3_state_space.png`, and `fig4_pipeline_latency.png`, plus the machine-readable `metrics.json`).

## What to record

For reproducible experiments, record: COGANT version or commit hash, interpreter version, list of stages executed, configuration file contents (redacted), input repository commit hash, and random seeds for any learned components **outside** COGANT that consume the exports.
