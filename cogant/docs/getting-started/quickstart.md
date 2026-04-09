# Quick Start

This page walks through a minimal end-to-end COGANT run: translate a repository, validate the bundle, and explain a single node.

## 1. Translate a repository

```bash
cogant translate ./my_repo --output output/ --layout-output
```

This runs the full pipeline: **ingest → static → normalize → graph → translate → statespace → process → export → validate**. The `--layout-output` flag reorganizes the results into `data/`, `diagrams/`, `site/`, `reports/`, and `figures/` subdirectories so the output tree is easy to browse.

Skip dynamic enrichment (coverage + trace) when you have no runtime data:

```bash
cogant translate ./my_repo --output output/ --no-dynamic
```

## 2. Validate the bundle

```bash
cogant validate output/
```

Validation accepts either a `bundle.json` file, a run directory, or a `gnn_package/` directory. For GNN packages it runs the full `GNNValidator` and prints a 0–100 score plus an error/warning table.

## 3. Explain a node

```bash
cogant explain ./my_repo my_function
```

`explain` runs the minimal pipeline (ingest + static + normalize + graph + translate), resolves `my_function` against the program graph with exact-then-substring matching, asks every translation rule to explain its decision, and prints:

- the assigned Active Inference role (HIDDEN_STATE, OBSERVATION, ACTION, POLICY, ...);
- which rules fired, in priority order, with evidence;
- which rules were considered but did not fire, with reasons;
- the Markov blanket role (mu / s / a / eta) with a one-line rationale.

## Python API

Same pipeline, programmatic entry points:

```python
from pathlib import Path
from cogant import PipelineRunner, Session
from cogant.api.pipeline import PipelineConfig

# Option A: ergonomic path-based session
session = Session(
    workspace="/tmp/cogant-workspace",
    repo_path=Path("path/to/repo"),
)
session.build_graph()
session.export_all("output/session", layout=True)

# Option B: full pipeline runner (same orchestration as the CLI)
runner = PipelineRunner()
config = PipelineConfig(output_dir="output/pipeline", layout_output=True)
bundle = runner.run(str(Path("path/to/repo").resolve()), config)

print(bundle.repo_summary())
print(bundle.program_graph().get("statistics", {}))
bundle.save_json("output/bundle.json")
```

See the [CLI Reference](../cli_reference.md) for every subcommand and the [API Reference](../api/translate.md) for module-level docs.
