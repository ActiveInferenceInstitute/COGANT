## System Overview

COGANT is a layered system with clear separation of concerns:

```
┌─────────────────────────────────────────────┐
│ User-Facing Layer                           │
│ - CLI (cogant command)                      │
│ - Python API (cogant package)               │
│ - Configuration System (YAML)               │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ Orchestration Layer (Python)                │
│ - Pipeline coordination                     │
│ - Stage execution                           │
│ - Error handling & recovery                 │
│ - Incremental caching                       │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ Analysis Layer (Python)                     │
│ - Language-specific parsers                 │
│ - Entity extraction                         │
│ - Translation rules                         │
│ - State space modeling                      │
│ - Validation                                │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ Core Layer (Rust)                           │
│ - Graph operations (petgraph)               │
│ - Data serialization                        │
│ - GNN export formatting                     │
│ - FFI bridge (PyO3)                         │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ Storage Layer                               │
│ - File system (JSON, MessagePack)           │
│ - In-memory caches                          │
│ - Index structures                          │
└─────────────────────────────────────────────┘
```

