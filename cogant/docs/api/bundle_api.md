## Bundle API

The `Bundle` class provides convenient accessors for analysis results.

### Summary

```python
# Get repository summary
summary = bundle.repo_summary()
# Returns: {
#   "target": "...",
#   "file_count": 123,
#   "language_distribution": {"python": 45, "go": 30, ...},
#   "total_errors": 0
# }
```

### Program Graph

```python
# Get program graph
graph = bundle.program_graph()
# Returns: {
#   "type": "program_graph",
#   "nodes": [...],
#   "edges": [...],
#   "statistics": {...}
# }

# Node count
num_nodes = len(graph.get("nodes", []))

# Edge types
edge_types = set(e.get("type") for e in graph.get("edges", []))
```

### State Space Model

```python
# Get semantic state space
state_space = bundle.state_space_model()
# Returns: {
#   "type": "state_space_model",
#   "states": [...],
#   "observations": [...],
#   "actions": [...],
#   "policies": [...]
# }

# Access components
states = state_space.get("states", [])
observations = state_space.get("observations", [])
actions = state_space.get("actions", [])
policies = state_space.get("policies", [])
```

### Process Model

```python
# Get process/execution model
process_model = bundle.process_model()
# Returns: {
#   "type": "process_model",
#   "stages": [...],
#   "dependencies": [...],
#   "timeline": [...]
# }
```

### Validation Report

```python
# Get validation results
validation = bundle.validation_report()
# Returns: {
#   "type": "validation",
#   "passed": True,
#   "checks": {...},
#   "warnings": [...]
# }

# Check if validation passed
if validation.get("passed"):
    print("Validation successful")
```

### GNN Markdown

```python
# Generate markdown representation
markdown = bundle.gnn_markdown()
# Returns formatted markdown string describing the GNN

# Save to file
with open("gnn_report.md", "w") as f:
    f.write(markdown)
```

### Rendering HTML Site

```python
# Generate full interactive HTML site
index_path = bundle.render_site("html_site/")

# Creates:
# - html_site/index.html
# - html_site/graph/program_graph.html
# - html_site/models/state_space.html
# - html_site/models/process.html
# - html_site/provenance/index.html
# - html_site/assets/style.css
# - html_site/assets/*.js
```

### JSON Export

```python
# Export bundle as JSON string
json_str = bundle.to_json()

# Save to file
bundle.save_json("bundle.json")

# Load from file
import json
with open("bundle.json") as f:
    data = json.load(f)
```

