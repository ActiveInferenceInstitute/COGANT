## Command index

`cogant --help` is the authoritative source. [`py/cogant/cli/main.py`](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/cogant/py/cogant/cli/main.py) currently registers 26 top-level commands directly on the Typer app, plus `plugin` and `migrate` sub-typers for 29 leaf commands total.

| Command | Purpose |
|---------|---------|
| `init` | Initialize a new COGANT project (guided first-time setup; optional `--check`, `--run`). |
| `doctor` | Diagnose the COGANT runtime environment (Python, deps, Rust backend, tree-sitter, git). |
| `scan` | Scan a repository and print a quick summary (table or JSON). |
| `extract-static` | Run static analysis only (AST, type inference, symbol tables). |
| `extract-dynamic` | Run dynamic analysis (coverage databases, runtime traces). |
| `graph` | Build and summarise the program dependency graph. |
| `translate` | Full pipeline: ingest → static → normalize → graph → dynamic → translate → statespace → process → export → validate. |
| `analyze` | Canonical pipeline entry point with first-class `--incremental <git-ref>` support and incremental cache. |
| `statespace` | Compile an Active Inference state-space model (S, O, A, π). |
| `process` | Extract the pipeline / execution process model from a repository. |
| `export-gnn` | Re-export a previously generated GNN bundle in a different format (`all`, `markdown`, `json`). |
| `render` | Render an interactive HTML site from a bundle. |
| `viz` | Rasterize every Mermaid / SVG / dot / network artifact under a run directory to PNG. |
| `validate` | Validate a bundle JSON, a run directory, or a `gnn_package/` (runs `GNNValidator`). |
| `diff` | Compare two bundles or output directories and report drift (full markdown drift report for directories). |
| `changed` | List files changed since a git ref (incremental analysis helper). |
| `explain` | Explain *why* a node was assigned its Active Inference role. |
| `benchmark` | Benchmark pipeline wall-clock performance over several runs. |
| `analyze-static` | Run only the static-analysis stages and report findings. |
| `analyze-graph` | Run the graph-construction stage and print adjacency summary. |
| `visualize` | Render interactive SVG/HTML visualizations of program graph and matrices. |
| `export` | Export a GNN bundle to a specified format (`json`, `jsonl`, `parquet`, `graphml`). |
| `reverse` | Synthesize a Python package from a GNN markdown file. |
| `roundtrip` | Verify forward-reverse-forward round-trip isomorphism. |
| `version` | Print the COGANT version and exit. |
| `upstream-gnn` | Re-run the Active Inference Institute 25-step `src.gnn` pipeline on an existing `gnn_package/` directory. |
| `plugin` | Manage and inspect COGANT plugins (subcommands: `list`, `info`). |
| `migrate` | Migrate GNN files to the current schema version (single default leaf under the `migrate` sub-typer). |

See [Commands](commands.md) for full per-command argument and flag documentation.
