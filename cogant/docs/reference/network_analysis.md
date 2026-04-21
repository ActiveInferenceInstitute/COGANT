# Network Analysis API Reference

## Overview

The graph analysis module (`cogant.graph.analysis`) provides advanced network analysis for program graphs: metrics, centrality computation, community detection, cycle detection, and path analysis. Uses pure Python with optional NetworkX acceleration.

## GraphAnalyzer

Analyzes program graph structure and properties.

### Initialization

```python
from cogant.graph.analysis import GraphAnalyzer

analyzer = GraphAnalyzer(graph)
```

The analyzer detects if NetworkX is available and uses it for acceleration. Fallback to pure Python if unavailable.

### Methods

#### compute_metrics()

Compute overall graph metrics.

```python
def compute_metrics(self) -> GraphMetrics:
    """
    Compute overall graph metrics.

    Returns:
        GraphMetrics with computed values
    """
```

**GraphMetrics:**
```python
@dataclass
class GraphMetrics:
    node_count: int
    """Number of nodes in the graph."""

    edge_count: int
    """Number of edges in the graph."""

    density: float
    """Graph density: actual_edges / possible_edges. Range [0, 1]."""

    avg_degree: float
    """Average degree (in + out) per node."""

    max_degree: int
    """Maximum degree of any node."""

    connected_components: int
    """Number of connected components."""

    is_dag: bool
    """True if the graph is acyclic (directed acyclic graph)."""

    diameter: int | None
    """Diameter of graph if connected, None if disconnected."""

    clustering_coefficient: float
    """Average clustering coefficient. Range [0, 1]."""
```

**Interpretation:**
- **Density** [0, 1]: Higher = more interconnected
  - 0.0: Disconnected graph
  - 0.1-0.3: Sparse (typical code)
  - 0.5+: Dense (high coupling)
- **Clustering Coefficient** [0, 1]: Local clustering (transitivity)
  - Higher = more "communities" or "cliques"
- **is_dag**: True = no circular dependencies (ideal)
- **Diameter**: Maximum shortest path length
  - Higher = more "spread out"

#### compute_centrality()

Compute per-node centrality scores using multiple algorithms.

```python
def compute_centrality(self) -> CentralityScores:
    """
    Compute centrality scores for all nodes.

    Uses betweenness, degree, PageRank, and closeness algorithms.

    Returns:
        CentralityScores with per-node scores
    """
```

**CentralityScores:**
```python
@dataclass
class CentralityScores:
    betweenness_centrality: dict[str, float] = field(default_factory=dict)
    """How often a node lies on shortest paths. Range [0, 1].

    High score = node is a critical bridge/bottleneck.
    """

    degree_centrality: dict[str, float] = field(default_factory=dict)
    """Degree normalized by max possible. Range [0, 1].

    High score = node is a hub (many connections).
    """

    pagerank: dict[str, float] = field(default_factory=dict)
    """PageRank score (importance based on incoming edges). Range [0, 1].

    High score = node is important in the graph structure.
    """

    closeness_centrality: dict[str, float] = field(default_factory=dict)
    """Inverse of average distance to all other nodes. Range [0, 1].

    High score = node is central (few hops to reach others).
    """
```

**Centrality Interpretation:**
| Metric | High Score Means | Low Score Means |
|--------|------------------|-----------------|
| **Betweenness** | Critical bottleneck; many paths go through | Not on important paths |
| **Degree** | Hub; many direct connections | Peripheral; few connections |
| **PageRank** | Important; pointed to by important nodes | Unimportant; not pointed to by important nodes |
| **Closeness** | Central; few hops to reach others | Peripheral; far from others |

#### detect_cycles()

Detect cycles using Tarjan's strongly connected components algorithm.

```python
def detect_cycles(self) -> CycleDetection:
    """
    Detect cycles in the graph.

    Uses Tarjan's algorithm for strongly connected components (O(V+E)).

    Returns:
        CycleDetection with cycles and SCCs
    """
```

