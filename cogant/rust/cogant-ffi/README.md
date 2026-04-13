# cogant-ffi — Python Bindings

PyO3-based FFI bindings exposing Rust implementations to Python.

## Contents
- src/lib.rs — Module definitions, type conversions, PyModule setup

## Exposed modules (from Python)

```python
from cogant.rust import (
    Graph, GraphBuilder, QueryEngine,
    RuleEngine, StateSpaceCompiler,
    TensorGenerator, PersistentStore
)
```

## Build

```bash
cargo build --release
maturin develop  # or pip install -e .
```

## Dependencies
- PyO3 — Python bindings
- All cogant-* crates

## Testing

```bash
pytest tests/
```

Integration with Python API is tested in py/cogant/tests/integration/
