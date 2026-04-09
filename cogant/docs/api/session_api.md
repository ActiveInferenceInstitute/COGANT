## Session API

The `Session` class manages the analysis pipeline state step-by-step.

### Creating a Session

```python
from cogant import Session

# From local path
session = Session.from_target("./my_repo")

# From URL
session = Session.from_target("https://github.com/user/repo")
```

### Extracting Analysis

```python
# Static analysis: ingest summary + per-module parse stats
syntax_tree = session.extract_static()
# Returns: {
#   "type": "syntax_tree",
#   "target": "...",
#   "ingest": {"file_count": ..., "language_distribution": {...}, ...},
#   "modules": [...],
#   "symbols": {"python_modules_parsed": N},
#   "nodes": [], "edges": []  # reserved; graph lives on build_graph()
# }

# Dynamic analysis: traces, coverage
trace_bundle = session.extract_dynamic()
# Returns: {
#   "type": "trace_bundle",
#   "traces": [...],
#   "coverage": {...}
# }
```

### Building Program Graph

```python
# Build from static analysis
program_graph = session.build_graph()
# Returns: {
#   "type": "program_graph",
#   "nodes": [...],
#   "edges": [...],
#   "metadata": {...}
# }
```

### Translating to GNN

```python
# Convert to GNN representation
gnn_model = session.translate_to_gnn()
# Returns: {
#   "type": "gnn_model",
#   "nodes": [...],
#   "edges": [...],
#   "features": {...}
# }
```

### Compiling State Space

```python
# Extract semantic state space
state_space = session.compile_state_space()
# Returns: {
#   "type": "state_space_model",
#   "states": [...],
#   "observations": [...],
#   "actions": [...],
#   "policies": [...]
# }
```

### Exporting Results

```python
# Export all artifacts to directory
session.export_all("output/")

# Results are written as JSON:
# - output/syntax_tree.json
# - output/program_graph.json
# - output/gnn_model.json
# - output/state_space.json
```

