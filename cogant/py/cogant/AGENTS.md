# Agents — py/cogant

## Owner
Runtime Lead

## Responsibilities
- Core Python library structure and public API surface
- Python/Rust FFI and interop layer
- Package initialization and dependency management
- Cross-module type contracts and import routing

## Coordination
- Subsystem modules (api/, cli/, ingest/, etc.) implement functionality; Runtime Lead ensures cohesion
- Static analysis helpers (static/) and schema definitions (schemas/) are shared resources
- Plugins (plugins/) extend this core; Plugin system must remain backward-compatible

## Files
- __init__.py — Package root and version
