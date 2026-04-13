# Agents — py/cogant/scoring

## Owner
Drift Detection & Quality Metrics

## What Is the Scoring Module

The `scoring/` module performs **architectural and semantic drift analysis** between program bundles across pipeline runs. It is stage 10 of the 10-stage COGANT pipeline. Given two snapshots (baseline and current) of program graphs, state spaces, semantic mappings, and validation results, this module:

1. **Compares Structure** — detects added/removed/modified nodes, edges, variables, factors
2. **Analyzes Semantic Drift** — measures changes in semantic mappings and role assignments
3. **Computes Quality Metrics** — tracks complexity, coupling, cohesion, observability, controllability
4. **Generates Reports** — produces drift scores, diff diffs, and trend analysis

Drift scoring is **critical for understanding program evolution** and catching regressions: a large drift may indicate refactoring, feature addition, or unexpected coupling explosion.

## Pipeline Integration

```
stage 9: export/            → Bundles (baseline and current)
    ↓
stage 10: scoring/          → DriftScore + CodebaseMetrics + Trends
                             → Drift reports + Mermaid diffs
                             → Quality gates (pass/fail)
```

The scoring module is the **final quality gate before deployment and release tracking**. All metrics feed into dashboards, CI/CD gates, and historical trend databases.

## Core Components

### DriftScore (drift.py)

Quantifies change magnitude across bundles.

**Fields:**
- `total_score` — [0.0, 100.0] composite drift; 0 = no change, 100 = complete rewrite
- `architectural_score` — [0.0, 100.0] structural drift (node/edge additions, removals, modifications)
- `semantic_churn_score` — [0.0, 100.0] semantic role changes (variable role flips, policy changes)
- `details` — `dict[str, Any]` with granular metrics:
  - `nodes_added`, `nodes_removed`, `nodes_modified` — counts
  - `edges_added`, `edges_removed`, `edges_modified` — counts
  - `variables_added`, `variables_removed`, `variables_modified` — counts
  - `variable_role_changes` — count of role flips (e.g., HIDDEN_STATE → OBSERVATION)
  - `action_set_changes` — count of added/removed actions
  - `policy_changes` — count of preference updates
  - `factor_structure_changes` — count of factor graph modifications
  - `matrix_delta` — change in matrix dimensions (ΔA_shape, ΔB_shape, etc.)
  - `complexity_delta` — change in cyclomatic/cognitive complexity
  - `coupling_delta` — change in instability/abstractness metrics
  - `coverage_delta` — change in validation coverage score
  - `confidence_delta` — change in average extraction confidence

**Scoring Algorithm:**
```
architectural_score = (
    0.3 * nodes_churn_ratio +          # (added + removed) / baseline_nodes
    0.3 * edges_churn_ratio +          # (added + removed) / baseline_edges
    0.2 * variable_churn_ratio +       # (added + removed) / baseline_variables
    0.2 * factor_structure_changes     # normalized by baseline_factors
)

semantic_churn_score = (
    0.4 * variable_role_change_ratio +
    0.3 * action_set_change_ratio +
    0.3 * policy_change_ratio
)

total_score = 0.6 * architectural_score + 0.4 * semantic_churn_score

# Clamp to [0.0, 100.0]
total_score = min(100.0, max(0.0, total_score * 100))
```

Higher scores indicate more significant change; threshold typically 20.0 to flag for review.

### DriftAnalyzer (drift.py)

Compares two bundles and computes drift scores.

**Key Methods:**
- `__init__(bundle_a, bundle_b)` — initialize with baseline and current bundles
- `analyze(bundle_a, bundle_b) -> DriftScore` — main entry; returns drift metrics
- `compute_structural_drift() -> dict[str, Any]` — node/edge/factor changes
- `compute_semantic_drift() -> dict[str, Any]` — role and mapping changes
- `compute_state_space_drift() -> dict[str, Any]` — variable and transition changes
- `compute_architectural_drift_score() -> float` — [0.0, 100.0] structural score
- `compute_semantic_churn_score() -> float` — [0.0, 100.0] semantic score
- `generate_diff_report() -> str` — human-readable diff summary
- `generate_diff_mermaid() -> str` — Mermaid diagram of changes
- `report(score) -> str` — formatted drift report with interpretation
- `to_dict() -> dict[str, Any]` — serialize to JSON-compatible dict

