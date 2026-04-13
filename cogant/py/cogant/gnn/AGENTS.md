# Agents — py/cogant/gnn

## Owner
GNN Bundle & Model Execution

## What Is the GNN Module

The `gnn/` module produces **complete, self-contained Active Inference model bundles** and executes them. It is stages 7–9 of the 10-stage COGANT pipeline. Given a `ProgramGraph`, `StateSpaceModel`, `ProcessModel`, and semantic mappings, this module:

1. **Builds GNN Package** — writes 17+ files to disk (manifest, markdown, JSON, visualizations)
2. **Validates Bundle** — checks all 18 canonical sections present and well-formed; scores 0–100
3. **Executes Models** — runs Active Inference with Variational Free Energy (VFE) and Expected Free Energy (EFE)
4. **Exports Results** — markdown (human-readable) and JSON (machine-readable)

A GNN bundle is a **portable, reproducible artifact**: it contains all information needed to understand, validate, or instantiate the learned agent model — no external dependencies on the original source code.

## Pipeline Integration

```
stage 6: process/           → ProcessModel (factor graph + causal structure)
    ↓
stage 7: gnn/               → GNN Package (17+ files: model.gnn.md, matrices, state space, etc.)
    ↓
stage 8: validate/          → ValidationReport (structural correctness + confidence)
    ↓
stage 9: export/            → Final artifacts (PDFs, summaries, deployment bundles)
    ↓
stage 10: scoring/          → Drift detection + quality metrics
```

The GNN module is the **boundary between symbolic analysis and Active Inference simulation**. All model execution depends on the correctness of the GNN bundle.

## Core Components

### GNNPackageBuilder (package.py)

Orchestrates creation of a complete GNN package on disk.

**REQUIRED_FILES** — list of 17 canonical output files:
1. `manifest.json` — package metadata (version, timestamp, checksums)
2. `model.gnn.md` — human-readable canonical markdown
3. `model.gnn.json` — machine-readable metadata
4. `state_space.json` — variable definitions, cardinalities, factorization
5. `observations.json` — observation modalities (A matrix metadata)
6. `actions.json` — action definitions and effects
7. `transitions.json` — state evolution rules (B matrix)
8. `preferences.json` — goal structure (C matrix)
9. `factors.json` — factor graph from ProcessModel
10. `provenance.json` — evidence tracking and attribution
11. `ontology.json` — semantic mappings and symbol dictionary
12. `diagrams/` — directory with Mermaid diagrams
13. `visualizations/` — directory with PNG/SVG renders
14. `README.md` — package-level documentation
15. `METADATA.yaml` — full configuration snapshot
16. `checksums.json` — SHA256 hashes for integrity checking
17. `INDEX.json` — file inventory and cross-references

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
4. Generate 18 canonical markdown sections (see GNNValidator.CANONICAL_SECTIONS)
5. Export matrices as JSON with precision metadata
6. Render diagrams (state machine, factor graph, temporal ordering)
7. Compute SHA256 checksums for all files
8. Write manifest with version, timestamp, checksums
9. Return summary dict with file counts, sizes, and index

### GNNValidator (validator.py)

Scores GNN bundles 0–100 by checking structural completeness, consistency, and confidence.

**CANONICAL_SECTIONS** — 18 required markdown sections:
1. Model Metadata (title, version, author, timestamp)
2. Repository Metadata (source file, commit hash, branch)
3. Source Coverage (% of code analyzed, symbol count)
4. State Space (variable definitions, cardinality, factorization)
5. Observation Modalities (A matrix, likelihood structure)
6. Actions/Policies (controllable transitions, preconditions)
7. Connections (coupling matrix, information flow)
8. Factors (factor graph, message-passing structure)
9. Transition Structure (B matrix, state evolution)
10. Likelihood Structure (observation model, probability densities)
11. Preferences/Constraints (C and D matrices, goals)
12. Time Settings (synchrony regime, temporal ordering)
13. Parameterization (distribution parameters, learning rates)
14. Ontology Mapping (semantic roles, symbol dictionary)
15. Provenance (evidence tracking, confidence scores)
16. Confidence Scores (per-variable, per-matrix extraction confidence)
17. Rendering Hints (visualization preferences, layout hints)
18. Validation Notes (degraded outputs, known limitations)

