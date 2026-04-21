# CLI Reference

COGANT ships a Typer-based CLI (entry point `cogant`, defined in `py/cogant/cli/main.py`) that registers **28 top-level subcommands** as of v0.5.0. Every subcommand supports `--help`; the list below covers the ones most commonly used day-to-day.

Run `cogant --help` to see the authoritative, in-tree list (counts change when new commands ship).

## `cogant translate`

Run the full pipeline: ingest → static → normalize → graph → translate → statespace → process → export → validate.

```bash
cogant translate <repo> [--output DIR] [--layout-output] [--no-dynamic]
                        [--coverage PATH] [--trace PATH]
                        [--config FILE] [--skip STAGES]
                        [--incremental REF] [--cache-dir DIR]
```

| Flag | Description |
| --- | --- |
| `--output`, `-o` | Output directory (default: `output`). |
| `--layout-output` | After export, reorganize artifacts into `data/`, `diagrams/`, `site/`, `reports/`, `figures/`. The batch runner (`run_all.py`) adds `analysis/`, `exports/`, `gnn_package/`, `roundtrip/` alongside these. |
| `--no-dynamic` | Skip the dynamic-analysis enrichment stage (coverage + trace). |
| `--coverage` | Path to a `.coverage` database or Cobertura `coverage.xml`. |
| `--trace` | Path to a Chrome DevTools trace JSON file. |
| `--config`, `-c` | YAML or JSON pipeline config file (supports flat or `pipeline:` nested layout). |
| `--skip` | Comma-separated list of stage names to skip. |
| `--incremental` | Git ref (e.g. `HEAD~1`, commit hash, tag) to use as the incremental baseline; only changed files are re-parsed. |
| `--cache-dir` | Override the incremental cache directory (default: `~/.cache/cogant`). |
| `--upstream-gnn-pipeline` / `--no-upstream-gnn-pipeline` | Enable/disable the upstream GNN 25-step pipeline pass after `validate` (default: disabled). |
| `--upstream-gnn-only-steps` | Comma-separated 1-based step numbers to run (e.g. `1,3,4,8`); subset of the upstream catalog. |
| `--upstream-gnn-skip-steps` | Comma-separated 1-based step numbers to skip; default skips network-bound steps (LLM, audio, website). |
| `--upstream-gnn-frameworks` | Comma-separated render targets for upstream step 11 (e.g. `pymdp,rxinfer`). |
| `--upstream-gnn-llm-model` | Override LLM model identifier for upstream step 13 (only relevant when step 13 is enabled). |

Writes `bundle.json` under the output directory and prints a per-stage status table.

## `cogant analyze`

Canonical pipeline entry point with first-class incremental support. Default form is equivalent to `cogant translate`; with `--incremental <commit>` it resolves `git diff --name-only <commit> HEAD`, consults a cached bundle under `~/.cache/cogant`, and re-parses only the changed files.

```bash
cogant analyze <repo> [--incremental REF] [--output DIR] [--cache-dir DIR]
                      [--no-dynamic] [--skip STAGES] [--quiet]
```

Incremental stats (`cache_hit`, `files_reparsed`, `files_total`, `reason`) are reported after the run and persisted on `bundle.metadata['incremental_stats']`.

## `cogant explain`

Explain *why* a given node was assigned its Active Inference role. Runs the minimal pipeline (ingest + static + normalize + graph + translate) and reports rules that fired, rules considered but not fired, and the Markov blanket role.

```bash
cogant explain <repo> <node_name> [--format text|json]
```

Resolution order for `node_name`: exact case-sensitive match → exact case-insensitive match → shortest case-insensitive substring match. If nothing matches, the CLI prints a sample of up to 25 candidate node names and exits non-zero.

Output fields:

- `assigned_role` — the final `MappingKind` (HIDDEN_STATE, OBSERVATION, ...).
- `rules_fired` — list of `RuleExplanation` objects sorted by priority (descending).
- `rules_considered` — rules that did not fire, with their reasons.
- `blanket_role` — one of `internal`, `sensory`, `active`, `external`.
- `blanket_rationale` — a one-line explanation from `MarkovBlanketExtractor`.

## `cogant changed`

List files changed since a git ref — the incremental-analysis helper. Emits a warning and exits non-zero when the target is not a git working tree.

