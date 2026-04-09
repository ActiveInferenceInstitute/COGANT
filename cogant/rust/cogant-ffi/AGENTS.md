# Agents — rust/cogant-ffi

## Owner
Infra Lead

## Responsibilities
- Python FFI bindings via PyO3
- Type conversions and memory safety
- Async interop and GIL management
- Version compatibility and deprecation

## Coordination
- Aggregates exports from all Rust crates
- Provides Python bindings in cogant.rust module
- Must maintain API stability

## Files
- Cargo.toml — Crate manifest
- src/lib.rs — PyO3 bindings and type conversions