**Bundle Format:**
```python
bundle = {
    "id": "flask_app_20240413",
    "timestamp": "2024-04-13T10:30:00Z",
    "graph": {...},  # ProgramGraph as dict
    "state_space": {...},  # StateSpaceModel as dict
    "mappings": {...},  # SemanticMappings dict
    "validation_report": {...},  # ValidationReport as dict
    "gnn_package": {...},  # GNN bundle metadata
}
```

**Comparison Algorithm (pseudocode):**
```
1. Parse graph_a and graph_b into node/edge sets
   nodes_added = graph_b.nodes - graph_a.nodes
   nodes_removed = graph_a.nodes - graph_b.nodes
   nodes_modified = {(n_a, n_b) : match(n_a, n_b) ∧ n_a.attrs ≠ n_b.attrs}

2. Similarly for edges, variables, factors

3. For each variable in both bundles:
   if role(var_a) ≠ role(var_b):
       variable_role_changes += 1

4. Compute churn ratios and scores

5. Return DriftScore(...)
```

### CodebaseMetrics (metrics.py)

Tracks multi-dimensional quality metrics across bundles.

**MetricsReport** — NamedTuple holding summary metrics:
- `complexity_score` — [0.0, 100.0] inverse of average cyclomatic complexity
- `coupling_score` — [0.0, 100.0] inverse of module instability
- `cohesion_score` — [0.0, 100.0] factor graph cohesion
- `semantic_coverage` — [0.0, 100.0] % of nodes with semantic roles assigned
- `observability_score` — [0.0, 100.0] % of hidden variables observable
- `controllability_score` — [0.0, 100.0] % of hidden variables controllable
- `node_count`, `edge_count` — structural counts
- `state_var_count`, `observation_count`, `action_count` — state space dimensions

**CodebaseMetrics** — computes multi-dimensional quality:

**Key Methods:**
- `__init__(graph_dict, state_space_dict, mappings_dict)` — initialize from bundle dicts
- `complexity_score() -> float` — [0.0, 100.0] based on avg cyclomatic complexity
  - Formula: `100 - min(100, avg_cc * 10)` (lower complexity → higher score)
- `coupling_score() -> float` — [0.0, 100.0] based on instability metric
  - Formula: `100 * (1 - avg_instability)` (lower instability → higher score)
- `cohesion_score() -> float` — [0.0, 100.0] factor graph cohesion
  - Measures % of factors with high internal message consistency
- `semantic_coverage() -> float` — [0.0, 100.0] % of nodes with assigned roles
  - Formula: `100 * nodes_with_roles / total_nodes`
- `observability_score() -> float` — [0.0, 100.0] % of state variables observable
  - Formula: `100 * observable_vars / total_hidden_vars`
- `controllability_score() -> float` — [0.0, 100.0] % of state variables controllable
  - Formula: `100 * controllable_vars / total_hidden_vars`
- `summary() -> MetricsReport` — aggregate all scores
- `format_report() -> str` — human-readable markdown report
- `to_dict() -> dict[str, Any]` — serialize to JSON

**Scoring Philosophy:**
- **Complexity**: Favors simpler code (lower avg cyclomatic); threshold 10 CC is "high complexity"
- **Coupling**: Favors independent modules; threshold instability I > 0.8 is "unstable"
- **Cohesion**: Favors tightly-integrated factor groups
- **Coverage**: Favors comprehensive semantic analysis; threshold 90% is "good"
- **Observability**: Favors observable state; hidden variables without outputs are "unobservable"
- **Controllability**: Favors controllable state; variables not affected by any action are "uncontrollable"

All scores are normalized to [0.0, 100.0] for uniformity; composite quality score is typically the average.

## Data Representations

### Example: Drift Analysis Between Baseline and Current

