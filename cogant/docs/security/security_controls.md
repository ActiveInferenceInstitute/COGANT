## Security Controls

### Input Validation

```python
# File discovery
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_FILES = 10000
MAX_TOTAL_SIZE = 1 * 1024**3  # 1GB

# Parsing
PARSE_TIMEOUT = 30  # seconds per file
MAX_MEMORY_PER_FILE = 500 * 1024 * 1024  # 500MB

# Configuration
ALLOWED_CONFIG_PATHS = {
    "discovery", "parsing", "translation",
    "statespace", "validation", "export"
}
FORBIDDEN_PATH_CHARS = {"..", "/", "\\"}
```

### Resource Limits

```rust
// Rust graph construction
const MAX_NODES: usize = 10_000_000;
const MAX_EDGES: usize = 100_000_000;
const MAX_RECURSION_DEPTH: usize = 1000;

// Memory per stage
const STAGE_MEMORY_LIMIT: usize = 4 * 1024 * 1024 * 1024;  // 4GB
```

### Type Safety

All IRs enforced with:
- Type-checked serialization (serde + custom validators)
- Schema validation (JSON schema)
- Field bounds checking
- Enum validation (no unknown variants)
