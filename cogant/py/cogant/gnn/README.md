# GNN — Model Package Building, Validation, and Active Inference Execution

Builds complete GNN model packages from program graphs, validates against 18 canonical sections, and executes Active Inference simulation with belief dynamics and policy evaluation.

## Core Classes

### GNNPackageBuilder (package.py)
Builds on-disk GNN package with 13+ required files:
1. manifest.json — metadata, checksums, package version
2. model.gnn.md — canonical markdown with all 18 sections
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

Constructor takes graph: ProgramGraph, state_space: StateSpaceModel, process_model: ProcessModel, mappings: Dict, optional config. build(output_dir: str) -> dict generates all files and returns manifest.

### GNNValidator (validator.py)
Validates GNN packages and scores 0-100. Checks:
- All 11 required files present
- JSON valid and well-formed
- Markdown has all 18 canonical sections in order:
  1. model_metadata — name, version, author, description
  2. repository_metadata — url, branch, last_commit, documentation
  3. source_coverage — lines analyzed, files covered, test coverage
  4. state_space — state variables and structure
  5. observation_modalities — sensor types and distributions
  6. actions_policies — action space and policies
  7. connections — graph structure and dependencies
  8. factors — factorization and conditional independence
  9. transition_structure — state dynamics
  10. likelihood_structure — observation model
  11. preferences_constraints — objectives and constraints
  12. time_settings — discrete/continuous time, step size
  13. parameterization — learned vs. fixed parameters
  14. ontology_mapping — semantic alignments
  15. provenance — evidence sources and confidence
  16. confidence — confidence tiers and scores
  17. rendering_hints — visualization preferences
  18. validation_notes — known issues, caveats, recommendations
- No orphan references, checksums match, provenance complete

Method validate_package(package_dir: str) -> ValidationResult. ValidationResult has valid: bool, score: float (0-100), errors: List[str], warnings: List[str].

### GNNModelRunner (runner.py)
Loads GNN package and executes Active Inference simulation. Maintains beliefs (probability distribution over hidden states) and performs Bayesian update on observation, then evaluates policies via Expected Free Energy (EFE) and selects action.

ExecutionTrace records each step with:
- step: int
- state, action, observation, reward
- beliefs: Dict[str, float] — posterior over hidden states
- beliefs_prior: Dict[str, float] — prior before update
- free_energy_before, free_energy_after — VFE before/after belief update
- policy_scores: List[Tuple[str, float]] — (action, efe_score) for each candidate
- action_rationale: str — why action was selected
- predicted_state: Dict — predicted next state

GNNModelRunner(package_dir: str) loads package. run(observations: List, num_steps: int, policies: Optional[List]) -> List[ExecutionTrace] executes simulation and returns trace.

### GNNMarkdownFormatter (formatter.py)
Formats GNN markdown with all 18 canonical sections in order. Outputs human-readable GNN markdown suitable for documentation and review.

### GNNJSONExporter (json_export.py)
Exports to machine-readable JSON. Produces JSON files for state_space, observations, actions, transitions, preferences, factors, provenance, ontology for programmatic access and downstream tools.

## Data Model

### 18 Canonical Sections
All GNN packages must include these sections in order (gnn_export.py):
1. GNNMetadata — name, version, author, created_at, updated_at
2. RepositoryMetadata — repository_url, branch, commit_hash, documentation_url
3. SourceCoverage — lines_analyzed, files_covered, test_coverage_percent
4. GraphSection — nodes, edges, adjacency structure
5. ObservationModalitySection — observation_variables, modality_types, likelihood_parameters
6. ActionPolicySection — action_variables, policy_rules, policy_parameters
7. ConnectionSection — factor graph structure, conditional dependencies
8. FactorSection — factor types, scope (which variables), parameterization
9. TransitionStructureSection — state dynamics, generative model
10. LikelihoodStructureSection — P(obs|state), observation model
11. PreferenceConstraintSection — utility functions, hard constraints
12. TimeSettingSection — time_model, step_size, horizon
13. ParameterizationSection — learned_parameters, fixed_parameters, priors
14. OntologyMappingSection — semantic_mappings, ontology_references
15. ProvenanceSection — evidence_sources, confidence_metadata, provenance_records
16. ConfidenceSection — confidence_scores, confidence_tiers
17. RenderingHints — visualization_hints, diagram_types
18. ValidationNotes — known_issues, caveats, recommendations

## Usage

```python
from cogant.gnn import GNNPackageBuilder, GNNValidator, GNNModelRunner

# Build package
builder = GNNPackageBuilder(
    graph=program_graph,
    state_space=state_space_model,
    process_model=process_model,
    mappings=semantic_mappings,
    config={"author": "alice", "version": "1.0.0"}
)
manifest = builder.build("/path/to/output")

# Validate package
validator = GNNValidator()
result = validator.validate_package("/path/to/output")
print(f"Valid: {result.valid}, Score: {result.score}/100")
if result.errors:
    print("Errors:", result.errors)

# Run Active Inference simulation
runner = GNNModelRunner("/path/to/output")
observations = [{"sensor_1": 0.5, "sensor_2": 0.3}, ...]
traces = runner.run(observations, num_steps=100)
for trace in traces:
    print(f"Step {trace.step}: action={trace.action}, reward={trace.reward}, free_energy={trace.free_energy_after}")
```

## Dependencies
- schemas/ — ProgramGraph, StateSpaceModel, ProcessModel, SemanticMapping
- gnn_export (internal) — 18 canonical section schemas
- simulate/ — CategoricalDistribution, FreeEnergyCalculator (Active Inference)
