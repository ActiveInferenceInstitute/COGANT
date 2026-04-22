# CLI — Command-Line Interface

Typer-based command-line interface for COGANT. Entry point is main.py with console script `cogant` from root pyproject.toml.

## Commands

cogant init: Initialize a COGANT project scaffold in specified directory, creating .cogant config directory and config.json with default pipeline stages.

cogant scan: Quick repository summary showing target, file count, language distribution, and symbol counts. Supports table and JSON output formats.

cogant extract-static: Extract static analysis from target repository, parsing Python files for AST, types, and symbols. Can optionally export full graph and layout output.

cogant extract-dynamic: Extract dynamic analysis (traces, coverage). Placeholder for runtime trace ingestion; supports optional trace file paths.

cogant graph: Build program dependency graph from target, showing node and edge counts. Runs ingest and static stages as prerequisites.

cogant translate: Run full analysis pipeline (all stages) translating codebase to GNN. Shows stage results table, error summary, and saves bundle.json. Supports --skip to exclude stages, --layout-output for post-export organization.

cogant statespace: Compile state space model showing states, observations, actions, and policies. Runs prerequisites through translate stage.

cogant process: Extract process/execution model showing stages and dependencies.

cogant export-gnn: Re-export an existing bundle JSON as JSON and/or a Markdown report covering target, repo, static analysis, per-stage counts (graph/translate/statespace/validate/…), errors and source commit. Reads `bundle.json`, writes `bundle.json` and/or `bundle.md` to the output directory.

cogant render: Generate interactive HTML site from bundle.json, creating index.html, graph/, models/, provenance/, and assets/ with CSS styling.

cogant viz: Walk a run/output directory and rasterize Mermaid, SVG, dot, and related artifacts to PNG (see `cogant.viz.png_export`).

cogant validate: Run validation checks on bundle.json, or on a directory containing `gnn_package/` (full GNN package validation when applicable). For a `gnn_package` directory, Active Inference Institute `src.gnn` checks on `model.gnn.md` run by default; pass `--no-upstream-gnn` to skip them while keeping COGANT structural validation, or set `COGANT_DISABLE_UPSTREAM_GNN=1`.

cogant diff: Compare two bundle.json files showing differences in errors and stages. Supports baseline vs current analysis.

cogant changed: List source files that changed since a given git ref (used for incremental analysis scoping).

cogant explain: Show fixpoint engine rule-match explanations for a given output bundle — which rules fired and why.

cogant analyze: Full pipeline alias (translate + statespace + export); convenience shorthand for the common workflow.

cogant analyze-static: Run only the static-analysis stages (ingest + parse + symbol extract) and report findings.

cogant analyze-graph: Run the graph-construction stage on a pre-ingested source tree and print adjacency summary.

cogant visualize: Render interactive SVG/HTML visualizations of the program graph and GNN matrices.

cogant export: Export the GNN bundle to a specified format (json, jsonl, parquet, protobuf, graphml).

cogant reverse: Synthesize a runnable Python package from a GNN markdown file.

cogant roundtrip: Verify forward-reverse-forward round-trip isomorphism (**23/23 ISOMORPHIC** on the canonical evaluation set — 12 zoo fixtures, 3 real-world examples, and 8 uncurated libraries).

cogant benchmark: Time pipeline performance across multiple runs, reporting average, min, and max execution times.

cogant version: Print the package version and exit.

cogant upstream-gnn: Re-run the Active Inference Institute 25-step `src.gnn` pipeline on an existing `gnn_package/` directory (skips Render/Execute by default; set `COGANT_RUN_UPSTREAM_PIPELINE=1` for the slow integration path).

cogant plugin list / cogant plugin info: Enumerate discovered plugins and print details about a specific plugin.

cogant migrate: Migrate on-disk artifacts to the current bundle schema version.

## Usage Examples

```bash
cogant init ./my_project
cogant scan ./my_repo
cogant translate ./my_repo --output output/ --layout-output
cogant render output/bundle.json --output site/
cogant viz output/
cogant diff output/baseline/bundle.json output/current/bundle.json
cogant benchmark ./my_repo --iterations 5
```

## Implementation

main.py: Typer app instance that registers **26 top-level commands** via `@app.command` (17 plain `@app.command()` calls + 9 with an explicit name — 6 positional like `@app.command("analyze-static")`, plus `name="reverse"`, `name="roundtrip"`, and `name="version"`). It also attaches the `plugin` sub-typer (2 leaves: `list`, `info`) and the `migrate` sub-typer (1 leaf) via `app.add_typer`, for **29 leaf commands total**. Each command delegates to Session, PipelineRunner, or ReviewAPI from `cogant.api`. Rich Console for styled table and panel output. Typer.Argument and Typer.Option for parameter handling.

diff.py: Helper functions load_bundle and diff_command for comparing two output directories using DriftAnalyzer and CodebaseMetrics.

## Dependencies

Typer, Rich (for tables, panels, syntax highlighting, console output), and cogant.api (Session, PipelineRunner, Bundle, ReviewAPI).
