## Commands

### init

Initialize a new COGANT project with configuration.

```bash
cogant init <path>
cogant init my_project
cogant init my_project --quiet
```

**Options:**
- `--quiet, -q`: Minimal output

### scan

Scan a repository and display summary information.

```bash
cogant scan <target>
cogant scan ./my_repo
cogant scan ./my_repo --format json
```

**Arguments:**
- `target`: Path to repository (default: current directory)

**Options:**
- `--format, -f`: Output format: `table` (default) or `json`

**Table columns:** ingest file count, Python modules parsed, symbol summary (the static stage uses module lists rather than legacy empty AST `nodes`/`edges` placeholders).

### extract-static

Extract static analysis (AST, types, symbols).

```bash
cogant extract-static <target>
cogant extract-static ./my_repo
cogant extract-static ./my_repo --output ./exports
```

**Arguments:**
- `target`: Path to repository

**Options:**
- `--output, -o`: Output **directory** for JSON artifacts. When set, runs the full export path (graph/GNN/state space) into that directory; omit for a short summary panel (modules parsed and symbols).

### extract-dynamic

Extract dynamic analysis (traces, coverage).

```bash
cogant extract-dynamic <target>
cogant extract-dynamic ./my_repo
cogant extract-dynamic ./my_repo --traces trace.json
```

**Arguments:**
- `target`: Path to repository

**Options:**
- `--traces, -t`: Path to trace file

### graph

Build program dependency graph.

```bash
cogant graph <target>
cogant graph ./my_repo
cogant graph ./my_repo --output graph.json
```

**Arguments:**
- `target`: Path to repository

**Options:**
- `--output, -o`: Reserved for future file export; graph counts are printed to the panel.

### translate

Run the full pipeline translation from code to GNN.

```bash
cogant translate <target>
cogant translate ./my_repo
cogant translate ./my_repo --output output/ --skip ingest,export
```

**Arguments:**
- `target`: Path to repository (default: current directory)

**Options:**
- `--config, -c`: Configuration file path
- `--skip`: Comma-separated stages to skip (whitespace around names is trimmed)
- `--output, -o`: Output directory (default: `output`)

**Artifacts:** Writes **`bundle.json`** in the output directory (full pipeline `Bundle` snapshot for `cogant render` / `cogant validate`) plus stage exports from the `export` stage when run.

**Stages:** ingest, static, normalize, graph, translate, statespace, process, export, validate

### statespace

Compile semantic state space model.

```bash
cogant statespace <target>
cogant statespace ./my_repo
cogant statespace ./my_repo --output statespace.json
```

**Arguments:**
- `target`: Path to repository

**Options:**
- `--output, -o`: Output file

### process

Extract process/execution model.

```bash
cogant process <target>
cogant process ./my_repo
```

**Arguments:**
- `target`: Path to repository

### export-gnn

Export GNN bundle in various formats.

```bash
cogant export-gnn <bundle_path>
cogant export-gnn output/bundle.json
cogant export-gnn output/bundle.json --format all --output exports/
```

**Arguments:**
- `bundle_path`: Path to bundle JSON file

**Options:**
- `--output, -o`: Output directory
- `--format, -f`: Export format: `all` (default), `markdown`, `json`

### render

Generate interactive HTML site from bundle.

```bash
cogant render <bundle_path>
cogant render output/bundle.json
cogant render output/bundle.json --output html_site/
```

**Arguments:**
- `bundle_path`: Path to bundle JSON file

**Options:**
- `--output, -o`: Output directory

Creates:
- `index.html` - Overview page
- `graph/program_graph.html` - Interactive graph visualization
- `models/state_space.html` - State space visualization
- `models/process.html` - Process model Gantt chart
- `provenance/` - Lineage inspector
- `assets/` - CSS, JavaScript, data files

### viz

Rasterize diagram and graph artifacts under a pipeline output directory to PNG files.

```bash
cogant viz <run_dir>
cogant viz output/my_repo_run/
```

**Arguments:**

- `run_dir`: Directory containing `program_graph.json`, `.mermaid`, `.dot`, `.svg`, or other assets produced by analysis (walks recursively).

Uses [`cogant.viz.png_export.render_all_pngs`](../py/cogant/viz/png_export.py). Safe to re-run; overwrites existing PNGs.

### validate

Run validation checks on a bundle file or on a directory (run output, `gnn_package`, or hybrid). Implementation: [`py/cogant/cli/main.py`](../py/cogant/cli/main.py).

```bash
cogant validate <bundle_or_dir>
cogant validate output/bundle.json
cogant validate output/run_dir/                 # see routing table below
cogant validate output/gnn_package/            # directory that *is* a package
```

**Routing** (first match wins):

| Input | Behavior |
|-------|----------|
| **File** (e.g. `…/bundle.json`) | Lightweight JSON checks: `target`, `artifacts`, `stage_results`, empty `errors`. |
| **Directory** whose path **is** a GNN package (`manifest.json` + `model.gnn.md` at that path) | Full [`GNNValidator`](../py/cogant/gnn/validator.py): score, errors, warnings (18-section contract). |
| **Directory** containing `gnn_package/manifest.json` | Same GNN validator on `…/gnn_package/`. |
| **Directory** with **`bundle.json`** but no resolvable GNN package above | Same lightweight checks on `dir/bundle.json` (run-directory fallback). |
| **Directory** with neither `gnn_package/` nor `bundle.json` | Exit **2** with an error message. |

**Exit codes:** **0** — checks passed (bundle) or GNN package `valid`; **1** — bundle checks failed or GNN package invalid; **2** — path not found, or unusable directory layout.

**Bundle JSON checks** (file or `dir/bundle.json`):

- Bundle has `target`
- Bundle has `artifacts`
- Bundle has `stage_results`
- No entries in `errors`

**GNN package path:** prints validation score, errors, and warnings from the 18-section contract.

**Troubleshooting:** Validating a **run directory** after `cogant translate` expects `gnn_package/` once the export stage built it (requires program graph, state-space model, process model, and semantic mappings dict on the bundle). If `gnn_package/` is missing, inspect `bundle.json` / stage artifacts for `export_warnings` and see [SPEC § Implementation status](../reference/README.md).

### diff

Compare two bundles and show differences.

```bash
cogant diff <bundle1> <bundle2>
cogant diff output/bundle_v1.json output/bundle_v2.json
```

**Arguments:**
- `bundle1`: First bundle (baseline)
- `bundle2`: Second bundle (current)

Shows:
- Error count changes
- Added/removed stages
- Architectural differences

### benchmark

Benchmark pipeline performance.

```bash
cogant benchmark <target>
cogant benchmark ./my_repo
cogant benchmark ./my_repo --iterations 5
```

**Arguments:**
- `target`: Path to repository

**Options:**
- `--iterations, -n`: Number of runs (default: 3)