```python
from cogant.scoring import DriftAnalyzer, CodebaseMetrics
import json

# Load two bundle snapshots
with open("baseline.json", "r") as f:
    bundle_a = json.load(f)
with open("current.json", "r") as f:
    bundle_b = json.load(f)

# Analyze drift
analyzer = DriftAnalyzer(bundle_a, bundle_b)
drift_score = analyzer.analyze(bundle_a, bundle_b)

print(f"=== Drift Analysis ===")
print(f"Total Score: {drift_score.total_score:.1f}/100")
print(f"Architectural: {drift_score.architectural_score:.1f}")
print(f"Semantic Churn: {drift_score.semantic_churn_score:.1f}")

print(f"\nDetailed Changes:")
print(f"  Nodes: +{drift_score.details['nodes_added']} -{drift_score.details['nodes_removed']} ~{drift_score.details['nodes_modified']}")
print(f"  Edges: +{drift_score.details['edges_added']} -{drift_score.details['edges_removed']} ~{drift_score.details['edges_modified']}")
print(f"  Variables: +{drift_score.details['variables_added']} -{drift_score.details['variables_removed']} ~{drift_score.details['variables_modified']}")
print(f"  Variable Role Changes: {drift_score.details['variable_role_changes']}")
print(f"  Action Set Changes: {drift_score.details['action_set_changes']}")
print(f"  Policy Changes: {drift_score.details['policy_changes']}")

print(f"\nMetrics Delta:")
print(f"  Complexity Δ: {drift_score.details['complexity_delta']:+.2f}")
print(f"  Coupling Δ: {drift_score.details['coupling_delta']:+.2f}")
print(f"  Coverage Δ: {drift_score.details['coverage_delta']:+.1%}")
print(f"  Confidence Δ: {drift_score.details['confidence_delta']:+.1%}")

# Generate human-readable report
report = analyzer.report(drift_score)
print(f"\n{report}")
# Output:
# DRIFT SUMMARY:
# Moderate drift detected (42.5/100). Consider review.
# Primary changes: variable role flips (5), policy updates (3).
# No new critical coupling discovered.

# Generate Mermaid diagram
mermaid = analyzer.generate_diff_mermaid()
print(mermaid)
# Output (Mermaid format):
# graph LR
#     A["Nodes: 47 → 52"] -->|+5| B["Added Nodes"]
#     A -->|-2| C["Removed Nodes"]
#     D["Edges: 102 → 118"] -->|+16| E["Added Edges"]
#     ...
```

### Example: Quality Metrics Analysis

```python
from cogant.scoring import CodebaseMetrics

# Compute metrics for current bundle
metrics = CodebaseMetrics(
    graph_dict=bundle["graph"],
    state_space_dict=bundle["state_space"],
    mappings_dict=bundle["mappings"]
)

# Individual scores
print(f"Complexity Score: {metrics.complexity_score():.1f}/100")
print(f"Coupling Score: {metrics.coupling_score():.1f}/100")
print(f"Cohesion Score: {metrics.cohesion_score():.1f}/100")
print(f"Semantic Coverage: {metrics.semantic_coverage():.1f}%")
print(f"Observability: {metrics.observability_score():.1f}%")
print(f"Controllability: {metrics.controllability_score():.1f}%")

# Summary report
report = metrics.summary()
print(f"\n{report}")
# Output:
# MetricsReport(
#   complexity_score=82.0,
#   coupling_score=75.0,
#   cohesion_score=88.0,
#   semantic_coverage=96.5,
#   observability_score=91.0,
#   controllability_score=85.0,
#   node_count=52,
#   edge_count=118,
#   state_var_count=23,
#   observation_count=15,
#   action_count=12
# )

# Formatted report
formatted = metrics.format_report()
print(formatted)
# Output (markdown):
# ## Code Quality Metrics
# | Dimension | Score | Status |
# |-----------|-------|--------|
# | Complexity | 82.0 | Good (avg CC ≤ 10) |
# | Coupling | 75.0 | Fair (I = 0.28) |
# | Cohesion | 88.0 | Good |
# | Semantic Coverage | 96.5% | Excellent |
# | Observability | 91.0% | Good |
# | Controllability | 85.0% | Good |
```

### Example: Comparative Analysis (Baseline → Current)

```python
from cogant.scoring import CodebaseMetrics

# Metrics for baseline and current
metrics_a = CodebaseMetrics(bundle_a["graph"], bundle_a["state_space"], bundle_a["mappings"])
metrics_b = CodebaseMetrics(bundle_b["graph"], bundle_b["state_space"], bundle_b["mappings"])

summary_a = metrics_a.summary()
summary_b = metrics_b.summary()

print(f"=== Quality Trend Analysis ===")
print(f"Complexity: {summary_a.complexity_score:.1f} → {summary_b.complexity_score:.1f} ({summary_b.complexity_score - summary_a.complexity_score:+.1f})")
print(f"Coupling: {summary_a.coupling_score:.1f} → {summary_b.coupling_score:.1f} ({summary_b.coupling_score - summary_a.coupling_score:+.1f})")
print(f"Cohesion: {summary_a.cohesion_score:.1f} → {summary_b.cohesion_score:.1f} ({summary_b.cohesion_score - summary_a.cohesion_score:+.1f})")
print(f"Coverage: {summary_a.semantic_coverage:.1%} → {summary_b.semantic_coverage:.1%} ({summary_b.semantic_coverage - summary_a.semantic_coverage:+.1%})")

# Detect regressions
if summary_b.complexity_score < summary_a.complexity_score - 5.0:
    print("⚠ Complexity regression detected (> 5-point drop)")
if summary_b.coupling_score < summary_a.coupling_score - 10.0:
    print("⚠ Coupling degradation detected")
if summary_b.semantic_coverage < summary_a.semantic_coverage - 0.05:
    print("⚠ Coverage regression detected (> 5% drop)")
```

