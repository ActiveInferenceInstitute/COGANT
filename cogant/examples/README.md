# Examples — Demo Repositories and Usage Patterns

Example repositories and scripts demonstrating COGANT usage.

Authoritative CLI list: [docs/CLI_GUIDE.md](../docs/CLI_GUIDE.md) (same as `cogant --help`).

## Contents

- **control_positive/** — Three hand-crafted fixtures (`calculator/`, `flask_mini/`, `event_pipeline/`) that are known to produce non-empty mappings, state spaces, and GNN packages. These are the canonical "does the pipeline still work end-to-end" targets used by tests and examples.
- **thin_orchestrated/** — 20 minimal scripts demonstrating each pipeline stage in isolation (01-12) and higher-order workflows that stitch stages together (13-20). See `thin_orchestrated/README.md` for the full index.
- **python-service/** — Larger Python service fixture with tests (demo).
- **workflow-engine/** — Workflow engine fixture with complex control flow (demo).
- `example_pipeline.py` — Standalone script showing full pipeline usage via the public API.
- `orchestrate_roundtrip.py` — Full `RoundtripOrchestrator` demo covering ingest → statespace → export → validate.
- `run_diff.py` — Entry point for diff-based drift reporting across two bundles.
- `test_drift_metrics.py` — Driver for the drift metrics that accompany `run_diff.py`.

## Running examples

From the repository root:

```bash
# Python service: full pipeline; artifacts under the output directory
cogant translate examples/python-service --output output/python-service

# Workflow engine
cogant translate examples/workflow-engine --output output/workflow-engine

# Quick summary without full pipeline
cogant scan examples/python-service

# Using the standalone script
python examples/example_pipeline.py
```

After `translate`, expect files such as `program_graph.json` and `gnn_model.json` under each output directory (see export stage in the pipeline). Commands `cogant render` and `cogant validate` expect a **bundle-shaped JSON** (see CLI guide); use the Python API `Bundle.save_json()` or `example_pipeline.py` if you need those flows.

## Example structure

```
python-service/
├── src/
│   ├── __init__.py
│   ├── api.py
│   ├── models.py
│   └── services/
└── tests/
    ├── test_api.py
    └── test_services.py

workflow-engine/
├── src/
│   ├── __init__.py
│   ├── executor.py
│   ├── parser.py
│   └── state.py
└── tests/
```

## Maintained as test fixtures

The `control_positive/` fixtures (`calculator`, `flask_mini`, `event_pipeline`) are the primary regression corpus: they are small enough to run in tests and large enough to exercise every translation rule and GNN section. Fixtures update in lockstep with the translation-rule and state-space-compiler changes they are designed to pin. Golden output lives under `tests/golden/`.

## Community examples

Users can contribute examples via pull request:
- Must be runnable and documented
- Should demonstrate specific COGANT features
- Reviewed for clarity and correctness
