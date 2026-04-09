# Agents — py/cogant/scoring

## Owner
Drift and Quality Metrics Lead

## Responsibilities
Analyze architectural and semantic drift between bundles. Compare program graphs, state spaces, mappings, and validation results. Compute comprehensive drift scores and quality metrics.

## Key Responsibilities
- Run DriftAnalyzer to compare baseline and current bundles
- Track node/edge additions, removals, and modifications
- Analyze semantic mapping changes
- Compute architectural and semantic churn scores
- Use CodebaseMetrics for complexity and coverage analysis

## How to Extend
Add new comparison metrics to DriftAnalyzer.analyze(). Create specialized scoring functions for specific change types. Extend CodebaseMetrics with new quality dimensions (maintainability, testability, etc.).

## Coordination
- Consumes: Bundle data from export/
- Produces: DriftScore and MetricsReport consumed by export/, reports
- Feeds: Results to validation and analysis pipelines
