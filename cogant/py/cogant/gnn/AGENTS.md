# Agents — py/cogant/gnn

## Owner
GNN Bundle & Model Execution

## What Is the GNN Module

The `gnn/` module produces self-contained Active Inference model bundles and executes them. It is **post-pipeline** infrastructure consumed by the `export/` (stage 9) and `validate/` (stage 10) stages. Given a `ProgramGraph`, `StateSpaceModel`, `ProcessModel`, and semantic mappings, this module:

1. **Builds GNN Package** — writes 16 required files plus diagrams/ and visualizations/ directories.
2. **Validates Bundle** — checks all 19 canonical sections present and well-formed; scores 0–100.
3. **Executes Models** — runs Active Inference with Variational Free Energy (VFE) and Expected Free Energy (EFE).
4. **Exports Results** — markdown (human-readable) and JSON (machine-readable).

A GNN bundle is a portable, reproducible artifact: it contains all information needed to understand, validate, or instantiate the learned agent model — no external dependencies on the original source code.

## Pipeline Integration

The 10 real pipeline stages (per `cogant.api.pipeline.PipelineConfig.stages`) are
``ingest → static → normalize → graph → dynamic → translate → statespace → process → export → validate``.
``gnn/``, ``viz/``, and ``scoring/`` are **post-pipeline** modules consumed by
``export`` and ``validate`` rather than being stages of their own:

```
stage 8 process/           → ProcessModel (factor graph + causal structure)
    ↓
gnn/  (post-pipeline)      → GNN Package (16 required files + diagrams/ + visualizations/)
    ↓
stage 9 export/            → Final artifacts (PDFs, summaries, deployment bundles)
    ↓
stage 10 validate/         → ValidationReport (structural correctness + confidence)
    ↓
scoring/  (post-pipeline)  → Drift detection + quality metrics
```

The GNN module is the boundary between symbolic analysis and Active Inference simulation. All model execution depends on the correctness of the GNN bundle.

### Upstream reference toolkit (`generalized-notation-notation`, **optional**)

The Active Inference Institute **generalized-notation-notation** package is an
**optional** dependency, installed only through the ``upstream`` extra
(``uv sync --extra upstream``; not part of ``all``). The extra pins a full GNN
5.0.1 released commit in ``pyproject.toml`` (mirrored in ``uv.lock``).
GNN >= 4.0 ships the top-level Python package ``gnn``; the bridge
(``cogant.gnn.upstream_bridge``, re-exported from ``cogant.gnn``) refuses an
installed upstream older than 4.0 or a ``gnn`` package owned by another
distribution. The ``GNN v2.0.0`` value COGANT writes under
``## GNNVersionAndFlags`` is COGANT's own schema identifier
(``cogant.schema.versions.CURRENT_GNN_VERSION``), not the upstream release.

Upstream single-file validation is **off by default**.
``GNNValidator.validate_package(package_dir, upstream_gnn=...)`` resolves the
flag through ``_resolve_upstream_flag``:

* ``upstream_gnn=True`` / ``False`` — the caller's explicit choice wins.
* ``upstream_gnn=None`` (the default) — upstream runs only when
  ``COGANT_ENABLE_UPSTREAM_GNN`` is truthy (``1`` / ``true`` / ``yes``,
  case-insensitive).

The pipeline's validate stage passes ``PipelineConfig.upstream_gnn_validation``
(default ``False``) explicitly, so pipeline runs need that field set to
``True``; the environment flag is not consulted there. ``cogant validate`` on
a package directory passes ``None`` (environment flag decides) and
``--no-upstream-gnn`` forces ``False``. ``COGANT_DISABLE_UPSTREAM_GNN`` is a
kill switch for the ``None`` case: it wins over ``COGANT_ENABLE_UPSTREAM_GNN``
but never over an explicit caller choice.

