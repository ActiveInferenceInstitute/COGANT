# AGENTS.md — Export module

Documentation for the COGANT export surface: the on-disk GNN package layout,
JSON / PyG / DGL emitters, feature engineering, compression, incremental
export, reproducibility metadata, and validation hooks. The goal of this
module is to give downstream consumers a stable, documented contract so
they can read COGANT output without having to read COGANT source.

## Purpose and ownership

Each page maps to a specific piece of the export pipeline in
`py/cogant/export/` and `py/cogant/gnn/`. When that code changes, the
matching page must change in the same PR. Owned by whoever is editing the
export or GNN package modules.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC, recommended reading order, cross-links | Any time a file is added, removed, or renamed |
| `AGENTS.md` | This file — maintenance rules | When ownership or the update-with-code policy changes |
| `overview.md` | Inventory of emitted artifacts and canonical package layout | When a new artifact is added or removed from the package |
| `artifact_ownership.md` | Which Python module owns which file in the package | When ownership moves between modules |
| `json_export_format.md` | Typed program-graph JSON (`TypedExporter`); cross-links GNN companions | When `typed_export` node/edge shapes or metadata keys change |
| `pytorch_geometric_export.md` | PyG `Data` emission | When PyG output attributes or types change |
| `dgl_export.md` | DGL `DGLGraph` emission | When DGL node/edge features change |
| `feature_engineering.md` | Default node/edge feature policy and customization | When the default feature set changes |
| `compression_size.md` | Compression options and size budgets | When compression defaults or size limits change |
| `incremental_export.md` | Batched export for large projects | When the batching API changes |
| `reproducibility.md` | Reproducibility metadata embedded in exports | When the reproducibility envelope changes |
| `validation.md` | Pre-finalization structural and semantic checks | When a new validator gates exports |
| `see_also.md` | Cross-links to CLI, reference, and related modules | When link targets move |

## Adding a new doc

1. Decide whether the new content is a format (goes alongside
   `json_export_format.md` / `pytorch_geometric_export.md` /
   `dgl_export.md`), a policy (alongside `compression_size.md` /
   `reproducibility.md`), or an operational concern (alongside
   `incremental_export.md` / `validation.md`).
2. Use a short, lower-case, underscore-separated slug (for example
   `numpy_export.md`).
3. Open with a one-sentence description of the output format or policy,
   followed by a minimal example that a consumer could copy-paste.
4. Document the schema version or backwards-compatibility story explicitly.
5. Add a row to the `## Contents` table in `README.md` and mention the new
   page in the `## Recommended Reading Order` if it belongs in the main
   spine rather than as a leaf.

## Known gotchas

- Schema changes are consumer-visible. Any edit to
  `json_export_format.md`, `pytorch_geometric_export.md`, `dgl_export.md`,
  or `feature_engineering.md` must ship alongside a matching schema-version
  bump and a note in `../roadmap/deprecation_policy.md`.
- `artifact_ownership.md` uses absolute GitHub URLs for module references
  so the doc remains readable when browsed outside MkDocs. If a module
  moves, fix the URL here as well as in code.
