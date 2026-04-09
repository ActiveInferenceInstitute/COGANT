# Agents — rust/cogant-store

## Owner
Infra Lead

## Responsibilities
- Persistent graph storage (RocksDB or similar)
- Indexing and retrieval optimization
- Incremental updates and snapshots
- Disk/memory trade-offs

## Coordination
- Optional persistence layer
- Consumed by Python api/ for large graph caching
- Provides snapshot/restore capability

## Files
- Cargo.toml — Crate manifest
- src/lib.rs — PersistentStore, index management