When it runs, the validator calls upstream ``gnn.validate_gnn_syntax`` at the
``standard`` level on ``model.gnn.md`` and stores the verdict under
``ValidationResult.details["upstream_gnn"]``. Upstream errors are appended to
``ValidationResult.errors`` as ``[upstream GNN] …``; a requested but
unavailable upstream adds a ``CAPABILITY_UNAVAILABLE`` error. Separately, the
validate stage always attempts the advisory ``parse_upstream_model_gnn_md``
summary (upstream ``parse_gnn_file``) and records an ``error`` entry when the
extra is absent; that summary never fails the stage.

Upstream is **CC-BY-NC-SA-4.0**; see ``LICENSES.md`` in the package root.

#### Upstream 25-step pipeline pass (opt-in)

Beyond the markdown validator, COGANT can drive the upstream **25-step
pipeline** over the produced ``gnn_package/``. The driver
(``cogant.gnn.upstream_bridge.pipeline``) issues **one**
``python -m gnn.main --only-steps …`` invocation and reads per-step outcomes
from ``<output_dir>/00_pipeline_summary/pipeline_execution_summary.json``;
see ``upstream_bridge/AGENTS.md`` for the per-step catalogue.

* Master switch: ``PipelineConfig.upstream_gnn_pipeline = True`` (default
  ``False``) or CLI ``--upstream-gnn-pipeline`` on
  ``analyze`` / ``translate`` / ``validate``.
* Default-skip list: ``DEFAULT_SKIP_STEPS == {1, 2, 11, 12}``
  (``1_setup`` mutates the caller's environment from an installed wheel,
  ``2_tests`` needs the upstream source checkout, ``11_render`` /
  ``12_execute`` are framework-specific code generation + simulation; opt in
  with ``--upstream-gnn-skip-steps ""`` or by listing them in
  ``--upstream-gnn-only-steps``).
* Refine: ``--upstream-gnn-only-steps "3,5,7"``,
  ``--upstream-gnn-skip-steps "1,2,11,12,13"``,
  ``--upstream-gnn-frameworks "lite|all|pymdp,jax"``,
  ``--upstream-gnn-llm-model <ollama-tag>``.
* Standalone: ``cogant upstream-gnn <package_dir>`` runs the same pass
  against an existing package without re-analysing the source repo.
* Inputs: only ``*.gnn.md`` files are staged into
  ``<output_dir>/_cogant_input/`` (GNN 4.x would treat every JSON sidecar
  as a model source).
* Output: per-step results in ``bundle.artifacts['upstream_pipeline_steps']``
  and ``['upstream_pipeline_summary']``, plus
  ``<output_dir>/upstream_pipeline_summary.json`` and the upstream console
  log ``<output_dir>/upstream_pipeline.log`` (``<output_dir>`` defaults to
  ``<run output>/upstream_pipeline/`` for pipeline runs).
* Failure model: **advisory only** — a failing upstream step appends a
  warning to the validate stage but never fails it. Promote to fatal in
  application code by inspecting ``UpstreamPipelineResult.failure_count``.

#### Facades only on ``cogant.gnn.upstream_bridge``

``cogant.gnn`` re-exports the bridge entry points listed in ``gnn/__init__.py`` ``__all__``.
Do not import upstream ``gnn`` directly from COGANT code: the bridge applies the
version/ownership gate, keeps the import lazy (upstream pulls in JAX/PyTorch), and
normalizes return values. If a new upstream entry point is needed, add a facade here
instead of bypassing the bridge. The current facades are thin wrappers around upstream
behavior plus path coercion and ``json_safe``:

| Name | Upstream target (GNN 4.x) |
|------|---------------------------|
| ``run_upstream_validate_gnn`` / ``upstream_validate_markdown`` | ``validate_gnn_syntax`` (level ``standard`` by default) |
| ``upstream_parse_file`` | ``parse_gnn_file`` |
| ``upstream_discover_files`` | ``discover_gnn_files`` |
| ``upstream_process_directory`` | ``process_gnn_directory`` |
| ``upstream_process_directory_lightweight`` | ``process_gnn_directory_lightweight`` |
| ``upstream_process_multi_format`` | ``process_gnn_multi_format`` |
| ``upstream_generate_report`` | ``generate_gnn_report`` |
| ``upstream_validate_structure`` | ``check_gnn_file_structure`` |
| ``upstream_validate_file_content`` | ``validate_gnn_source`` |
| ``upstream_validate_syntax_formal`` | ``validate_gnn_syntax`` |
| ``upstream_parse_formal`` | ``parse_gnn_formal`` |
| ``upstream_module_info`` | ``get_module_info`` |