**CycleDetection:**
```python
@dataclass
class CycleDetection:
    has_cycles: bool
    """True if any cycle exists in the graph."""

    cycles: list[list[str]] = field(default_factory=list)
    """List of cycles (each cycle is a list of node IDs).

    Example: [['A', 'B', 'C', 'A'], ['D', 'E', 'D']]
    """

    strongly_connected_components: list[frozenset[str]] = field(default_factory=list)
    """Strongly connected components (Tarjan's algorithm).

    Each component is a set of nodes reachable from each other.
    """
```

**Interpretation:**
- **has_cycles = True**: Graph contains one or more cycles (not a DAG)
  - Design smell: circular dependencies between modules
  - May indicate: tight coupling, difficult to test
- **Cycles list**: Each cycle is a closed path (A → B → C → A)
- **SCCs**: Maximal sets of mutually reachable nodes
  - SCC with 1 node = acyclic
  - SCC with N > 1 nodes = cycle(s) present

#### detect_communities()

Detect communities (clusters) in the graph using Louvain algorithm (if NetworkX available).

```python
def detect_communities(self) -> list[frozenset[str]]:
    """
    Detect communities in the graph.

    Uses Louvain algorithm (if NetworkX available).
    Pure-Python fallback uses greedy clustering.

    Returns:
        List of communities (each community is a frozenset of node IDs)

    Raises:
        ImportError: If NetworkX unavailable and no fallback available
    """
```

**Interpretation:**
- Communities are clusters of densely-connected nodes
- Useful for identifying modules/subsystems
- Example: [{'A', 'B', 'C'}, {'D', 'E', 'F'}]

#### analyze_paths()

Analyze paths between two nodes.

```python
def analyze_paths(
    self,
    source_id: str,
    target_id: str,
    max_depth: int = 5
) -> PathAnalysis:
    """
    Analyze paths from source to target node.

    Args:
        source_id: Source node ID
        target_id: Target node ID
        max_depth: Maximum search depth for all_paths

    Returns:
        PathAnalysis with shortest path, all paths, critical path
    """
```

**PathAnalysis:**
```python
@dataclass
class PathAnalysis:
    shortest_path: list[str] | None
    """Shortest path from source to target, or None if no path.

    Example: ['main', 'process', 'validate', 'error_handler']
    """

    all_paths: list[list[str]] = field(default_factory=list)
    """All paths from source to target (up to max_depth).

    Limited to prevent exponential blowup.
    """

    critical_path: list[str] = field(default_factory=list)
    """Longest path in a DAG (if graph is acyclic).

    Indicates critical path in project (longest chain of dependencies).
    """
```

**Interpretation:**
- **shortest_path**: Minimum hops from A to B (e.g., coupling strength)
- **all_paths**: May reveal unexpected call chains or dependencies
- **critical_path**: In DAGs, longest path indicates project depth

#### find_hotspots()

Identify hotspots: hubs, bottlenecks, sources, sinks.

```python
def find_hotspots(self) -> HotspotAnalysis:
    """
    Identify hotspots in the graph.

    Hubs = high-degree nodes (many connections)
    Bottlenecks = high betweenness (many paths through)
    Sources = no incoming edges (entry points)
    Sinks = no outgoing edges (dead ends)

    Returns:
        HotspotAnalysis with hotspots
    """
```

**HotspotAnalysis:**
```python
@dataclass
class HotspotAnalysis:
    hubs: list[tuple[str, int]] = field(default_factory=list)
    """Highest-degree nodes: (node_id, degree).

    Hubs are central coordination points; changes here affect many others.
    """

    bottlenecks: list[tuple[str, float]] = field(default_factory=list)
    """Highest betweenness nodes: (node_id, centrality).

    Bottlenecks are critical paths; many dependencies flow through.
    """

    sinks: list[str] = field(default_factory=list)
    """Nodes with no outgoing edges.

    Sinks are leaf modules; low-level utilities or endpoints.
    """

    sources: list[str] = field(default_factory=list)
    """Nodes with no incoming edges.

    Sources are entry points; top-level drivers or main functions.
    """
```

