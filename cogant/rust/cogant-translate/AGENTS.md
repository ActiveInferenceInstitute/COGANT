# Agents — rust/cogant-translate

## Owner
Semantic Lead

## Responsibilities
- High-performance rule evaluation and graph transformations
- Parallel rule execution
- Confidence scoring at scale
- Memory-efficient incremental compilation

## Coordination
- Consumes rules from Python translate/ module
- Operates on graphs from cogant-graph
- Outputs confidence-scored graph to Python

## Files
- Cargo.toml — Crate manifest
- src/lib.rs — RuleEngine, rule compilation, execution
