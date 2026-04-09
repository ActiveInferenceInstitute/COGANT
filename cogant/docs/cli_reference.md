# CLI Reference

COGANT ships a Typer-based CLI (entry point `cogant`, defined in `py/cogant/cli/main.py`) that registers 14+ subcommands. Every subcommand supports `--help`; the list below covers the ones most commonly used day-to-day.

Run `cogant --help` to see the authoritative, in-tree list.

## `cogant translate`

Run the full pipeline: ingest → static → normalize → graph → translate → statespace → process → export → validate.

```bash
cogant translate <repo> [--output DIR] [--layout-output] [--no-dynamic]
                        [--coverage PATH] [--trace PATH]
                        [--config FILE] [--skip STAGES]
```

| Flag | Description |
| --- | --- |
| `--output`, `-o` | Output directory (default: `output`). |
| `--layout-output` | After export, reorganize artifacts into `data/`, `diagrams/`, `site/`, `reports/`, `figures/`. |
| `--no-dynamic` | Skip the dynamic-analysis enrichment stage (coverage + trace). |
| `--coverage` | Path to a `.coverage` database or Cobertura `coverage.xml`. |
| `--trace` | Path to a Chrome DevTools trace JSON file. |
| `--config`, `-c` | YAML or JSON pipeline config file (supports flat or `pipeline:` nested layout). |
| `--skip` | Comma-separated list of stage names to skip. |

Writes `bundle.json` under the output directory and prints a per-stage status table.

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
| `cogant init <path>` | Initialize a new COGANT project (creates `.cogant/config.json`). |
| `cogant scan <target>` | Scan repository and print a summary table. |
| `cogant extract-static <target>` | Run only the static-analysis stages. |
| `cogant extract-dynamic <target>` | Run only the dynamic-analysis stage. |
| `cogant graph <target>` | Build the program graph and print node / edge counts. |
| `cogant statespace <target>` | Compile the state-space model and print state / observation / action / policy counts. |
| `cogant export-gnn <bundle>` | Export an existing bundle as Markdown / JSON / both. |
| `cogant render <bundle>` | Render an interactive HTML site from a bundle. |
| `cogant viz <run_dir>` | Rasterize every Mermaid / SVG / dot / networkX artifact in a run directory. |
| `cogant validate <target>` | Validate a bundle JSON, a run directory, or a `gnn_package/` (runs `GNNValidator`). |
| `cogant diff <a> <b>` | Compare two bundles or two output directories (drift report in Markdown). |

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
