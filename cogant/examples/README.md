# Examples — Demo Repositories and Usage Patterns

Example repositories and scripts demonstrating COGANT usage.

Authoritative CLI list: [docs/cli_reference.md](../docs/cli_reference.md) (same as `cogant --help`).

## Contents

- **control_positive/** — Hand-crafted fixtures that are known to produce non-empty mappings, state spaces, and GNN packages. The canonical smoke trio is `calculator/`, `flask_mini/`, and `event_pipeline/`; the expanded local corpus adds `cli_tool/`, `async_service/`, `data_pipeline/`, `plugin_architecture/`, `notebook_module/`, and `multi_package_workspace/` for shape-specific evidence.
- **thin_orchestrated/** — 30 numbered scripts (`01_*.py`–`30_*.py`): each pipeline stage in isolation (01–12) and higher-order workflows that stitch stages together (13–30). See `thin_orchestrated/README.md` for the full index.
- **python-service/** — Larger Python service fixture with tests (demo).
- **workflow-engine/** — Workflow engine fixture with complex control flow (demo).
- `example_pipeline.py` — Standalone script showing full pipeline usage via the public API.
- `orchestrate_roundtrip.py` — Full `RoundtripOrchestrator` demo covering ingest → statespace → export → validate.
- `run_diff.py` — Entry point for diff-based drift reporting across two bundles.
- `test_drift_metrics.py` — Driver for the drift metrics that accompany `run_diff.py`.
- `demo_notebook.ipynb` — End-to-end Jupyter notebook demo (see [Demo System](#demo-system) below).
- `demo_server.py` — Minimal REST server exposing the forward pipeline and `cogant explain` (see [Demo System](#demo-system) below).

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

The `control_positive/` fixtures are the primary local regression corpus: they
are small enough to run in tests and broad enough to exercise CLI tools, async
services, data pipelines, plugin registries, notebook-converted modules,
multi-package workspaces, and the original calculator / Flask / event fixtures.
Each fixture keeps a README with its intent and expected graph motifs. Golden
output lives under `tests/golden/`; network-dependent repositories remain
configuration-driven through `run_all.json`.

## Community examples

Users can contribute examples via pull request:
- Must be runnable and documented
- Should demonstrate specific COGANT features
- Reviewed for clarity and correctness

## Demo System

The `examples/` directory ships a self-contained demo system that exercises
the four user-facing surfaces of COGANT — the forward pipeline, Markov
blanket extraction, reverse synthesis, and per-node explain — against the
bundled `control_positive/calculator` fixture.

### `demo_notebook.ipynb` — Jupyter demo

A fully-rendered nbformat v4.5 notebook with seven code cells that walk
through the complete engine end-to-end:

| Cell | Topic | What it does |
| ---- | ----- | ------------ |
| 1    | Install / import / version | Imports COGANT and prints `__version__` plus the Rust backend flag. |
| 2    | Analyze calculator | Runs the static forward pipeline and reports graph node/edge counts plus role assignments. |
| 3    | Markov blanket | Runs `MarkovBlanketExtractor(strategy='auto')` and reports internal/sensory/active/external counts. |
| 4    | Reverse synthesis | Runs `verify_repo_roundtrip` — forward -> reverse -> forward — and prints the synthesized package layout. |
| 5    | Round-trip score | Breaks down the role-match score by multiset overlap per role. |
| 6    | `cogant explain` | Calls `explain_node` on `input_digit` and prints the fired rules and blanket role. |
| 7    | Summary table | Collects every metric from cells 2-6 into a single summary dict and prints it as both a table and JSON. |

**Launch the notebook** (from the repository root, so the editable install
is on `sys.path`):

```bash
# Make sure Jupyter is available; COGANT does not pin it as a runtime dep.
uv pip install jupyterlab
uv run jupyter lab examples/demo_notebook.ipynb
```

If you cannot install Jupyter, you can validate the notebook's code cells
directly with Python:

```bash
uv run python -c "
import json
nb = json.load(open('examples/demo_notebook.ipynb'))
ns = {}
for c in nb['cells']:
    if c['cell_type'] == 'code':
        exec(''.join(c['source']), ns)
"
```

### `demo_server.py` — REST server

A minimal single-threaded REST server over the in-process engine.

**Endpoints**

| Method | Path              | Purpose |
| ------ | ----------------- | ------- |
| GET    | `/health`         | Liveness probe. Returns `{"status": "ok", "version": "<cogant.__version__>"}`. |
| POST   | `/analyze`        | Body `{"repo_path": "..."}`. Runs the static forward pipeline and returns graph / mapping / Markov blanket summary. |
| GET    | `/explain/{node}` | Query `?repo_path=...`. Returns the `ExplainResult` JSON for `{node}`. |
| GET    | `/docs`           | Redirects to the COGANT / GNN documentation site. With FastAPI installed, the auto-generated OpenAPI UI is also available at `/docs`. |

The server prefers **FastAPI + uvicorn** when they are installed (so you
get the interactive OpenAPI docs at `/docs` for free). When they are not
available it falls back to the pure-stdlib `http.server`, so the demo is
runnable on any Python 3.10+ install without extra dependencies.

**Launch the server** (from the repository root):

```bash
# Default: bind 127.0.0.1:8080
uv run python examples/demo_server.py

# Custom host / port
uv run python examples/demo_server.py --host 0.0.0.0 --port 9000

# Force the stdlib fallback even when FastAPI is installed (handy for testing)
uv run python examples/demo_server.py --force-stdlib
```

**Smoke test with curl**:

```bash
curl -s localhost:8080/health

curl -s -X POST localhost:8080/analyze \
    -H 'content-type: application/json' \
    -d '{"repo_path": "examples/control_positive/calculator"}'

curl -s 'localhost:8080/explain/input_digit?repo_path=examples/control_positive/calculator'
```

### System requirements

- Python **>= 3.10** (the whole COGANT package is 3.10+).
- COGANT installed from the repo root via `uv sync` (editable install).
- The demo notebook uses only stdlib + COGANT; Jupyter is required **only**
  to render it interactively.
- The demo server uses only stdlib + COGANT by default; install
  `fastapi uvicorn` (optional) to get auto-generated OpenAPI docs.
- No network access is required at runtime — the server's `/docs` endpoint
  redirects to the COGANT documentation URL but the engine itself is
  fully in-process.
