# cogant (Python Core)

The Python implementation of COGANT: parsers, graph construction, translation, validation, and export.

## Contents

Thirty subpackages. Parent [`AGENTS.md`](../../AGENTS.md) carries the stage mapping; per-directory
`AGENTS.md` files cover responsibilities and file lists.

- **api/** — Stable Python entry points (`Session`, `PipelineRunner`, `Bundle`, `ReviewAPI`).
- **cache/** — Content-addressed caches for ingest/parse results.
- **cli/** — Typer app with 26 top-level `@app.command` decorators + `plugin` / `migrate` sub-typers (**29 leaf commands total**; see `cli/AGENTS.md` and `docs/cli_reference.md`).
- **config/** — Configuration schema and defaults.
- **dynamic/** — Hooks for execution-informed facts (coverage, traces).
- **export/** — Writers for 9 formats (JSON, GraphML, Parquet, SVG, PNG, PDF, Mermaid, DOT, JSONLINES).
- **gnn/** — AII-spec GNN bundle emission.
- **graph/** — In-memory `ProgramGraph` with builder, queries, merge, analysis.
- **ingest/** — File discovery, manifest, repository scanning, language detection.
- **markov/** — Markov blanket partition (`explicit`, `module`, `kind`, `auto`, `mapping_kind`).
- **normalize/** — Cross-language symbol identity and reference resolution.
- **observability/** — Logging, metrics, and tracing helpers.
- **parsers/** — Re-exports and routing for Python/JS/TS/Rust/Go parsers under `../parsers/`.
- **pipeline/** — DAG-based pipeline scheduling (`PipelineDAG`, `Stage`, `DAGResult`).
- **plugins/** — Extension points and plugin base classes.
- **process/** — Timeline extraction and process-model policies.
- **provenance/** — Source attribution and run metadata tracking.
- **reverse/** — `PackagePlan`-based synthesis of a runnable Python package from a GNN bundle.
- **runtime/** — `AgentRuntime` (multi-episode Bayesian learning, free-energy loops).
- **schema/** — Versioned schema helpers.
- **schemas/** — Core type definitions (Graph, Bundle, Provenance, GNN export, `SemanticRole`, `MappingKind`).
- **scoring/** — Calibrated edge/node confidence and drift detection.
- **server/** — FastAPI app (REST + WebSocket).
- **simulate/** — Simulation drivers used by runtime / examples.
- **statespace/** — Compiles `SemanticMappings` into A/B/C/D matrices and policies.
- **static/** — Shared static analysis helpers (symbols, types, calls, dataflow, Halstead).
- **tools/** — Developer helpers (not shipped as public API).
- **translate/** — Fixpoint engine + 22 declarative rules (`structural`, `semantic`, `control`, `behavioral`, `resilience`; 5+5+3+4+5).
- **validate/** — AII validator (0–100 score), schema checks, integrity audits.
- **viz/** — PDF / PNG / SVG / Mermaid / HTML visualization.

## Usage

All modules are importable from the root cogant package:

```python
from cogant import PipelineRunner, Session, Bundle
from cogant.schemas import ProgramGraph
from cogant.graph import ProgramGraphBuilder
from cogant.export import BundleExporter
```

Subsystem-specific imports:

```python
from cogant.ingest import RepoIngester
from cogant.translate import TranslationEngine
from cogant.validate import ValidationReport
```

## Dependencies
- networkx — graph representation and algorithms
- pydantic — schema validation
- PyYAML — configuration files
- pyarrow — columnar export
- jinja2 — HTML rendering
- All modules depend on schemas/ and static/
