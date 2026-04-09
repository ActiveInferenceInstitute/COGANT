## Convert to Node
node = normalizer.to_node(normalized, node_id="canonical_id")
```

**Metadata Extraction:**
- Extracts common fields: visibility, is_abstract, is_static, decorators, type_hints
- Language-specific: Python (is_async, is_generator), JavaScript (is_arrow, export_type), Java (modifiers, annotations)

---

### 2. Graph Construction Layer

#### 2.1 ProgramGraphBuilder (`cogant/graph/builder.py`)

**Purpose:** Construct typed program graphs incrementally.

**Key Methods:**
- `add_node()` - Add typed node with language, source range, metadata
- `add_edge()` - Add relationship between nodes
- `get_neighbors()` - Get adjacent nodes
- `find_path()` - BFS shortest path between nodes
- `get_subgraph()` - Extract subgraph by node list
- `get_connected_components()` - Find all connected components
- `find_cycles()` - Detect cycles in the graph
- `get_statistics()` - Graph metrics

**Example:**
```python
from cogant.graph.builder import ProgramGraphBuilder
from cogant.schemas.core import NodeKind, EdgeKind

builder = ProgramGraphBuilder(repo_uri="https://github.com/example/repo")

