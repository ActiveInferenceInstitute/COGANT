# cogant-statespace/src

Rust source for state-space types. The crate implements state variables, observations, actions, transitions, and model cardinality helpers.

## Files

- `lib.rs` - public crate API, unit tests, and FFI-facing helpers when applicable.

## Verification

From [`../../`](../../):

```bash
cargo test -p cogant-statespace
cargo check -p cogant-statespace
```
