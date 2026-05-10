# Exports, parser capabilities, and progressive IR stages {#sec:06-02-exports-parser-and-ir-stages}


## Export targets

The primary export targets are the **Generalized Notation Notation (GNN)** canonical Markdown (`model.gnn.md`) and the equivalent companion JSON files described in `../cogant/docs/export/README.md`. Optional interop targets (GraphML, Parquet) support analysis in Gephi/yEd and DuckDB, and optional tensor views for PyTorch Geometric, DGL, or HDF5 can be selected when downstream graph neural network training pipelines need to consume the program graph as a relational tensor. Ensure the Python environment includes optional dependencies for these tensor exports when those code paths are used.

## Python AST parser capabilities

The v{{VERSION}} front end relies on `cogant.static.parser.PythonASTParser`, which processes Python source through the standard-library `ast` module at the CPython version available in the runtime (3.11+ required, consistent with the `requires-python = ">=3.11"` declared in `../cogant/pyproject.toml`). The parser extracts the following construct categories:

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

Processing advances through six intermediate representations, each adding semantic detail atop its predecessor. The pipe table below is the canonical @tbl:progressive-ir-stages.

| Stage | IR name | Key additions | Typical output size (10K-function repo) |
|-------|---------|---------------|----------------------------------------|
| 1 | Repo IR | Raw entities and relationships per file; deduplication; merged type info | ~15 MB JSON |
| 2 | Program Graph IR | Consolidated directed graph $G=(V,E)$; stable identifiers; confidence and provenance on every node and edge | ~20 MB JSON |
| 3 | Semantic Mapping IR | Translation rules applied; semantic roles assigned; confidence adjusted by rule engine | ~22 MB JSON (graph + mapping log) |
| 4 | State Space IR | Variables, actions, transitions, observations; dynamic traces integrated where available | ~5 MB JSON (behavioral model) |
| 5 | Process Model IR | Higher-level control patterns (request--response, producer--consumer, state machines) | ~2 MB JSON |
| 6 | Validation IR | Coverage metrics, confidence distribution, schema compliance, consistency checks, reproducibility hashes | ~1 MB JSON (report) |

: Table 3 — Progressive IR stages and their contributions. {#tbl:progressive-ir-stages}

Stages 4 and 5 are **partial** for many repositories: the state-space compiler requires either execution traces or sufficient static structure (for example annotated state machines) to produce meaningful output. Where dynamic evidence is available, COGANT's ingestion pipeline follows the established pattern of attaching runtime observations (coverage, call frequencies, traces) to static program elements --- dynamic instrumentation frameworks such as Pin [@luk2005pin] and invariant detectors such as Daikon [@ernst2007daikon] established this general approach of augmenting static program structure with execution-time evidence. The pipeline tolerates missing stages gracefully; the Validation IR records which stages completed and which were skipped.

## See also (MkDocs)

Python front end and parsers: [`../cogant/docs/plugins/README.md`](../cogant/docs/plugins/README.md). Export targets: [`../cogant/docs/export/README.md`](../cogant/docs/export/README.md).
