# COGANT Cookbook

> Practical recipes for common COGANT workflows. Each recipe is self-contained, takes 2-15 minutes to complete, and ships with copy-pasteable commands. Use the cookbook when you have a specific outcome in mind; use [../tutorials/](../tutorials/README.md) when you want a guided walkthrough and [../concepts/](../concepts/README.md) when you want background theory.

## Contents

| # | Recipe | Description | Level |
|---|--------|-------------|-------|
| 01 | [Scan your first project](01_scan_basic.md) | Run `cogant scan` on a Python repo and read the summary table | Beginner |
| 02 | [Export as JSON](02_json_output.md) | Pipe the program graph into a JSON file for downstream tools | Beginner |
| 03 | [Explain a node](03_explain_node.md) | Understand why a node was assigned its Active Inference role | Beginner |
| 04 | [Custom thresholds](04_custom_threshold.md) | Tune confidence thresholds via pipeline config YAML | Intermediate |
| 05 | [Monorepo scanning](05_multi_project.md) | Run COGANT across multiple packages in a monorepo | Intermediate |
| 06 | [Reverse synthesis](06_reverse_basic.md) | Generate a runnable Python package from a GNN markdown file | Intermediate |
| 07 | [Custom package layout](07_reverse_custom.md) | Control the output directory and structure of synthesized code | Intermediate |
| 08 | [CI/CD integration](08_ci_integration.md) | Add COGANT validation to a GitHub Actions workflow | Intermediate |
| 09 | [Pre-commit hook](09_precommit_hook.md) | Detect GNN drift before commits land | Intermediate |
| 10 | [Docker](10_docker.md) | Run COGANT inside a container for reproducible builds | Intermediate |
| 11 | [JavaScript/TypeScript](11_javascript.md) | Scan JS/TS projects alongside Python | Intermediate |
| 12 | [Batch scanning](12_batch_scan.md) | Translate many repos in a single shell loop | Intermediate |
| 13 | [Incremental rescanning](13_incremental.md) | Skip unchanged files with `cogant changed` | Intermediate |
| 14 | [GNN validation](14_gnn_validation.md) | Validate a hand-written or edited GNN package | Intermediate |
| 15 | [Markov blanket visualization](15_markov_blanket.md) | Visualize blanket partitions in the program graph | Intermediate |
| 16 | [PNG export](16_png_figures.md) | Rasterize Mermaid/SVG/dot diagrams to PNG | Beginner |
| 17 | [Benchmarking](17_benchmark.md) | Measure pipeline wall-clock performance | Advanced |
| 18 | [Role filtering](18_role_filter.md) | Filter results by semantic role using `jq` | Intermediate |
| 19 | [Custom translation rules](19_extend_rules.md) | Add a new rule to the translation engine | Advanced |
| 20 | [Dataset export](20_dataset.md) | Export a training dataset for ML from COGANT output | Advanced |

## Numbering scheme

Recipes are numbered `NN_slug.md` roughly in the order a new user is likely
to encounter them: basics first (01-05), then integration and workflow
(06-13), then the more advanced workflows (14-20). Numbers are editorial
only — they do not encode dependencies, and you can jump to any recipe
directly.

## Non-numbered recipes

Three stable recipes predate the numbering scheme and are kept under their
original slugs so external links do not break. They remain valid but new
content should go into a new numbered recipe rather than extending these.

| Recipe | Description | Status |
|--------|-------------|--------|
| [Analyze a Flask app](analyze_a_flask_app.md) | End-to-end Flask analysis walkthrough | Stable; overlaps with `../tutorials/03_flask_walkthrough.md` |
| [Custom translation rules](custom_translation_rules.md) | Author a new translation rule for the engine | Stable; overlaps with `19_extend_rules.md` |
| [Interpret GNN output](interpret_gnn_output.md) | Read and interpret a generated GNN package | Stable; overlaps with `03_explain_node.md` |

## Recommended Reading Order

1. [01 Scan your first project](01_scan_basic.md) — confirm COGANT works end-to-end on your machine.
2. [02 Export as JSON](02_json_output.md) and [03 Explain a node](03_explain_node.md) — learn to read and interrogate the output.
3. [04 Custom thresholds](04_custom_threshold.md) — your first configuration tweak.
4. [08 CI/CD integration](08_ci_integration.md) and [09 Pre-commit hook](09_precommit_hook.md) — wire COGANT into your day-to-day workflow.
5. [06 Reverse synthesis](06_reverse_basic.md) and [14 GNN validation](14_gnn_validation.md) — exercise the reverse pipeline and validation surface.
6. Pick targeted recipes from the rest of the table as use cases arise.

## Prerequisites

All recipes assume COGANT is installed:

```bash
pip install cogant
# or with visualization extras
pip install "cogant[viz]"
```

Verify your environment:

```bash
cogant doctor
```

Agent notes: [AGENTS.md](AGENTS.md) - Hub: [../index.md](../index.md)
