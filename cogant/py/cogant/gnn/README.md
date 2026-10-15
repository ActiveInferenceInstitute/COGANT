# GNN — Model Package Building, Validation, and Active Inference Execution

Builds complete GNN model packages from program graphs, validates against 19 canonical sections, and executes Active Inference simulation with belief dynamics and policy evaluation.

## Core Classes

### GNNPackageBuilder (package.py)
Builds on-disk GNN package with 16 required files:
1. manifest.json — metadata, checksums, package version
2. model.gnn.md — canonical markdown with all 19 sections
3. model.gnn.json — machine-readable model representation
4. state_space.json — state variables, observations, actions, transitions
5. observations.json — observation modalities and likelihoods
6. actions.json — action space and effects
7. transitions.json — transition dynamics (generative model)
8. preferences.json — preferences and constraints
9. factors.json — factorization structure
10. provenance.json — full provenance chain
11. ontology.json — ontology mappings
12. actions_policies.json — policy definitions
13. connections.json — factor graph connections
14. preferences_constraints.json — detailed constraints
15. markov_blanket.json — Active Inference Markov blanket partition
16. markov_network.json — collapsed four-role aggregate network

Constructor takes graph: ProgramGraph, state_space: StateSpaceModel, process_model: ProcessModel, mappings: Dict, optional config. build(output_dir: str) -> dict generates all files and returns manifest.

### GNNValidator (validator.py)
Validates GNN packages and scores 0-100. Checks:
- All 16 required files present
- JSON valid and well-formed
- Markdown has all 19 canonical sections in order:
  1. model_metadata — name, version, author, description
  2. repository_metadata — url, branch, last_commit, documentation
  3. source_coverage — lines analyzed, files covered, test coverage
  4. state_space — state variables and structure
  5. observation_modalities — sensor types and distributions
  6. actions_policies — action space and policies
  7. program_graph_connections — graph structure and dependencies
  8. factors — factorization and conditional independence
  9. transition_structure — state dynamics
  10. likelihood_structure — observation model
  11. preferences_constraints — objectives and constraints
  12. time_settings — discrete/continuous time, step size
  13. parameterization — learned vs. fixed parameters
  14. ontology_mapping — semantic alignments
  15. markov_blanket — Active Inference boundary partition
  16. provenance — evidence sources and confidence
  17. confidence — confidence tiers and scores
  18. rendering_hints — visualization preferences
  19. validation_notes — known issues, caveats, recommendations
- No orphan references, checksums match, provenance complete

Method validate_package(package_dir: str, *, upstream_gnn: bool | None = None) -> ValidationResult. ValidationResult has valid: bool, score: float (0-100), errors: List[str], warnings: List[str]. Upstream `gnn.validate_gnn_syntax` runs only for `upstream_gnn=True`, or for `upstream_gnn=None` when `COGANT_ENABLE_UPSTREAM_GNN` is truthy (see [`AGENTS.md`](AGENTS.md)).

### GNNModelRunner (runner.py)
Loads the complete A/B/C/D matrices from `model.gnn.md` and executes the shared
categorical inference kernel. Missing, malformed, or degraded matrices fail
before execution. Every run starts from D, filters the current belief through A,
scores one-step policies by risk plus ambiguity, and predicts the next belief
through the selected B slice.

ExecutionTrace records each step with:
- step: int
- state: incoming belief; action and observation: declared axis labels
- beliefs: Dict[str, float] — posterior over hidden states
- beliefs_prior: Dict[str, float] — prior before update
- free_energy_after — posterior VFE evaluated against the incoming prior
- policy_scores: List[Tuple[str, float]] — (action, efe_score) for each candidate
- predicted_state: Dict — next belief after applying B

`GNNModelRunner().load_package(package_dir)` admits a source snapshot.
`run(steps=10)` returns JSON-ready records, source and matrix SHA256 identities,
action counts, and posterior VFE. Observations are deterministic modes of the
predicted observation distribution; this is a model rollout, not measured
program execution. It does not establish globally optimal control or the
behavioral adequacy of source-to-model extraction. For externally supplied
observations use `cogant.runtime.inference.run_gnn_inference` with
`InferenceOptions(observations=..., steps=...)`.

`run_with_profiling(num_steps=10, num_trials=1)` returns records annotated by
trial and measured total elapsed milliseconds. Each trial restarts from D.
Counts must be positive integers; each run and the combined profiling workload
are bounded to 10,000 steps, with additional matrix-work admission limits.

### GNNMarkdownFormatter (formatter.py)
Formats GNN markdown with all 19 canonical sections in order. Outputs human-readable GNN markdown suitable for documentation and review.

### GNNJSONExporter (json_export.py)
Exports to machine-readable JSON. Produces JSON files for state_space, observations, actions, transitions, preferences, factors, provenance, ontology for programmatic access and downstream tools.

## Data Model

### 19 Canonical Sections
All GNN packages must include these sections in order (validator.py CANONICAL_SECTIONS):
1. model_metadata — name, version, author, created_at, updated_at
2. repository_metadata — repository_url, branch, commit_hash, documentation_url
3. source_coverage — lines_analyzed, files_covered, test_coverage_percent
4. state_space — state variables and structure
5. observation_modalities — observation_variables, modality_types, likelihood_parameters
6. actions_policies — action_variables, policy_rules, policy_parameters
7. program_graph_connections — factor graph structure, conditional dependencies
8. factors — factor types, scope (which variables), parameterization
9. transition_structure — state dynamics, generative model
10. likelihood_structure — P(obs|state), observation model
11. preferences_constraints — utility functions, hard constraints
12. time_settings — time_model, step_size, horizon
13. parameterization — learned_parameters, fixed_parameters, priors
14. ontology_mapping — semantic_mappings, ontology_references
15. markov_blanket — Active Inference boundary partition (internal/sensory/active/external)
16. provenance — evidence_sources, confidence_metadata, provenance_records
17. confidence — confidence_scores, confidence_tiers
18. rendering_hints — visualization_hints, diagram_types
19. validation_notes — known_issues, caveats, recommendations

## Usage

```python
from cogant.gnn import GNNPackageBuilder, GNNValidator, GNNModelRunner

# Build package
builder = GNNPackageBuilder(
    graph=program_graph,
    state_space=state_space_model,
    process_model=process_model,
    mappings=semantic_mappings,
    config={"author": "alice", "version": "1.0.0"},
)
manifest = builder.build("/path/to/output")

# Validate package
validator = GNNValidator()
result = validator.validate_package("/path/to/output")
print(f"Valid: {result.valid}, Score: {result.score}/100")
if result.errors:
    print("Errors:", result.errors)

# Run Active Inference simulation
runner = GNNModelRunner()
runner.load_package("/path/to/output")
execution = runner.run(steps=100)
for trace in execution["traces"]:
    print(
        f"Step {trace['step']}: action={trace['action']}, "
        f"posterior VFE={trace['free_energy_after']}"
    )
```

## Dependencies
- schemas/ — ProgramGraph, StateSpaceModel, ProcessModel, SemanticMapping
- gnn_export (internal) — 19 canonical section schemas
- runtime/ — shared categorical Bayesian filtering and one-step EFE
- Optional: the Active Inference Institute `generalized-notation-notation` package (`cogant[upstream]` extra, GNN 4.1.0 release line, import package `gnn`), reached only through [`upstream_bridge/`](upstream_bridge/README.md). Core GNN building, validation, and execution do not require it.
