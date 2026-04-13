## Reproducibility

Export includes metadata for verification:

```json
{
  "export_metadata": {
    "cogant_version": "0.5.0",
    "export_timestamp": "2026-04-10T12:00:00Z",
    "graph_id": "graph_myproject",
    "node_count": 320,
    "edge_count": 1250,
    "input_hash": "sha256:abc123...",
    "config_hash": "sha256:def456...",
    "feature_config": {
      "node_features": ["kind", "role", "confidence", "degree"],
      "edge_features": ["kind", "confidence"],
      "embeddings": false
    }
  }
}
```

Concrete keys vary by bundle stage; treat `manifest.json` and any `export_metadata` block as the source of truth for a given run.

### See also

- [Validation](validation.md) — checks applied before artifacts are trusted.
- [Overview](overview.md) — manifest and package layout.

