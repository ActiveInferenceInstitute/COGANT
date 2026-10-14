# `upstream_bridge`

Lazy facade over the Active Inference Institute
**`generalized-notation-notation`** package (GNN 4.1.0 release line; import
package `gnn`). It is an **optional** dependency, installed only through the
`upstream` extra (`uv sync --extra upstream`), and heavy upstream dependencies
are imported only on first use, so `import cogant` stays fast.

Callers should use this facade instead of a raw `import gnn`: the bridge
refuses an upstream older than 4.0 or a `gnn` package owned by another
distribution, and maps COGANT's facades onto the GNN 4.x API
(`validate_gnn_syntax`, `validate_gnn_source`, `check_gnn_file_structure`).
The GNN 2.x `src.gnn` import surface no longer exists upstream.

Two independent surfaces:

* **Validation / parsing helpers** (`upstream_*` functions) — wrap
  individual upstream entry points (`validate_gnn_syntax`, `parse_gnn_file`,
  `process_gnn_directory`, …) with JSON-safe returns; validation reports an
  unavailable upstream instead of raising. Upstream validation is opt-in:
  `upstream_gnn=True`, `PipelineConfig.upstream_gnn_validation=True`, or a
  truthy `COGANT_ENABLE_UPSTREAM_GNN` when the caller leaves the choice open.
* **Pipeline driver** (`pipeline.py`) — runs the upstream **25-step
  pipeline** over a COGANT-built `gnn_package/` as one
  `python -m gnn.main --only-steps …` invocation. Steps `1_setup`, `2_tests`,
  `11_render`, and `12_execute` are skipped by default (`DEFAULT_SKIP_STEPS`);
  upstream may still run 11 and 12 as hard prerequisites of selected steps.

See [`AGENTS.md`](AGENTS.md) for the full `upstream_*` API surface,
the 25-step catalogue, the `UpstreamPipelineConfig` reference, the
opt-in `COGANT_ENABLE_UPSTREAM_GNN` / kill-switch `COGANT_DISABLE_UPSTREAM_GNN`
env flags (upstream validation is off by default), and the upstream
**CC-BY-NC-SA-4.0** license note (also tracked in `cogant/LICENSES.md`).
Recorded results against the current pin live in
`cogant/docs/evaluation/GNN_UPSTREAM_AUDIT_SURFACE.md`.
