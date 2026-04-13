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

cogant export-gnn: Export GNN bundle in JSON or Markdown format. Reads bundle.json and writes to output directory.

cogant render: Generate interactive HTML site from bundle.json, creating index.html, graph/, models/, provenance/, and assets/ with CSS styling.

cogant viz: Walk a run/output directory and rasterize Mermaid, SVG, dot, and related artifacts to PNG (see `cogant.viz.png_export`).

cogant validate: Run validation checks on bundle.json, or on a directory containing `gnn_package/` (full GNN package validation when applicable).

cogant diff: Compare two bundle.json files showing differences in errors and stages. Supports baseline vs current analysis.

cogant benchmark: Time pipeline performance across multiple runs, reporting average, min, and max execution times.

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

main.py: Typer app instance with 14 subcommands. Each command uses Session, PipelineRunner, or ReviewAPI from cogant.api. Rich Console for styled table and panel output. Typer.Argument and Typer.Option for parameter handling.

diff.py: Helper functions load_bundle and diff_command for comparing two output directories using DriftAnalyzer and CodebaseMetrics.

## Dependencies

Typer, Rich (for tables, panels, syntax highlighting, console output), and cogant.api (Session, PipelineRunner, Bundle, ReviewAPI).
