# Agents - rust/.cargo

## Scope

Workspace-level Cargo configuration only.

## Rules

- Keep configuration portable across macOS and Linux CI.
- Do not add build artifacts or generated bindings here.
- After changing config, run from [`..`](../):

```bash
cargo fmt --check
cargo check --workspace
cargo test --workspace
```
