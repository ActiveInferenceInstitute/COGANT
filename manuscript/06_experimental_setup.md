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

## What to record

For reproducible experiments, record: COGANT version or commit hash, interpreter version, list of stages executed, configuration file contents (redacted), input repository commit hash, and random seeds for any learned components **outside** COGANT that consume the exports.
