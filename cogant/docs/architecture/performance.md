## Performance

### Benchmarks (Target)

- 10K functions: <30s (4-core machine)
- 100K functions: <5min (4-core machine)
- 1M functions: <1hr (4-core machine)

### Critical Paths

1. **Parsing**: Most time-consuming (parallelizable)
2. **Graph construction**: Fast (Rust, in-memory)
3. **Rule application**: Fast (parallel)
4. **Export**: Medium (format-specific)

### Optimization Techniques

- Incremental caching (skip unchanged stages)
- Parallel file processing
- Lazy evaluation (streaming)
- Index structures (fast lookup)
- Memory-mapped I/O (for large files)

