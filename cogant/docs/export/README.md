# Export

> How COGANT emits artifacts for downstream consumers: the canonical GNN
> package on disk, JSON schemas for machine readers, graph exports for
> PyTorch Geometric and DGL, and the feature-engineering, compression,
> validation, and reproducibility policies that govern them. Read this
> section when you are integrating COGANT output into a training pipeline,
> another analysis tool, or a storage layer.

## Contents

| Page | Description | Level |
|------|-------------|-------|
| [Overview](overview.md) | Inventory of emitted artifacts and the canonical GNN package layout | Beginner |
| [Artifact ownership](artifact_ownership.md) | Which Python module writes which file and owns its schema | Intermediate |
| [JSON export format](json_export_format.md) | Typed program-graph JSON (`TypedExporter`) vs GNN package companions | Intermediate |
| [PyTorch Geometric export](pytorch_geometric_export.md) | `torch_geometric.data.Data` emission for PyG pipelines | Intermediate |
| [DGL export](dgl_export.md) | `DGLGraph` emission with node and edge features | Intermediate |
| [Feature engineering](feature_engineering.md) | Default node and edge features and how to customize them | Intermediate |
| [Compression and size](compression_size.md) | Compression options and size budgets for large exports | Intermediate |
| [Incremental export](incremental_export.md) | Emitting in batches for large projects | Advanced |
| [Reproducibility](reproducibility.md) | Metadata embedded in the export for reproducible downstream runs | Intermediate |
| [Validation](validation.md) | Structural and semantic checks applied before an export is finalized | Intermediate |
| [See also](see_also.md) | Cross-links to CLI, reference, and related modules | Beginner |

## Recommended Reading Order

1. [Overview](overview.md) — understand what COGANT actually writes to disk.
2. [Artifact ownership](artifact_ownership.md) — learn which module to edit
   when a specific file needs to change.
3. [JSON export format](json_export_format.md) — the most common consumer
   surface and a good reference for schema discipline.
4. Pick the graph export format you care about:
   [PyTorch Geometric](pytorch_geometric_export.md) or
   [DGL](dgl_export.md).
5. [Feature engineering](feature_engineering.md) — control what ends up on
   the nodes and edges of those graphs.
6. [Validation](validation.md) and [Reproducibility](reproducibility.md) —
   required reading before you wire the output into a production pipeline.
7. [Compression and size](compression_size.md) and
   [Incremental export](incremental_export.md) — scaling concerns once the
   happy path works.

## Related modules

- [../reference/README.md](../reference/README.md) — canonical schemas and
  package layout.
- [../cli/README.md](../cli/README.md) — `export-gnn`, `validate`, and
  related commands.
- [../concepts/gnn.md](../concepts/gnn.md) — conceptual primer on the GNN
  intermediate representation.
- [../validation/README.md](../validation/README.md) — validators that run
  against exported artifacts.

Agent notes: [AGENTS.md](AGENTS.md) - Hub: [../index.md](../index.md)
