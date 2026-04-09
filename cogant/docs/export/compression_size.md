## Compression & Size

### Compression Options

```yaml
export:
  compression: gzip  # or deflate, bz2, lz4, none
```

### Size Estimates

| Format | 1K Functions | 10K Functions | 100K Functions |
|--------|-------------|---------------|----------------|
| JSON (uncompressed) | 2MB | 20MB | 200MB |
| JSON (gzip) | 0.3MB | 3MB | 30MB |
| PyG (no embeddings) | 1MB | 10MB | 100MB |
| PyG (with embeddings) | 300MB | 3GB | 30GB |
| HDF5 | 0.5MB | 5MB | 50MB |

### Recommendations

- **Small projects** (<10K funcs): JSON uncompressed
- **Medium projects** (10-100K funcs): JSON gzip or PyG
- **Large projects** (>100K funcs): HDF5 or split format

