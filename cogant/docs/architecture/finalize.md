## Finalize
graph = builder.finalize()
```

#### 2.2 GraphQuery (`cogant/graph/queries.py`)

**Purpose:** Advanced queries and analysis on program graphs.

**Key Methods:**
- `filter_nodes()` - Filter by kind, language, name pattern, metadata
- `filter_edges()` - Filter by kind, source, target, weight
- `find_shortest_path()` - BFS to find shortest path
- `find_all_paths()` - Find all paths up to max depth
- `compute_degree_centrality()` - Node importance by degree
- `compute_betweenness_centrality()` - Node importance by shortest paths
- `compute_closeness_centrality()` - Average distance to all nodes
- `find_connected_components()` - All connected subgraphs
- `find_cycles()` - All cycles in graph
- `extract_subgraph_by_kind()` - Filter by node types
- `get_dependency_chain()` - All dependencies up to depth

**Example:**
```python
from cogant.graph.queries import GraphQuery
from cogant.schemas.core import NodeKind, EdgeKind

query = GraphQuery(graph)