Heavy directory pipelines are not duplicated in COGANT tests; call upstream with small
fixtures if you need to debug imports.

## Core Components

### GNNPackageBuilder (package.py)

Orchestrates creation of a complete GNN package on disk.

**REQUIRED_FILES** — 16 required files (from `package.py` / `validator.py`):
1. `manifest.json` — package metadata (version, timestamp, checksums)
2. `model.gnn.md` — human-readable canonical markdown (19 sections)
3. `model.gnn.json` — machine-readable metadata
4. `state_space.json` — variable definitions, cardinalities, factorization
5. `observations.json` — observation modalities (A matrix metadata)
6. `actions.json` — action definitions and effects
7. `transitions.json` — state evolution rules (B matrix)
8. `preferences.json` — goal structure (C matrix)
9. `factors.json` — factor graph from ProcessModel
10. `provenance.json` — evidence tracking and attribution
11. `ontology.json` — semantic mappings and symbol dictionary
12. `actions_policies.json` — canonical actions and policies
13. `connections.json` — factor graph connections
14. `preferences_constraints.json` — detailed constraints
15. `markov_blanket.json` — Active Inference Markov blanket partition
16. `markov_network.json` — collapsed four-role aggregate network

The Markov blanket pair is best-effort: when extraction fails both files are written as `status: "unavailable"` placeholders and `manifest.json` records `artifact_status.markov_blanket = "unavailable"` plus a warning.

**Key Methods:**
- `__init__(graph, state_space, process_model, mappings, config)` — initialize builder
- `build(output_dir) -> dict[str, Any]` — write all files; returns metadata dict

**Attributes:**
- `PACKAGE_VERSION` — semantic version of package format (e.g., "0.5.0")
- `checksums` — `dict[str, str]` mapping file paths to SHA256 hashes
- `timestamp` — ISO8601 creation time
- `graph`, `state_space`, `process_model`, `mappings`, `config` — cached inputs

**Algorithm:**
1. Validate inputs (graph, state_space, process_model all non-empty)
2. Create output directory
3. Compute A, B, C, D matrices from state space
4. Generate 19 canonical markdown sections (see GNNValidator.CANONICAL_SECTIONS)
5. Export matrices as JSON with precision metadata
6. Render diagrams (state machine, factor graph, temporal ordering)
7. Compute SHA256 checksums for all files
8. Write manifest with version, timestamp, checksums
9. Return summary dict with file counts, sizes, and index

### GNNValidator (validator.py)

Scores GNN bundles 0–100 by checking structural completeness, consistency, and confidence.

**CANONICAL_SECTIONS** — 19 required markdown sections (from `validator.py`):
1. Model Metadata (title, version, author, timestamp)
2. Repository Metadata (source file, commit hash, branch)
3. Source Coverage (% of code analyzed, symbol count)
4. State Space (variable definitions, cardinality, factorization)
5. Observation Modalities (A matrix, likelihood structure)
6. Actions/Policies (controllable transitions, preconditions)
7. Program Graph Connections (coupling matrix, information flow)
8. Factors (factor graph, message-passing structure)
9. Transition Structure (B matrix, state evolution)
10. Likelihood Structure (observation model, probability densities)
11. Preferences/Constraints (C and D matrices, goals)
12. Time Settings (synchrony regime, temporal ordering)
13. Parameterization (distribution parameters, learning rates)
14. Ontology Mapping (semantic roles, symbol dictionary)
15. Markov Blanket (Active Inference boundary partition)
16. Provenance (evidence tracking, confidence scores)
17. Confidence Scores (per-variable, per-matrix extraction confidence)
18. Rendering Hints (visualization preferences, layout hints)
19. Validation Notes (degraded outputs, known limitations)

