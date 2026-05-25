## Export stage and GNN package

The **`export`** pipeline stage is implemented by [`run_export`](https://github.com/docxology/cogant/blob/main/cogant/py/cogant/api/orchestration.py) (invoked from `PipelineRunner` and from `Session.export_all` / CLI `translate`). It writes flat JSON artifacts under `output_dir` (`program_graph.json`, `state_space.json`, `process_model.json`, `gnn_model.json`, etc.).

When all of the following are present on the in-memory bundle—**program graph** (`_program_graph`), **state-space model** (`_state_space_model`), **process model** (`_process_model`)—orchestration also builds a full **`output_dir/gnn_package/`** tree via [`GNNPackageBuilder`](https://github.com/docxology/cogant/blob/main/cogant/py/cogant/gnn/package.py). Semantic mappings must be stored as a **dict** on `bundle.artifacts["_semantic_mappings"]` (mapping id → [`SemanticMapping`](https://github.com/docxology/cogant/blob/main/cogant/py/cogant/schemas/semantic.py)); the builder and markdown formatter expect dict-shaped input, not a bare list of mappings.

On failure, package build is non-fatal: warnings may appear under export-related artifact keys; see [GNN export](../export/README.md) and [SPEC § Implementation status](../reference/README.md).

To validate a package from the CLI or disk layout, use [`cogant validate`](../cli/README.md). The **`validate`** stage in `run_validate` can run [`GNNValidator`](https://github.com/docxology/cogant/blob/main/cogant/py/cogant/gnn/validator.py) when `_gnn_package_dir` was set during export.
