# COGANT Cookbook

Practical recipes for common COGANT workflows. Each recipe is
self-contained and takes 2-15 minutes to complete.

| # | Recipe | Description |
|---|--------|-------------|
| 01 | [Scan your first project](01_scan_basic.md) | Run `cogant scan` on a Python repo and read the summary table |
| 02 | [Export as JSON](02_json_output.md) | Pipe the program graph into a JSON file for downstream tools |
| 03 | [Explain a node](03_explain_node.md) | Understand why a node was assigned its Active Inference role |
| 04 | [Custom thresholds](04_custom_threshold.md) | Tune confidence thresholds via pipeline config YAML |
| 05 | [Monorepo scanning](05_multi_project.md) | Run COGANT across multiple packages in a monorepo |
| 06 | [Reverse synthesis](06_reverse_basic.md) | Generate a runnable Python package from a GNN markdown file |
| 07 | [Custom package layout](07_reverse_custom.md) | Control the output directory and structure of synthesized code |
| 08 | [CI/CD integration](08_ci_integration.md) | Add COGANT validation to a GitHub Actions workflow |
| 09 | [Pre-commit hook](09_precommit_hook.md) | Detect GNN drift before commits land |
| 10 | [Docker](10_docker.md) | Run COGANT inside a container for reproducible builds |
| 11 | [JavaScript/TypeScript](11_javascript.md) | Scan JS/TS projects alongside Python |
| 12 | [Batch scanning](12_batch_scan.md) | Translate many repos in a single shell loop |
| 13 | [Incremental rescanning](13_incremental.md) | Skip unchanged files with `cogant changed` |
| 14 | [GNN validation](14_gnn_validation.md) | Validate a hand-written or edited GNN package |
| 15 | [Markov blanket visualization](15_markov_blanket.md) | Visualize blanket partitions in the program graph |
| 16 | [PNG export](16_png_figures.md) | Rasterize Mermaid/SVG/dot diagrams to PNG |
| 17 | [Benchmarking](17_benchmark.md) | Measure pipeline wall-clock performance |
| 18 | [Role filtering](18_role_filter.md) | Filter results by semantic role using `jq` |
| 19 | [Custom translation rules](19_extend_rules.md) | Add a new rule to the translation engine |
| 20 | [Dataset export](20_dataset.md) | Export a training dataset for ML from COGANT output |

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