**REQUIRED_FILES** — same 16 files as GNNPackageBuilder.REQUIRED_FILES:
- manifest.json, model.gnn.md, model.gnn.json, state_space.json, observations.json, actions.json, transitions.json, preferences.json, factors.json, provenance.json, ontology.json, actions_policies.json, connections.json, preferences_constraints.json, markov_blanket.json, markov_network.json

**ValidationResult** — NamedTuple holding validation outcome:
- `valid` — boolean; True iff no errors and all 19 sections present
- `errors` — `list[str]` of blocking issues (e.g., "Missing observations.json")
- `warnings` — `list[str]` of non-blocking issues (e.g., "Low confidence on variable X")
- `score` — [0.0, 100.0] composite score
- `section_scores` — `dict[str, float]` per-section scores
- `details` — `dict[str, Any]` detailed findings

**Key Methods:**
- `validate_package(package_dir) -> ValidationResult` — main entry
- `validate_markdown(markdown_str) -> list[str]` — check markdown sections
- `validate_state_space(state_space_json) -> list[str]` — check variable definitions
- `validate_matrices(matrices_json) -> list[str]` — check A/B/C/D consistency
- `validate_provenance(provenance_json) -> list[str]` — check evidence completeness
- `generate_validation_badge(result) -> str` — create SVG badge (e.g., "valid · 98/100")

**Scoring Algorithm:**
- Section presence: 19 points if all sections present (1 point each)
- JSON validity: 10 points if all required JSON files parse
- Matrix consistency: 20 points if A/B/C/D are internally consistent
- Confidence average: 20 points based on avg extraction confidence
- Completeness: 20 points based on % of state space covered
- Provenance: 12 points based on evidence ratio
- **Final score = (weighted sum) / 100** clamped to [0.0, 100.0]

All 6 shipped fixtures (control_positive, flask_app, event_pipeline, etc.) score 100/100.

### GNNMarkdownFormatter (formatter/ package)

Formats the 19 canonical sections into human-readable markdown.

**Key Methods:**
- `format_section(section_name, data) -> str` — format one section
- `format_all_sections(state_space, process, mappings) -> str` — format complete document
- `format_matrices(A, B, C, D) -> str` — render A/B/C/D as tables with annotations
- `format_factor_graph(factors) -> str` — render factor graph in Mermaid syntax
- `format_state_variables(variables) -> str` — tabulate all variables with metadata

**Output Style:**
- Markdown with embedded YAML for structured data
- Mermaid diagrams for graphs (state machine, factor graph, temporal ordering)
- Tables for matrices (with row/column labels and confidence annotations)
- Bullet lists for definitions, with linked references

### GNNJSONExporter (json_export.py)

Exports state space, matrices, and metadata to machine-readable JSON.

**Key Methods:**
- `export_state_space(state_space) -> dict[str, Any]` — variables, cardinalities, factors
- `export_matrices(A, B, C, D) -> dict[str, Any]` — sparse or dense matrix formats
- `export_graph_structure(process_model) -> dict[str, Any]` — factor graph as adjacency list
- `to_string(data) -> str` — serialize to JSON string with sorted keys

**Format:**
- Sparse matrix: `{shape: [m, n], indices: [[i, j, ...]], values: [v, ...]}`
- Dense matrix: `{shape: [m, n], data: [[...], ...]}`
- State variables: `{id: {name, type, cardinality, domain, factors, ...}, ...}`

### GNNMatrices (matrices.py)

Extracts and caches A, B, C, D matrices from state space and process model.

**Key Methods:**
- `compute_A_matrix(observations, state_vars) -> ndarray` — likelihood: P(obs | hidden state)
- `compute_B_matrix(transitions, state_vars) -> ndarray` — transition: P(next state | action)
- `compute_C_matrix(preferences) -> ndarray` — preferences: log P(obs), goal distribution
- `compute_D_matrix(factorization) -> ndarray` — prior: P(initial state)
- `to_sparse(matrix) -> dict` — convert to sparse JSON format
- `to_dense(matrix) -> dict` — convert to dense JSON format
- `validate_matrices() -> list[str]` — check dimensions, normalization, etc.

