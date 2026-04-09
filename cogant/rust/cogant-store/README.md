# cogant-store — Persistent Graph Storage

Persistent storage and indexing for large graphs (optional).

## Contents
- src/lib.rs — PersistentStore, indexing, snapshots

## Features
- RocksDB or SQLite backend
- Multi-level indexing (by source, type, attribute)
- Incremental updates and transactions
- Snapshot/restore for reproducibility
- Optional compression

## Build

```bash
cargo build --release
cargo test
```

## Dependencies
- rocksdb or rusqlite — Persistent storage
- cogant-core — Type definitions

## Performance

1M-node graph:
- Load from disk: < 5s
- Single node lookup: < 1ms
- Range query: < 100ms
