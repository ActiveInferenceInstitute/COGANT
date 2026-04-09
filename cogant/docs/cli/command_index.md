## Command index

Fourteen Typer subcommands are registered in [`py/cogant/cli/main.py`](../py/cogant/cli/main.py).

| Command | Purpose |
|---------|---------|
| `init` | Initialize a COGANT project directory / config |
| `scan` | Summarize repository (files, languages, layout) |
| `extract-static` | Run ingest + Python static analysis |
| `extract-dynamic` | Attach coverage / trace data to the graph |
| `graph` | Build or emit the program graph |
| `translate` | Run the full multi-stage pipeline |
| `statespace` | Compile state-space–oriented view |
| `process` | Extract process / workflow model |
| `export-gnn` | Emit GNN markdown/JSON (and related) from a bundle |
| `render` | Generate static HTML site from a bundle |
| `viz` | Rasterize `.mermaid`, `.svg`, `.dot`, etc. under a run directory to PNG |
| `validate` | Validate bundle JSON or a `gnn_package` directory (full GNN validator when applicable) |
| `diff` | Compare bundles or rich output directories (drift report) |
| `benchmark` | Time pipeline runs with configurable iterations |

