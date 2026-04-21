## Memory Management

### In Python
- Objects freed by reference counting
- Large graphs may trigger garbage collection
- Generators used for streaming processing

### In Rust
- Stack allocation for small structures
- Heap allocation for graphs (vec, hashmap)
- RAII for resource cleanup
- No garbage collection overhead

### Memory Limits

Target: <2GB for 1M function projects on 4GB machine