**Interpretation:**
- **Hubs**: High-priority for refactoring/testing (changes affect many)
- **Bottlenecks**: Critical infrastructure; failures have broad impact
- **Sources**: Entry points; application flow starts here
- **Sinks**: Utilities/dependencies; used but don't call others

## Common Patterns

### Find the Most Important Node (by PageRank)

```python
analyzer = GraphAnalyzer(graph)
centrality = analyzer.compute_centrality()

top_nodes = sorted(
    centrality.pagerank.items(),
    key=lambda x: x[1],
    reverse=True
)[:5]

print("Top 5 important nodes:")
for node_id, score in top_nodes:
    print(f"  {node_id}: {score:.4f}")
```

### Find Bottleneck Nodes

```python
hotspots = analyzer.find_hotspots()

print("Bottleneck nodes (high betweenness):")
for node_id, score in hotspots.bottlenecks[:5]:
    print(f"  {node_id}: {score:.4f}")
```

### Analyze Circular Dependencies

```python
cycles = analyzer.detect_cycles()

if cycles.has_cycles:
    print(f"Found {len(cycles.cycles)} cycles:")
    for cycle in cycles.cycles:
        print(f"  {' → '.join(cycle)} → {cycle[0]}")
else:
    print("Graph is acyclic (DAG)")
```

### Find Path Between Two Modules

```python
paths = analyzer.analyze_paths("main", "database.query")

if paths.shortest_path:
    print(f"Shortest path ({len(paths.shortest_path)} hops):")
    print(f"  {' → '.join(paths.shortest_path)}")
else:
    print("No path found")
```

### Find Communities (Subsystems)

```python
communities = analyzer.detect_communities()

for i, community in enumerate(communities):
    print(f"Community {i}: {len(community)} nodes")
    nodes = [graph.nodes[nid].name for nid in community if nid in graph.nodes]
    print(f"  {', '.join(nodes)}")
```

### Identify Critical Subsystems

```python
metrics = analyzer.compute_metrics()
centrality = analyzer.compute_centrality()
hotspots = analyzer.find_hotspots()

print(f"Graph density: {metrics.density:.2f} (sparse={metrics.density < 0.1})")
print(f"Number of components: {metrics.connected_components}")
print(f"Is acyclic: {metrics.is_dag}")

print(f"\nCritical hubs (high degree):")
for node_id, degree in hotspots.hubs[:3]:
    node = graph.nodes[node_id]
    print(f"  {node.name}: {degree} connections")

print(f"\nCritical bottlenecks (high betweenness):")
for node_id, score in hotspots.bottlenecks[:3]:
    node = graph.nodes[node_id]
    print(f"  {node.name}: {score:.4f}")
```

## Performance Notes

| Method | Time Complexity | Space | Notes |
|--------|-----------------|-------|-------|
| compute_metrics() | O(V+E) | O(V) | Fast, always use first |
| compute_centrality() | O(V²) or O(V+E) with NX | O(V) | ~1-5s for 1000 nodes |
| detect_cycles() | O(V+E) | O(V) | Tarjan's algorithm, very fast |
| detect_communities() | O(E) to O(V²) | O(V) | Louvain (NX) or greedy (fallback) |
| analyze_paths() | O(V+E*depth) | O(V) | Exponential if many paths exist |
| find_hotspots() | O(V²) | O(V) | Uses centrality scores |

## See Also

- `py/cogant/graph/analysis.py` — Implementation
- `py/cogant/graph/AGENTS.md` — Agent guide with usage patterns
- `py/cogant/graph/README.md` — Module overview
