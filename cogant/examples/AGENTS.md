# Agents — examples/

## Owner
Frontend Lead

## Responsibilities
- Example repository curation and maintenance
- Documentation and usage patterns
- Test fixtures for golden tests
- Community-facing showcase

## Coordination
- Example READMEs and shell snippets must match `cogant --help` (see [docs/CLI_GUIDE.md](../docs/CLI_GUIDE.md)); avoid documenting removed commands (`analyze`, `visualize`, `plugins` unless implemented).
- Examples must be runnable and up-to-date
- Updated when API changes
- Double as test fixtures for integration tests

## Files
- control_positive/ — Three regression fixtures (`calculator/`, `flask_mini/`, `event_pipeline/`) guaranteed to produce non-empty mappings and GNN packages; the primary corpus for thin examples and integration tests.
- thin_orchestrated/ — 20 stage-isolation and higher-order demo scripts with a shared `_common.py` helper. See `thin_orchestrated/README.md`.
- python-service/ — Larger Python service example.
- workflow-engine/ — Workflow engine example.
- example_pipeline.py — Standalone pipeline example script.
- orchestrate_roundtrip.py — Full `RoundtripOrchestrator` demo.
- run_diff.py — Diff/drift-report entry point.
- test_drift_metrics.py — Driver for the drift metrics next to `run_diff.py`.