```bash
cogant changed <repo> [--since HEAD~1] [--python-only] [--source-only] [--output FILE]
```

| Flag | Description |
| --- | --- |
| `--since`, `-s` | Git ref to compare against (default `HEAD~1`). |
| `--python-only` | Only list changed Python files. |
| `--source-only` | Only list changed source files in known languages. |
| `--output`, `-o` | Write the list of changed files to a path (one per line). |

## `cogant process`

Extract the process / execution model. Runs the pipeline with `export` and `validate` stages skipped, then prints a compact summary (stage and dependency counts).

```bash
cogant process <repo> [--no-dynamic]
```

## `cogant benchmark`

Benchmark pipeline performance across multiple runs. Prints per-run wall time and an aggregate average / min / max table.

```bash
cogant benchmark <repo> [--iterations N] [--no-dynamic]
```

Defaults to 3 iterations. Each iteration runs the pipeline with `export` and `validate` skipped to measure the analytical path.

## Other commands

| Command | Purpose |
| --- | --- |
| `cogant init <path>` | Initialize a new COGANT project (creates `.cogant/config.json`; supports `--check`, `--run`, `-y`). |
| `cogant doctor` | Diagnose the runtime environment (Python, deps, tree-sitter, Rust, git). Exits `1` on any required check failure. |
| `cogant scan <target>` | Scan repository and print a summary table (`--format table|json`). |
| `cogant extract-static <target>` | Run only the static-analysis stages. `--output DIR` triggers the full export path; `--layout-output` reorganizes artifacts. |
| `cogant extract-dynamic <target>` | Run only the dynamic-analysis stage. `--traces PATH` merges a pre-recorded trace. |
| `cogant graph <target>` | Build the program graph and print node / edge counts. |
| `cogant statespace <target>` | Compile the state-space model and print state / observation / action / policy counts. |
| `cogant export-gnn <bundle>` | Export an existing bundle as Markdown / JSON / both (`--format all|markdown|json`). |
| `cogant render <bundle>` | Render an interactive HTML site from a bundle. |
| `cogant viz <run_dir>` | Rasterize every Mermaid / SVG / dot / networkX artifact in a run directory. |
| `cogant validate <target>` | Validate a bundle JSON, a run directory, or a `gnn_package/` (runs `GNNValidator`). |
| `cogant diff <a> <b>` | Compare two bundles or two output directories (drift report in Markdown; `--output FILE`). |
| `cogant reverse <gnn_file>` | Synthesize a Python package from a GNN markdown file (`--output DIR`, `--json`). |
| `cogant roundtrip <target>` | Verify forward-reverse-forward round-trip isomorphism (`--threshold FLOAT`, `--keep-tmp`, `--json`). |
| `cogant plugin list` / `cogant plugin info <name>` | Manage and inspect COGANT plugins. |
| `cogant migrate migrate <path>` | Migrate GNN files to the current schema version (`--target`, `--dry-run`). |
| `cogant upstream-gnn <package_dir>` | Drive the upstream GNN 25-step pipeline (`generalized-notation-notation`) against an existing `gnn_package/` (`--only-steps`, `--skip-steps`, `--output-dir`, `--frameworks`, `--llm-model`, `--verbose`). |

## Upstream GNN 25-step pipeline

`cogant upstream-gnn` shells out to the upstream `generalized-notation-notation` repo (under `cogant/_extensions/generalized-notation-notation/src/main.py`) to run the canonical 25-step pipeline against an existing COGANT-emitted `gnn_package/`. Network- and LLM-dependent steps (12 LLM, 14 ML integration, 18 audio, 23 website) are skipped by default. The same wiring is also exposed as opt-in flags on `cogant translate`, `cogant analyze`, and `cogant validate` (see `--upstream-gnn-pipeline` above) so a single pipeline run can produce both the COGANT bundle and the upstream artifacts.

```bash
cogant upstream-gnn output/gnn_package
cogant upstream-gnn output/gnn_package --only-steps 1,3,8 --output-dir output/upstream
cogant upstream-gnn output/gnn_package --frameworks pymdp,rxinfer --verbose
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | Validation failed or diagnostic check failed. |
| `2` | Input path not found, or argument invalid. |

## See also

- [Quick Start](getting-started/quickstart.md)
- [Flask app walkthrough](tutorials/flask.md)
- [API Reference — `cogant.translate`](api/translate.md)
