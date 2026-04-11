# Recipe: Analyze a Flask App

**Goal:** Run the full COGANT pipeline against the canonical six-module Flask fixture and read the GNN bundle.

> This is a short, copy-pasteable recipe. For the full narrative — node and
> edge counts, role distribution tables, and per-module commentary — see
> [Tutorial 3: Flask walkthrough](../tutorials/03_flask_walkthrough.md) and
> the deep-dive in [`flask.md`](../tutorials/flask.md).

## Prerequisites

- COGANT installed (`uv sync` from a checkout, or `pip install cogant`).
- The repo's bundled fixture at `examples/real_world/flask_app/`. It contains
  six Python modules totalling 853 lines: `__init__.py`, `app.py`, `config.py`,
  `models.py`, `services.py`, `utils.py`.

## Step 1 — translate

```bash
uv run cogant translate examples/real_world/flask_app \
    --output output/flask_app \
    --layout-output
```

This runs the default `stages=["ingest", "static", "normalize", "graph",
"translate", "statespace", "process", "export", "validate"]` pipeline. Expect
a 100 / 100 validator score on a clean checkout.

## Step 2 — validate

```bash
uv run cogant validate output/flask_app/gnn_package
```

Expected output:

```text
GNN validation: output/flask_app/gnn_package
  Score:    100.0 / 100
  Errors:   0
  Warnings: 0
```

## Step 3 — read the bundle

The bundle directory `output/flask_app/gnn_package/` contains:

| File | What's in it |
| --- | --- |
| `model.gnn.md` | Canonical GNN markdown — human-readable role table. |
| `model.gnn.json` | Same content, machine-readable. |
| `A.json`, `B.json`, `C.json`, `D.json` | The four generative-model matrices. |
| `manifest.json` | Bundle metadata, validator score, edge / node counts. |

For a row-by-row walkthrough of `A.json`, `B.json`, `C.json`, `D.json`, see
[Tutorial 5: Reading the A / B / C / D matrices](../tutorials/05_gnn_interpretation.md).

## Step 4 — programmatic equivalent

The same pipeline through the Python API:

```python
from cogant import PipelineRunner
from cogant.api.pipeline import PipelineConfig

runner = PipelineRunner()
config = PipelineConfig(output_dir="output/flask_app")
bundle = runner.run("./examples/real_world/flask_app", config)

assert not bundle.errors
print(bundle.repo_summary())
bundle.save_json("output/flask_app/bundle.json")
```

## See also

- [Tutorial 3: Flask walkthrough](../tutorials/03_flask_walkthrough.md) — full narrative with commentary.
- [`docs/tutorials/flask.md`](../tutorials/flask.md) — canonical numeric breakdown (98 nodes, 597 edges).
- [`PipelineRunner` API](../api/pipelinerunner_api.md) — every option used above.
- [`docs/api/static.md`](../api/static.md) — what the static stage does to the six modules.
