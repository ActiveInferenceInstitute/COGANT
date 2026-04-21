## Artifact ownership

Canonical package layout is assembled by [`GNNPackageBuilder`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/gnn/package.py) (`REQUIRED_FILES` lists the top-level JSON siblings). Primary modules:

| Concern | Python module(s) |
|---------|------------------|
| GNN package directory layout, manifests, checksums | [`gnn/package.py`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/gnn/package.py) |
| `model.gnn.md` (18-section markdown) | [`gnn/formatter/`](https://github.com/cogant-contributors/cogant/tree/main/cogant/py/cogant/gnn/formatter) (`GNNMarkdownFormatter` and section helpers) |
| `model.gnn.json` and companion JSON | [`gnn/json_export.py`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/gnn/json_export.py) |
| Package validation score | [`gnn/validator.py`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/gnn/validator.py) |
| Execution / simulation runner | [`gnn/runner.py`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/gnn/runner.py) |
| Generic graph / bundle export (GraphML, Parquet, typed JSON) | [`export/`](https://github.com/cogant-contributors/cogant/tree/main/cogant/py/cogant/export) |

**When `gnn_package/` appears:** The directory is created during the pipeline **`export`** stage ([`run_export`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/api/orchestration.py)), which runs inside CLI **`cogant translate`** (and `Session.export_all` / full `PipelineRunner` runs)—not as a separate manual step. It is emitted when the bundle already has a program graph, state-space model, process model, and dict-shaped semantic mappings so [`GNNPackageBuilder`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/gnn/package.py) can run. The standalone **`cogant export-gnn`** command re-reads a saved bundle and writes formats under your chosen output; both paths go through the same GNN/export layers. Check packages with [`cogant validate`](../cli/README.md). Stage boundaries: [ARCHITECTURE](../architecture/README.md).
