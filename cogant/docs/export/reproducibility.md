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

## Future verification certificates

A future `verification_certificate.json` should be a separate optional export artifact, not a replacement for `manifest.json` or `GNNValidator`. The certificate would bind the source snapshot digest, pipeline configuration digest, emitted GNN package checksums, and runtime trace digest so consumers can verify internal artifact consistency for a specific run. This is inspired by commit-and-audit systems such as ProvableWorldModel, but it would remain a COGANT artifact-integrity certificate unless a real inference proof verifier is added; it must not be described as a Freivalds/Merkle/Fiat-Shamir proof of model execution by default.

### See also

- [Validation](validation.md) — checks applied before artifacts are trusted.
- [Overview](overview.md) — manifest and package layout.
