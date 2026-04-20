# `upstream_bridge`

Lazy facade over the Active Inference Institute
**`generalized-notation-notation`** package (import path `src.gnn`).
Heavy upstream dependencies are imported only on first use, so
`import cogant` stays fast.

Two independent surfaces:

* **Validation / parsing helpers** (`upstream_*` functions) — wrap
  individual upstream entry points (`validate_gnn`, `parse_gnn_file`,
  `process_gnn_directory`, …) with JSON-safe returns and graceful
  fallback when the upstream package is missing.
* **Pipeline driver** (`pipeline.py`) — runs the upstream **25-step
  pipeline** (`src.main.execute_pipeline_step`) over a COGANT-built
  `gnn_package/`. Render (step 11) and Execute (step 12) are skipped
  by default; everything else runs as a configurable post-validate
  pass.

See [`AGENTS.md`](AGENTS.md) for the full `upstream_*` API surface,
the 25-step catalogue, the `UpstreamPipelineConfig` reference, the
`COGANT_DISABLE_UPSTREAM_GNN` env flag, and the upstream
**CC-BY-NC-SA-4.0** license note (also tracked in
`cogant/LICENSES.md`).