### GNNModelRunner (runner.py)

Before changing package execution, read [README.md](README.md#gnnmodelrunner-runnerpy)
for the public API and observation scope. The runner loads the exact
`model.gnn.md` source snapshot and delegates execution to
`runtime.inference.run_gnn_inference`; the same categorical kernel serves the
runtime and reverse matrix APIs.

Keep A[o,s], B[next,current,action], C[o], and D[s] authoritative.
Admission rejects missing/degraded matrices, invalid probability mass, and
workloads exceeding the declared limits. A rejected load clears the previously
loaded source; a rejected run clears its prior report.

Trace order is incoming prior, observation, posterior and its VFE, one-step
risk-plus-ambiguity policy scores, then the selected action's next belief.
The rollout takes modal predicted observations. Reports must identify this as
model inference and preserve source/matrix digests; they establish neither
measured source-program behavior nor globally optimal control.

When changing execution, exercise a complete exported package from a real
fixture repository, compare the labelled runner record against the shared
inference trace, and confirm that a non-stochastic exported matrix is rejected.
`tests/gnn_execution_fixture.py` supplies a complete numerical model for
Bayesian, action-selection, reset, report, and resource-admission controls.

### Example: Complete GNN Package Build

```python
from cogant.gnn import GNNPackageBuilder, GNNValidator

# Given: graph, state_space, process_model, mappings from earlier stages
builder = GNNPackageBuilder(
    graph=graph,
    state_space=state_space,
    process_model=process_model,
    mappings=semantic_mappings,
    config={"name": "flask_app", "version": "1.0.0"},
)

# Build package
result = builder.build("/tmp/gnn_package")
print(f"Created {result['file_count']} files")
print(f"Total size: {result['total_size_bytes']} bytes")
print(f"Files: {result['files']}")
# Output:
# Created 16 files
# Total size: 256000 bytes
# Files: ['manifest.json', 'model.gnn.md', 'state_space.json', ...]

# Validate
validator = GNNValidator()
validation = validator.validate_package("/tmp/gnn_package")
print(f"Valid: {validation.valid}")
print(f"Score: {validation.score}/100")
print(f"Section scores: {validation.section_scores}")
# Output:
# Valid: True
# Score: 100.0/100
# Section scores: {'metadata': 100, 'state_space': 100, 'matrices': 100, ...}

if validation.errors:
    for err in validation.errors:
        print(f"ERROR: {err}")
if validation.warnings:
    for warn in validation.warnings:
        print(f"WARNING: {warn}")
```

### Example: Execute Model and Trace Beliefs

```python
from cogant.gnn import GNNModelRunner

runner = GNNModelRunner()
runner.load_package("/tmp/gnn_package")

# Run for 10 steps
result = runner.run(steps=10)
print(f"Executed {len(result['traces'])} steps")

# Inspect traces
for trace in result["traces"][:3]:
    print(f"\nStep {trace['step']}:")
    print(f"  Incoming belief: {trace['state']}")
    print(f"  Action: {trace['action']}")
    print(f"  Observation: {trace['observation']}")
    print(f"  Posterior VFE: {trace['free_energy_after']:.4f}")
    print(f"  Posterior beliefs: {trace['beliefs']}")
    print(f"  Policy scores: {trace['policy_scores']}")

# Generate report
report = runner.generate_execution_report()
print(report)
```

### Example: Profile Model Performance

```python
from cogant.gnn import GNNModelRunner

runner = GNNModelRunner()
runner.load_package("/tmp/gnn_package")

# Run with profiling
traces, stats = runner.run_with_profiling(num_steps=100, num_trials=5)

print(f"Timing stats: {stats}")
print(f"Measured total elapsed time: {stats['total_ms']:.3f} ms")
```

## Integration with Downstream Stages

1. **Validation** (stage 8) — consumes GNN package; scores completeness and consistency
2. **Export** (stage 9) — renders to PDF, HTML, deployment bundles
3. **Simulation** — uses GNNModelRunner to instantiate and run agents
4. **Scoring** (stage 10) — compares bundles across versions for drift detection

## Responsibilities & Coordination

### Core Responsibilities
- Extract A, B, C, D matrices from state space and process model
- Write 16 required files plus diagrams/ and visualizations/ directories
- Format as human-readable markdown (19 sections) and machine-readable JSON
- Validate bundles against schema (0–100 scoring)
- Execute Active Inference update loops with Free Energy calculation
- Generate execution traces and reports
- Support incremental builds and caching

### Coordination
- **Input**: ProgramGraph, StateSpaceModel (from statespace/), ProcessModel (from process/), SemanticMappings (from translate/)
- **Output**: GNN Package (16 required files + diagrams/ + visualizations/), ExecutionTrace (from runner), ValidationResult (from validator)
- **Consumed by**: ValidationReport (stage 8), Export (stage 9), Scoring (stage 10), downstream simulators
- **Configuration**: schema_name, package_version, config dict (custom metadata)
- **No mutable state**: Packages are write-once; bundles are immutable after creation

### Additional (non-required) generated files
- `diagrams/` — Mermaid diagrams (class, state, sequence, dependency, active-inference)
- `visualizations/` — HTML charts (dashboard, node/edge distribution, confidence)
- `program_graph.json` — typed graph sidecar for downstream rasterizers
- `process_model.json` — process model sidecar for Gantt rendering

## How to Extend

### Add New Matrix Type
1. Extend `GNNMatrices` with new `compute_X_matrix()` method
2. Update `GNNValidator.CANONICAL_SECTIONS` (currently 19 sections) to require new section
3. Add JSON export format in `GNNJSONExporter`
4. Document in markdown formatter

### Support New Active Inference Schemas
1. Create variant of `GNNPackageBuilder` for new schema
2. Add new state-action encoding in `compute_B_matrix()`
3. Update markdown sections for schema-specific details
4. Register in CLI (cogant gnn build --schema=<name>)

### Extend Validation Rules
1. Add new check method to `GNNValidator`
2. Update `CANONICAL_SECTIONS` (19 sections) or `REQUIRED_FILES` (16 files)
3. Adjust scoring weights if needed
4. Test on fixtures to ensure all pass 100/100

### Add Visualization Types
1. Create renderer in `gnn/visualizations/`
2. Register in `GNNPackageBuilder.build()`
3. Call renderer from `build()` method
4. Update manifest.json to reference new files

## Error Handling & Diagnostics

**GNNPackageBuilder:**
- File write errors → exception with context (dir not writable, disk full, etc.)
- Matrix computation errors → logged, fallback matrices generated with DegradedOutput flag
- Missing inputs → validation error before building

**GNNValidator:**
- Missing files → errors list
- JSON parse errors → logged with file path and line number
- Section check failures → warning (non-blocking)
- Placeholder best-effort artifacts (`manifest.artifact_status` not `"success"`, or a `markov_blanket.json` stub with `metadata.status: "unavailable"`) → warning per artifact; status map in `details["artifact_status"]`
- Confidence aggregation failures → score defaults to 0.0 for that component

**GNNModelRunner:**
- Package load failures → exception with diagnostics
- Invalid inference input → exception with diagnostics; the previous successful report is cleared
- Invalid or non-finite matrix values → rejected at admission
- Profiling → measures complete runs with a combined work budget and fresh D for each trial

## See Also

- `py/cogant/gnn/README.md` — module-level overview
- `py/cogant/statespace/` — produces StateSpaceModel consumed by gnn/
- `py/cogant/process/` — produces ProcessModel consumed by gnn/
- `py/cogant/validate/` — validates GNN packages
- `py/cogant/export/` — renders packages to PDF, HTML, deployment formats
- `py/cogant/runtime/` — shared categorical kernel and versioned inference artifacts
