# Scoring

Analyzes architectural and semantic drift between bundles. Compares program graph structure, semantic mappings, state space modifications, process models, and validation results to compute comprehensive drift scores.

## API

DriftAnalyzer compares two bundles and computes drift metrics. Initialize with bundle_a (baseline) and bundle_b (current), then call analyze() to get a DriftScore. DriftScore contains total_score (0-1, higher = more drift), architectural_score, semantic_churn_score, and details dict.

CodebaseMetrics computes architectural quality metrics from graph, state space, and mappings. Produces MetricsReport with complexity_score, coupling_score, cohesion_score, semantic_coverage, observability_score, controllability_score, and element counts.

The module supports detailed change tracking: node additions/removals/modifications, edge changes, state variable evolution, observation changes, action changes, mapping changes, and validation drift.

## Usage

```python
from cogant.scoring import DriftAnalyzer

# Two bundles from different analysis runs
bundle_a = {"graph": {...}, "state_space": {...}, "mappings": {...}}
bundle_b = {"graph": {...}, "state_space": {...}, "mappings": {...}}

# Analyze drift
analyzer = DriftAnalyzer(bundle_a, bundle_b)
drift_score = analyzer.analyze()

print(f"Total drift: {drift_score.total_score}")
print(f"Architectural: {drift_score.architectural_score}")
print(f"Semantic churn: {drift_score.semantic_churn_score}")
print(f"Details: {drift_score.details}")
```
