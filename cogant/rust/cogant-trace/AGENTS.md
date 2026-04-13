# Agents — rust/cogant-trace

## Owner
Runtime Lead

## Responsibilities
- High-performance trace collection and filtering
- Privacy-preserving trace sanitization
- Compression and aggregation
- Integration with dynamic analysis

## Coordination
- Consumes raw traces from instrumentation
- Outputs filtered traces to Python dynamic/
- Optional layer; not critical path

## Files
- Cargo.toml — Crate manifest
- src/lib.rs — TraceCollector, filters, compression
