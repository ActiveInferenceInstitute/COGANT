## Commands

The Typer app in [`py/cogant/cli/main.py`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/cli/main.py) registers **28 top-level subcommands** as of v0.5.0. `cogant --help` is ground truth; the entries below are kept in sync by the doc-link verifier.

### init

Initialize a new COGANT project with configuration. Safe to re-run: creates `.cogant/config.json` if missing and refuses to clobber an existing config.

```bash
cogant init <path>
cogant init my_project
cogant init my_project --check --run -y
```

**Arguments:**
- `path`: Path to initialize (created if it does not exist). Required.

**Options:**
- `--quiet, -q`: Minimal output (suppresses confirmation summary).
- `--check / --no-check`: Run `cogant doctor` before touching the filesystem. Default: `--no-check`.
- `--run`: After initializing, also run `cogant translate` on the newly created project.
- `--yes, -y`: Skip the confirmation prompt before running `translate`.

### doctor

Diagnose the COGANT runtime environment. Prints a Rich panel listing the Python version, every runtime dependency (core, viz, multilang), the optional Rust backend, and external tooling such as `git`. Exits with code `1` when any required check fails so it can gate CI setups.

```bash
cogant doctor
```

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
- `--layout-output`: After export, move artifacts into `data/`, `diagrams/`, `site/`, `reports/`, `figures/` subdirectories for easier downstream consumption.

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
cogant translate ./my_repo --output output/ --skip dynamic,export
```

**Arguments:**
- `target`: Path to repository (default: current directory)

**Options:**
- `--config, -c`: YAML or JSON pipeline config file with stage / plugin overrides.
- `--skip`: Comma-separated list of stages to skip (e.g. `'dynamic,validate'`). Whitespace around names is trimmed.
- `--output, -o`: Directory where `bundle.json` and derived artifacts are written. Default: `output`.
- `--layout-output`: After export, move artifacts into `data/`, `diagrams/`, `site/`, `reports/`, `figures/` subdirectories.
- `--no-dynamic`: Skip the dynamic-analysis enrichment stage (coverage + trace). Faster but less accurate.
- `--coverage`: Path to a coverage database (`.coverage`) or Cobertura `coverage.xml`.
- `--trace`: Path to a Chrome DevTools trace JSON file for dynamic analysis.
- `--incremental`: Git ref (e.g. `HEAD~1`, a commit hash, or a tag) to use as the incremental baseline. Only files that changed between this ref and HEAD are re-parsed; unchanged results are served from `~/.cache/cogant` when available.
- `--cache-dir`: Override the incremental cache directory. Defaults to `~/.cache/cogant`. Useful for tests and benchmarks that need an isolated cache state.

**Artifacts:** Writes **`bundle.json`** in the output directory (full pipeline `Bundle` snapshot for `cogant render` / `cogant validate`) plus stage exports from the `export` stage when run.

**Stages:** ingest, static, normalize, graph, translate, statespace, process, export, validate

### analyze

Canonical entry point for running the COGANT pipeline on a codebase, with first-class incremental support. In its default form it is equivalent to `cogant translate`. With `--incremental <commit>` it switches to the fast path: resolves `git diff --name-only <commit> HEAD`, looks up a cached bundle in `~/.cache/cogant`, and re-parses only changed files, patching cached stage results via `cogant.ingest.incremental.apply_incremental_patch`. On cache miss it falls back to a full cold run and populates the cache.

```bash
cogant analyze <target>
cogant analyze ./my_repo
cogant analyze ./my_repo --incremental HEAD~1 --no-dynamic
```

**Arguments:**
- `target`: Path of the repository to analyze. Default: `.`.

**Options:**
- `--incremental`: Git commit SHA, tag, branch, or relative ref (e.g. `HEAD~1`) to use as the incremental baseline. Omit to run a full cold analysis.
- `--output, -o`: Directory where `bundle.json` and derived artifacts are written. Default: `output`.
- `--cache-dir`: Override the incremental cache directory. Defaults to `~/.cache/cogant`.
- `--no-dynamic`: Skip the dynamic-analysis enrichment stage. Recommended for incremental runs.
- `--skip`: Comma-separated list of stages to skip (e.g. `'dynamic,validate'`).
- `--quiet, -q`: Suppress per-stage progress output (still prints summary).

Incremental stats (`cache_hit`, `files_reparsed`, `files_total`, `reason`) are reported after the run and persisted on `bundle.metadata['incremental_stats']`.

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

Extract the pipeline / execution process model from a repository. Runs the pipeline without the `export` and `validate` stages so you get the process graph quickly.

```bash
cogant process <target>
cogant process ./my_repo
cogant process ./my_repo --no-dynamic
```

**Arguments:**
- `target`: Path to the repository whose execution / process model to extract. Default: `.`.

**Options:**
- `--no-dynamic`: Skip the dynamic-analysis enrichment stage (coverage + trace).

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

Uses [`cogant.viz.png_export.render_all_pngs`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/viz/png_export.py). Safe to re-run; overwrites existing PNGs.

### validate

Run validation checks on a bundle file or on a directory (run output, `gnn_package`, or hybrid). Implementation: [`py/cogant/cli/main.py`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/cli/main.py).

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
| **Directory** whose path **is** a GNN package (`manifest.json` + `model.gnn.md` at that path) | Full [`GNNValidator`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/gnn/validator.py): score, errors, warnings (18-section contract). |
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

Compare two bundles or output directories and report drift. When both arguments are directories containing COGANT output (with `program_graph.json`, `semantic_mappings.json`, and/or `model.gnn.json`), the full [`cogant.cli.diff.diff_command`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/cli/diff.py) is invoked: it runs `DriftAnalyzer` and `CodebaseMetrics` and prints / writes a full markdown drift report. When both arguments are bundle JSON files, a lightweight shallow diff is shown (legacy behavior).

```bash
cogant diff <path_a> <path_b>
cogant diff output/bundle_v1.json output/bundle_v2.json
cogant diff output/run_v1/ output/run_v2/ --output drift.md
```

**Arguments:**
- `path_a`: Baseline bundle JSON or output directory. Required.
- `path_b`: Current bundle JSON or output directory. Required.

**Options:**
- `--output, -o`: Write the full drift report to this markdown file.

### benchmark

Benchmark pipeline wall-clock performance over several runs. Prints average / min / max across `iterations`. The `export` and `validate` stages are skipped so the measurement focuses on the translation core rather than IO.

```bash
cogant benchmark <target>
cogant benchmark ./my_repo
cogant benchmark ./my_repo --iterations 5 --no-dynamic
```

**Arguments:**
- `target`: Path of the repository to benchmark. Default: `.`.

**Options:**
- `--iterations, -n`: Number of independent pipeline runs to time. Default: `3`.
- `--no-dynamic`: Skip the dynamic-analysis enrichment stage (coverage + trace). Use this to measure pure static-analysis throughput.

### changed

List files changed since a git ref — the incremental-analysis helper. Emits a warning and exits non-zero when the target is not a git working tree.

```bash
cogant changed <path>
cogant changed ./my_repo --since HEAD~3 --python-only
cogant changed ./my_repo --output changed.txt
```

**Arguments:**
- `path`: Repository path (must be a git working tree). Default: `.`.

**Options:**
- `--since, -s`: Git ref to compare against. Default: `HEAD~1`.
- `--python-only`: Only list changed Python files.
- `--source-only`: Only list changed source files in known languages.
- `--output, -o`: Write the list of changed files to this path (one per line).

### explain

Explain *why* a given node was assigned its Active Inference role. Runs the static pipeline (ingest → static → normalize → graph → translate) against `repo_path`, resolves `node_name` to a concrete node in the program graph, then asks every registered translation rule whether it fired on that node and why.

```bash
cogant explain <repo_path> <node_name>
cogant explain ./my_repo MyService.handle_request
cogant explain ./my_repo handle --format json
```

**Arguments:**
- `repo_path`: Path to the repository to analyze. Required.
- `node_name`: Node name (or substring) to explain. Required.

**Options:**
- `--format, -f`: Output format: `text` (rich console) or `json`. Default: `text`.

**Resolution order** for `node_name`: exact case-sensitive match → exact case-insensitive match → shortest case-insensitive substring match. If nothing matches, the CLI prints a sample of up to 25 candidate node names and exits non-zero.

**Exit codes:** `0` success; `1` pipeline / IO errors; `2` when the node name cannot be resolved.

### reverse

Synthesize a Python package from a GNN markdown file.

```bash
cogant reverse <gnn_file>
cogant reverse output/gnn_package/model.gnn.md --output synthesized/
cogant reverse output/model.gnn.md --json
```

**Arguments:**
- `gnn_file`: Path to a GNN markdown file produced by COGANT (or any conforming emitter). Required.

**Options:**
- `--output, -o`: Directory where the synthesized Python package will be written. Default: `reverse_output`.
- `--json`: Print a machine-readable JSON summary instead of the Rich table.

### roundtrip

Verify forward-reverse-forward round-trip isomorphism. Accepts either a GNN markdown file or a repository directory.

```bash
cogant roundtrip <target>
cogant roundtrip ./my_repo --threshold 0.8 --keep-tmp
cogant roundtrip output/model.gnn.md --json
```

**Arguments:**
- `target`: Either a GNN markdown file or a repository directory to round-trip. Required.

**Options:**
- `--output, -o`: Directory where intermediate GNN + synthesized package are stored.
- `--threshold`: Minimum role-match score for the round-trip to be flagged isomorphic. Default: `0.5`.
- `--json`: Print a JSON summary of the round-trip instead of the Rich table.
- `--keep-tmp`: Preserve the synthesized package on disk for inspection.

### plugin

Manage and inspect COGANT plugins. A Typer command group with two subcommands.

```bash
cogant plugin list
cogant plugin info <name>
```

**Subcommands:**
- `plugin list`: List all discovered COGANT plugins.
- `plugin info <name>`: Show detailed information about a specific plugin. `name` is required.

### migrate

Migrate GNN files to the current schema version. A Typer command group whose single subcommand is itself named `migrate` (so the full invocation is `cogant migrate migrate <path>`).

```bash
cogant migrate migrate <path>
cogant migrate migrate output/model.gnn.md --target 1.1
cogant migrate migrate output/model.gnn.md --dry-run
```

**Subcommand `migrate`:**
- `path`: Path to GNN markdown file to migrate. Required.
- `--dry-run`: Print diff without modifying the file.
- `--target`: Target schema version. Default: `1.1`.

### upstream-gnn

Drive the upstream GNN 25-step pipeline (`generalized-notation-notation`) against an existing COGANT-emitted `gnn_package/`. Network- and LLM-bound steps (12 LLM, 14 ML integration, 18 audio, 23 website) are skipped by default to keep CI offline-safe.

```bash
cogant upstream-gnn output/gnn_package
cogant upstream-gnn output/gnn_package --output-dir output/upstream
cogant upstream-gnn output/gnn_package --only-steps 1,3,8 --frameworks pymdp,rxinfer
cogant upstream-gnn output/gnn_package --skip-steps 12,14,18,23 --verbose
```

**Arguments:**
- `package_dir`: Path to a `gnn_package/` directory (typically produced by `cogant translate`). Required.

**Options:**
- `--output-dir, -o`: Where upstream artifacts are written. Default: `<package_dir>/upstream_gnn/`.
- `--only-steps`: Comma-separated 1-based step numbers to run (subset of the 25-step catalog).
- `--skip-steps`: Comma-separated 1-based step numbers to skip. Defaults to network-bound steps when neither `--only-steps` nor `--skip-steps` is given.
- `--frameworks`: Comma-separated render targets for upstream step 11 (e.g. `pymdp,rxinfer`).
- `--llm-model`: Model identifier passed to upstream step 13 (only used when step 13 is enabled).
- `--verbose, -v`: Forward `-v` to the upstream subprocess.

The same wiring is also exposed as opt-in flags on `cogant translate`, `cogant analyze`, and `cogant validate` via `--upstream-gnn-pipeline` (and the matching `--upstream-gnn-only-steps` / `--upstream-gnn-skip-steps` / `--upstream-gnn-frameworks` / `--upstream-gnn-llm-model` knobs); see `cogant translate --help` for the full surface.

**Exit codes:** `0` on success; `1` if the upstream subprocess exits non-zero on any executed step.