**REQUIRED_FILES** — JSON/metadata files that must be present:
- manifest.json, state_space.json, observations.json, actions.json, transitions.json, preferences.json, factors.json, provenance.json, ontology.json, diagrams/*, visualizations/*

**ValidationResult** — NamedTuple holding validation outcome:
- `valid` — boolean; True iff no errors and all 18 sections present
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
- Section presence: 18 points if all sections present (1 point each)
- JSON validity: 10 points if all required JSON files parse
- Matrix consistency: 20 points if A/B/C/D are internally consistent
- Confidence average: 20 points based on avg extraction confidence
- Completeness: 20 points based on % of state space covered
- Provenance: 12 points based on evidence ratio
- **Final score = (weighted sum) / 100** clamped to [0.0, 100.0]

All 6 shipped fixtures (control_positive, flask_app, event_pipeline, etc.) score 100/100.

### GNNMarkdownFormatter (formatter.py)

Formats the 18 canonical sections into human-readable markdown.

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

Loads and executes GNN models via Active Inference update loops.

**ExecutionTrace** — single-step trace:
- `step` — episode step counter
- `state` — current hidden state values
- `action` — selected action ID
- `observation` — observed values
- `reward` — immediate reward
- `timestamp` — wall-clock time
- `beliefs` — posterior belief distribution (updated posterior)
- `beliefs_prior` — prior belief (before observation)
- `free_energy_before` — VFE before action selection
- `free_energy_after` — VFE after observation update
- `policy_scores` — `list[(action_id, score)]` ranking policies
- `action_rationale` — explanation of why action was selected
- `predicted_state` — state predicted before observation

**Key Methods:**
- `load_package(package_dir) -> dict[str, Any]` — load manifest and models
- `run(steps=10) -> dict[str, Any]` — execute Active Inference for N steps; returns trace history
- `run_with_profiling(num_steps=10, num_trials=1) -> (traces, stats)` — measure timing and performance
- `generate_execution_report(trace) -> str` — render execution trace as markdown

**Update Loop (pseudocode):**
```
For each step t:
  1. compute_posterior(observation_t, likelihood_A, prior_beliefs)
  2. beliefs_t ← posterior
  3. free_energy_t ← VFE(beliefs_t, A, B, D)
  4. for each policy π: efe_π ← compute_efe(π, beliefs, C, B)
  5. select_action(π*) = argmax_π [-EFE_π]
  6. predict_state(s_{t+1}) ← B[action, :] @ beliefs_t
  7. trace.append(ExecutionTrace(...))
  8. Observe(o_{t+1}) from environment/stochastic B
```

Requires `pymdp` library (optional dependency; graceful fallback if unavailable).

## Data Representations

### Example: Complete GNN Package Build

```python
from cogant.gnn import GNNPackageBuilder, GNNValidator

# Given: graph, state_space, process_model, mappings from earlier stages
builder = GNNPackageBuilder(
    graph=graph,
    state_space=state_space,
    process_model=process_model,
    mappings=semantic_mappings,
    config={"name": "flask_app", "version": "1.0.0"}
)

# Build package
result = builder.build("/tmp/gnn_package")
print(f"Created {result['file_count']} files")
print(f"Total size: {result['total_size_bytes']} bytes")
print(f"Files: {result['files']}")
# Output:
# Created 17 files
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
for trace in result['traces'][:3]:
    print(f"\nStep {trace.step}:")
    print(f"  State: {trace.state}")
    print(f"  Action: {trace.action}")
    print(f"  Observation: {trace.observation}")
    print(f"  Free Energy: {trace.free_energy_after:.4f}")
    print(f"  Beliefs: {trace.beliefs}")
    print(f"  Policy Scores: {trace.policy_scores}")

# Generate report
report = runner.generate_execution_report()
print(report)
# Output:
# ## Execution Report
# - Episodes: 1
# - Total steps: 10
# - Average free energy: 4.23
# - Action distribution: {send_request: 6, retry: 3, abort: 1}
```

### Example: Profile Model Performance

```python
from cogant.gnn import GNNModelRunner

runner = GNNModelRunner()
runner.load_package("/tmp/gnn_package")

# Run with profiling
traces, stats = runner.run_with_profiling(num_steps=100, num_trials=5)

print(f"Timing stats: {stats}")
# Output:
# {
#   'mean_step_time_ms': 12.5,
#   'total_time_ms': 1250.0,
#   'belief_update_time_ms': 4.2,
#   'policy_eval_time_ms': 6.8,
#   'action_selection_time_ms': 1.5,
#   'trials': 5
# }
```

## Integration with Downstream Stages

1. **Validation** (stage 8) — consumes GNN package; scores completeness and consistency
2. **Export** (stage 9) — renders to PDF, HTML, deployment bundles
3. **Simulation** — uses GNNModelRunner to instantiate and run agents
4. **Scoring** (stage 10) — compares bundles across versions for drift detection

## Responsibilities & Coordination

### Core Responsibilities
- Extract A, B, C, D matrices from state space and process model
- Write 17+ canonical files (manifest, markdown, JSON, visualizations)
- Format as human-readable markdown (18 sections) and machine-readable JSON
- Validate bundles against schema (0–100 scoring)
- Execute Active Inference update loops with Free Energy calculation
- Generate execution traces and reports
- Support incremental builds and caching

### Coordination
- **Input**: ProgramGraph, StateSpaceModel (from statespace/), ProcessModel (from process/), SemanticMappings (from translate/)
- **Output**: GNN Package (17+ files), ExecutionTrace (from runner), ValidationResult (from validator)
- **Consumed by**: ValidationReport (stage 8), Export (stage 9), Scoring (stage 10), downstream simulators
- **Configuration**: schema_name, package_version, config dict (custom metadata)
- **No mutable state**: Packages are write-once; bundles are immutable after creation

## How to Extend

### Add New Matrix Type
1. Extend `GNNMatrices` with new `compute_X_matrix()` method
2. Update `GNNValidator.CANONICAL_SECTIONS` to require new section
3. Add JSON export format in `GNNJSONExporter`
4. Document in markdown formatter

### Support New Active Inference Schemas
1. Create variant of `GNNPackageBuilder` for new schema
2. Add new state-action encoding in `compute_B_matrix()`
3. Update markdown sections for schema-specific details
4. Register in CLI (cogant gnn build --schema=<name>)

### Extend Validation Rules
1. Add new check method to `GNNValidator`
2. Update `CANONICAL_SECTIONS` or `REQUIRED_FILES`
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
- Confidence aggregation failures → score defaults to 0.0 for that component

**GNNModelRunner:**
- Package load failures → exception with diagnostics
- Belief update divergence → warning logged, traces recorded with NaN handling
- Free Energy calculation errors → fallback to deterministic policy selection

## See Also

- `py/cogant/gnn/README.md` — module-level overview
- `py/cogant/statespace/` — produces StateSpaceModel consumed by gnn/
- `py/cogant/process/` — produces ProcessModel consumed by gnn/
- `py/cogant/validate/` — validates GNN packages
- `py/cogant/export/` — renders packages to PDF, HTML, deployment formats
- `py/cogant/simulate/` — executes models using GNNModelRunner