## Integration with Downstream Stages

1. **Export Pipelines** — skip bundles with drift_score > 50.0 or quality regression
2. **CI/CD Gates** — enforce max drift thresholds before merge
3. **Dashboards** — track drift and quality trends over time
4. **Release Notes** — include drift summary in deployment artifacts
5. **Historical Analysis** — feed into trend databases for capacity planning

## Responsibilities & Coordination

### Core Responsibilities
- Compare program graphs, state spaces, and semantic mappings across bundle versions
- Detect and quantify structural changes (node/edge/factor additions, removals, modifications)
- Analyze semantic drift (variable role changes, policy updates, action set evolution)
- Compute multi-dimensional quality metrics (complexity, coupling, cohesion, coverage, observability, controllability)
- Generate drift scores and quality reports
- Support trend analysis and regression detection
- Produce human-readable reports and Mermaid diagrams

### Coordination
- **Input**: Two bundles (baseline and current) with graphs, state spaces, mappings, validation results
- **Output**: DriftScore, CodebaseMetrics, trend reports, Mermaid diffs
- **Consumed by**: CI/CD gates, dashboards, release pipelines, trend databases
- **Configuration**: drift thresholds, quality gates, metric weights
- **No mutable state**: All analyses are pure functions; thread-safe

## How to Extend

### Add New Drift Dimension
1. Add new field to DriftScore.details
2. Implement comparison logic in `DriftAnalyzer.compute_X_drift()`
3. Update scoring formula in `compute_architectural_drift_score()` or `compute_semantic_churn_score()`
4. Test on fixtures and known diffs

### Add New Quality Metric
1. Create method in CodebaseMetrics: `def new_metric() -> float:`
2. Normalize to [0.0, 100.0]
3. Add to MetricsReport if part of summary
4. Update `format_report()` to include in markdown
5. Document scoring algorithm in docstring

### Support New Bundle Formats
1. Create parser for new bundle type
2. Implement conversion to standard dict format
3. Register in DriftAnalyzer.__init__()
4. Test with fixtures in new format

### Add Regression Detectors
1. Create rule function: `def detect_X_regression(metrics_a, metrics_b) -> bool:`
2. Add threshold parameters to config
3. Call from comparison workflows
4. Report findings in diff report

## Error Handling & Diagnostics

```python
try:
    drift_score = analyzer.analyze(bundle_a, bundle_b)
except Exception as e:
    logger.error(f"Drift analysis failed: {e}")
    # Return neutral score (0 drift) with error details
    return DriftScore(
        total_score=0.0,
        architectural_score=0.0,
        semantic_churn_score=0.0,
        details={"error": str(e), "recovery": "Bundles may be incompatible"}
    )
```

- Graph parsing errors → logged, bundles treated as incomparable
- Missing metrics → defaults to 0.0 for that dimension
- Incompatible bundle versions → flagged with clear message
- Floating-point overflow → clamped to valid range

## CI/CD Integration Example

```yaml
quality_gates:
  drift:
    max_total_score: 50.0
    max_architectural_score: 40.0
    max_semantic_churn_score: 30.0
    action: fail  # or warn
  
  metrics:
    min_complexity_score: 70.0
    min_coupling_score: 60.0
    min_semantic_coverage: 90.0
    min_observability: 80.0
    action: fail

  regressions:
    max_complexity_delta: -5.0
    max_coupling_delta: -10.0
    max_coverage_delta: -0.05
    action: warn  # warnings don't block merge

on_failure:
  comment_pr: true
  block_merge: true
  post_report: true
```

## See Also

- `py/cogant/scoring/README.md` — module-level overview
- `py/cogant/validate/` — produces ValidationReport consumed by scoring/
- `py/cogant/export/` — uses drift/quality scores for deployment decisions
- `py/cogant/gnn/validator.py` — GNN bundle validation (separate from drift scoring)
- **Metrics Background**: [Martin Metrics](https://en.wikipedia.org/wiki/Software_metrics#Coupling), [Cyclomatic Complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity)
