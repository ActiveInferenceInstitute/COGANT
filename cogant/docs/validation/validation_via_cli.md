## Validation via CLI

Use [`cogant validate`](../cli/README.md) to check: a path to **`bundle.json`**; a **run directory** that contains **`gnn_package/`** (full [`GNNValidator`](../py/cogant/gnn/validator.py) score) or a directory that **is** a `gnn_package`; or a run directory that has **`bundle.json`** but no GNN package path resolved (lightweight bundle checks on `dir/bundle.json`). Directories with neither `gnn_package/` nor `bundle.json` exit with code **2**. Exit codes and routing table: [CLI guide § validate](../cli/README.md).

