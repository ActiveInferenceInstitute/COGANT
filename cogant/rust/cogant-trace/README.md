# cogant-trace — Trace Collection and Processing

High-performance trace collection and privacy-preserving filtering.

## Contents
- src/lib.rs — TraceCollector, event filters, aggregation

## Features
- In-process and subprocess trace collection
- PII/sensitive data filtering
- Compression (zstd)
- Streaming processing for large traces
- Integration with pytest, unittest plugins

## Build

```bash
cargo build --release
cargo test
```

## Dependencies
- zstd — Compression
- serde — Serialization

## Performance

Tracing 100K function calls: < 100ms overhead
