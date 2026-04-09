## Secure Coding Practices

### Rust

- **Memory safety**: No unsafe code except where necessary
- **Bounds checking**: petgraph handles graph invariants
- **Error handling**: Result types, no panics in production
- **Type system**: Leverage compiler for safety
- **SAST**: Run clippy on all code

Example:
```rust
// Safe: bounds checked
pub fn get_node(&self, id: &StableId) -> Option<&NodeData> {
    self.id_to_index.get(id).and_then(|idx| {
        self.graph.node_weight(*idx)
    })
}
```

### Python

- **No eval/exec**: Never execute user code
- **Path validation**: Use pathlib, reject `..`
- **Input validation**: Validate all external input
- **Type hints**: Use type hints for clarity
- **SAST**: Run bandit and pylint

Example:
```python
from pathlib import Path
import os

def load_config(config_path: str) -> Dict:
    path = Path(config_path)
    
    # Prevent directory traversal
    if ".." in path.parts:
        raise ValueError("Path traversal not allowed")
    
    # Prevent absolute paths
    if path.is_absolute():
        raise ValueError("Absolute paths not allowed")
    
    # Prevent symlink attacks
    if path.is_symlink():
        raise ValueError("Symlinks not allowed")
    
    return yaml.safe_load(path.read_text())
```

