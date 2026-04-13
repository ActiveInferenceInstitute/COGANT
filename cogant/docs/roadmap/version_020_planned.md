# Version 0.2.0 — Archived (Shipped)

> **ARCHIVED.** All items in this file were delivered and shipped as part of the
> v0.2.0–v0.5.0 release arc. The authoritative record is
> [version_050_shipped.md](version_050_shipped.md).

The features originally planned here shipped as follows:

| Item | Outcome |
|------|---------|
| JavaScript/TypeScript parser (tree-sitter) | ✅ Shipped v0.4.0 |
| Rust parser (tree-sitter, PyO3 FFI) | ✅ Shipped v0.4.0 |
| Language-specific rule sets | ✅ Shipped v0.2.0 (YAML DSL + 22 Python rules) |
| Parquet export | ✅ Shipped wave-21 |
| Incremental caching | ✅ Shipped v0.5.0 (`--incremental <git-ref>`, 19.6× speedup) |
| Execution trace integration | 🔲 Deferred to v0.7.x (see [feature_backlog.md](feature_backlog.md#4)) |
| Custom validators framework | ✅ Shipped v0.2.0 |
| Plugin system | ✅ Shipped v0.2.0 (entry-point registry) |
| Docker image | ✅ Shipped v0.1.0 (`cogant/Dockerfile`, EXPOSE 8080) |
| Performance benchmarks | ✅ Shipped v0.4.0 (Chart.js dashboard) |
| Test suite >80% coverage | ✅ Shipped v0.5.0 (83.42% coverage, 2,129 tests) |
| DGL format | 🔲 Won't fix — see [feature_backlog.md § Won't Fix](feature_backlog.md#wont-fix--out-of-scope) |
| HDF5 format | 🔲 Won't fix — Parquet covers the analytics use case |
| Custom binary format | 🔲 Deferred indefinitely |
| Parallel file processing | 🔲 Planned v1.0 ([version_100_planned.md](version_100_planned.md#h6)) |
| Java parser | 🔲 Planned v0.6.x ([version_060_planned.md](version_060_planned.md#l1)) |
