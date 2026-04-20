# Agents — examples/

## Owner
Frontend Lead

## Responsibilities
- Example repository curation and maintenance
- Documentation and usage patterns
- Test fixtures for golden tests
- Community-facing showcase

## Coordination
- Example READMEs and shell snippets must match `cogant --help` (see [docs/cli/README.md](../docs/cli/README.md)); all 26 CLI entries (`analyze`, `visualize`, `export`, etc.) are live — reference them freely.
- Examples must be runnable and up-to-date
- Updated when API changes
- Double as test fixtures for integration tests

## Files
- control_positive/ — Three regression fixtures (`calculator/`, `flask_mini/`, `event_pipeline/`) guaranteed to produce non-empty mappings and GNN packages; the primary corpus for thin examples and integration tests.
- thin_orchestrated/ — Stage-isolation and higher-order demo scripts with a shared `_common.py` helper. See [thin_orchestrated/README.md](thin_orchestrated/README.md).
- zoo/ — Numbered POMDP / Active Inference toy scenarios; see [zoo/README.md](zoo/README.md).
- plugins/ — Sample plugin packages; see [plugins/README.md](plugins/README.md).
- real_world/ — Small Flask / `requests` / stdlib JSON apps; see [real_world/README.md](real_world/README.md).
- calculator_js/ — Minimal JavaScript calculator for parser coverage; see [calculator_js/README.md](calculator_js/README.md).
- python-service/ — Larger Python service example.
- workflow-engine/ — Workflow engine example.
- example_pipeline.py — Standalone pipeline example script.
- orchestrate_roundtrip.py — Full `RoundtripOrchestrator` demo.
- run_diff.py — Diff/drift-report entry point.
- test_drift_metrics.py — Driver for the drift metrics next to `run_diff.py`.
