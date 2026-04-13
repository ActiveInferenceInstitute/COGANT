## JSON export format

> **Scope:** Typed **program graph** JSON produced by `TypedExporter.export_typed_graph` (`py/cogant/export/typed_export.py`). This is distinct from the **GNN package** companions (`model.gnn.json`, `state_space.json`, …) emitted under `gnn_package/` — see [Overview](overview.md) and [`gnn/json_export.py`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/gnn/json_export.py).

### Top-level shape

```json
{
  "metadata": {
    "repo_uri": "file:///path/to/repo",
    "languages": ["python"],
    "version": "1.0",
    "created_at": "2026-04-10T12:00:00+00:00",
    "updated_at": "2026-04-10T12:00:00+00:00",
    "evidence_sources": ["static"],
    "custom_metadata": {},
    "node_count": 320,
    "edge_count": 1250
  },
  "nodes": [ ... ],
  "edges": [ ... ]
}
```

### Node objects

Each entry mirrors `cogant.schemas.core.Node` as serialized by the exporter:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable node id |
| `kind` | string | `NodeKind` value (e.g. `function`, `class`, `module`) |
| `name` | string | Short name |
| `qualified_name` | string | Fully qualified symbol name |
| `path` | string \| null | File or module path |
| `language` | string \| null | Source language tag |
| `source_range` | object \| null | Line/column span when available |
| `metadata` | object | Language-specific extras (visibility, decorators, …) |
| `created_at` | string | ISO-8601 timestamp |

Semantic **roles**, translation **confidence**, and similar fields appear in higher-level bundle or training views; see [Data representations](../reference/data_representations.md) for the conceptual shape when those layers attach them.

### Edge objects

Each entry mirrors `cogant.schemas.core.Edge`:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable edge id |
| `source_id` | string | Source node id |
| `target_id` | string | Target node id |
| `kind` | string | `EdgeKind` value (e.g. `calls`, `imports`) |
| `weight` | number | Default `1.0` |
| `metadata` | object | Additional relationship data |
| `evidence_sources` | array | Provenance tags |
| `created_at` | string | ISO-8601 timestamp |

### Related surfaces

- **GNN package JSON** — sections and companions under `gnn_package/`; [Overview](overview.md).
- **Configuration** — `ExportConfig` compression and bundle options: [`ExportConfig`](https://github.com/cogant-contributors/cogant/blob/main/cogant/py/cogant/config/schema.py) (`compression`: `none` \| `gzip` \| `zstd`).
- **See also** — [See also](see_also.md), [Validation](validation.md).
