## Dependencies
deps = query.get_dependency_chain(node_id, max_depth=5)
```

#### 2.3 GraphMerger (`cogant/graph/merge.py`)

**Purpose:** Merge static and dynamic analysis graphs, handling conflicts.

**Key Methods:**
- `merge_graphs()` - Merge two graphs with conflict resolution
- `merge_multiple_graphs()` - Sequential merge of multiple graphs
- `get_merge_statistics()` - Track conflicts and changes

**Conflict Resolution Strategies:**
- `union` - Take maximum weight/confidence
- `static_priority` - Prefer static analysis
- `dynamic_priority` - Prefer dynamic/runtime evidence

**Example:**
```python
from cogant.graph.merge import GraphMerger

merger = GraphMerger()
