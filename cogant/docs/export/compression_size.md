## Compression and size

### Compression options

Bundle and export serialization honor `ExportConfig` in `cogant.yaml` / pipeline config:

```yaml
export:
  compression: gzip   # none | gzip | zstd
  compression_level: 6  # 1–9 when applicable
```

Values outside this set are not accepted by the current schema; extend `ExportConfig` in code before documenting new algorithms here.

### Size estimates

The table below is **illustrative** — measure on your own corpora (`du`, bundle manifests) before relying on numbers for capacity planning.

| Format | 1K nodes (order of magnitude) | 10K nodes | 100K nodes |
|--------|------------------------------|-----------|------------|
| JSON (uncompressed) | ~2 MB | ~20 MB | ~200 MB |
| JSON (gzip) | ~0.3 MB | ~3 MB | ~30 MB |
| PyG tensor bundle (no embeddings) | ~1 MB | ~10 MB | ~100 MB |
| PyG (with name/doc embeddings) | much larger | much larger | much larger |

Embeddings dominate when enabled; keep them off unless you need them.

### Recommendations

- **Small graphs:** JSON with defaults is usually enough.
- **Large graphs:** prefer `gzip` or `zstd`, split work across [incremental export](incremental_export.md) patterns, and use Parquet/GraphML from the main bundle when columnar or tool interop matters.

### See also

- [Overview](overview.md) — full artifact list.
- [Reproducibility](reproducibility.md) — checksums and manifest fields.
