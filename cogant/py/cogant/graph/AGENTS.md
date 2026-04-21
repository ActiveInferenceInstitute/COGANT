# Agents — py/cogant/graph

## Owner
Graph Construction

## What Is the Graph Module

The `graph/` module builds and analyzes **program graphs** — the central data structure of COGANT. A program graph is a typed, directed, acyclic graph (DAG) where **nodes represent code entities** (functions, classes, modules) and **edges represent relationships** (calls, imports, data flow, control flow). Nodes carry metadata (complexity, coupling, type info); edges carry kind labels (CALLS, IMPORTS, READS, WRITES, etc.).

The graph is constructed in stage 3 from normalized facts produced by `static/` (stage 2). It feeds into translation (stage 4), state space construction (stage 5), and all downstream stages.

## Pipeline Integration

```
stage 2: static/        → SymbolInfo, ImportEdge, CallEdge, ...
    ↓
stage 2.5: normalize/   → LanguageFact (canonical form)
    ↓
stage 3: graph/         → ProgramGraph (nodes + edges)
    ↓
stage 4: translate/     → SemanticMappings (HIDDEN_STATE, OBSERVATION, ACTION, ...)
    ↓
stages 5-10: statespace, process, export, validate, ...
```

The graph is the **single point of truth** for the codebase structure. All analyses depend on graph quality and completeness.

## Responsibilities
ProgramGraphBuilder accumulates nodes and edges, assigns stable IDs via IdentityResolver, and deduplicates. GraphQuery filters and traverses: find by kind/language, path finding, reachability, transitive closure, centrality. GraphMerger combines static and dynamic graphs with conflict strategies (union, static_priority, dynamic_priority) and records provenance. GraphAnalyzer computes network metrics, centrality, communities, cycles, hotspots.

## Core Components

### Existing: Graph Construction & Query (2 files)

**builder.py** — `ProgramGraphBuilder`
- Accumulates nodes and edges from normalized facts
- Assigns stable IDs via `IdentityResolver` (deterministic, content-based)
- Deduplicates nodes by ID
- Methods: `add_node(node)`, `add_edge(source_id, target_id, kind)`, `build() -> ProgramGraph`
- Consumes: `LanguageFact` records from `normalize/`

**query.py** — `GraphQuery`
- Filters nodes: by kind, by language, by name pattern
- Path finding: `find_path(source, target)`, `all_paths(source, target)`
- Reachability: `is_reachable(source, target)`, `transitive_closure(node)`
- Traversal: BFS, DFS, topological sort
- Methods: `find_by_kind()`, `find_by_language()`, `get_neighborhood()`, `filter_by_edge_type()`, `find_by_role()` (new)
- Optional: NetworkX acceleration (if installed)

### Network analysis (`analysis.py`)

**analysis.py** — `GraphAnalyzer`
- Computes network metrics: density, avg degree, clustering coefficient, diameter, connectivity
- Centrality analysis: betweenness, degree, PageRank, closeness (9 methods). Betweenness uses
  NetworkX `betweenness_centrality(..., normalized=True)` when NetworkX is available; otherwise
  a pure-Python fallback scales by the maximum score so values stay in **[0, 1]**.
- Community detection: Louvain algorithm (optional NetworkX), modularity scoring
- Cycle detection: Tarjan's strongly connected components (SCC), cycle listing
- Path analysis: shortest paths, all paths (up to max_depth), critical paths in DAGs
- Hotspot analysis: hubs (high-degree), bottlenecks (high betweenness), sources, sinks
- Output: `GraphMetrics`, `CentralityScores`, `CycleDetection`, `PathAnalysis`, `HotspotAnalysis`
- Methods: `compute_metrics()`, `compute_centrality()`, `detect_communities()`, `detect_cycles()`, `analyze_paths()`, `find_hotspots()`

**merge.py** — `GraphMerger` (existing)
- Combines static and dynamic graphs with configurable conflict strategies
- Strategies: union (merge all), static_priority (prefer static facts), dynamic_priority (prefer dynamic facts)
- Records provenance (which fact came from which source)
- Handles edge deduplication and metadata merging

### `GraphQuery` API surface

```python
class GraphQuery:
    # Existing
    find_by_kind(kind: NodeKind) -> List[Node]
    find_by_language(language: str) -> List[Node]
    find_path(source_id: str, target_id: str) -> List[str] | None
    all_paths(source_id: str, target_id: str, max_depth: int = 5) -> List[List[str]]
    is_reachable(source_id: str, target_id: str) -> bool
    transitive_closure(node_id: str) -> Set[str]

    # New in v0.5.0+
    find_by_role(role: str) -> List[Node]  # HIDDEN_STATE, OBSERVATION, ACTION, POLICY, etc.
    get_neighborhood(node_id: str, depth: int = 1, direction: str = 'both') -> Set[str]
    filter_by_edge_type(edge_type: str) -> List[Edge]
    get_subgraph(node_ids: Set[str]) -> ProgramGraph
```

### Data Representations

```python
@dataclass
class Node:
    id: str
    name: str
    kind: NodeKind  # FUNCTION, CLASS, MODULE, VARIABLE, ...
    language: str  # 'python', 'javascript', 'typescript'
    file_path: Path
    line_start: int
    line_end: int
    metadata: dict[str, Any]  # complexity, coupling, type_info, role, ...
    is_public: bool
    stability_score: float  # 0.0-1.0 (1.0 = stable)

@dataclass
class Edge:
    source_id: str
    target_id: str
    kind: EdgeKind  # CALLS, IMPORTS, READS, WRITES, CONSTRAINT, CONFIGURATION, ...
    confidence: float  # 0.0-1.0 (1.0 = certain)
    metadata: dict[str, Any]

@dataclass
class ProgramGraph:
    nodes: dict[str, Node]  # id -> Node
    edges: list[Edge]
    source_language: str
    repo_root: Path
    metadata: dict[str, Any]  # pipeline stage, timestamp, version, ...
```

### Analysis Results

```python
@dataclass
class GraphMetrics:
    node_count: int
    edge_count: int
    density: float  # [0, 1]
    avg_degree: float
    max_degree: int
    connected_components: int
    is_dag: bool
    diameter: int | None
    clustering_coefficient: float  # [0, 1]

@dataclass
class CentralityScores:
    betweenness_centrality: dict[str, float]
    degree_centrality: dict[str, float]
    pagerank: dict[str, float]
    closeness_centrality: dict[str, float]

@dataclass
class CycleDetection:
    has_cycles: bool
    cycles: list[list[str]]  # Each cycle is a list of node IDs
    strongly_connected_components: list[frozenset[str]]

@dataclass
class PathAnalysis:
    shortest_path: list[str] | None
    all_paths: list[list[str]]
    critical_path: list[str]  # Longest path in DAG

@dataclass
class HotspotAnalysis:
    hubs: list[tuple[str, int]]  # (node_id, degree)
    bottlenecks: list[tuple[str, float]]  # (node_id, betweenness)
    sinks: list[str]  # No outgoing edges
    sources: list[str]  # No incoming edges
```

## Common Usage Patterns

### Build a Graph from Static Analysis

```python
from pathlib import Path
from cogant.graph.builder import ProgramGraphBuilder
from cogant.normalize import normalize_facts

# Get normalized facts from static analysis
facts = normalize_facts(static_analysis_results)

# Build graph
builder = ProgramGraphBuilder()
for fact in facts:
    builder.add_node(fact.to_node())
    for edge in fact.to_edges():
        builder.add_edge(edge.source_id, edge.target_id, edge.kind)

graph = builder.build()
print(f"Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
```

### Query the Graph

```python
from cogant.graph.query import GraphQuery

query = GraphQuery(graph)

# Find all functions
functions = query.find_by_kind("FUNCTION")
print(f"Functions: {[n.name for n in functions]}")

# Find all local imports
local_imports = query.filter_by_edge_type("IMPORTS_LOCAL")
print(f"Local import edges: {len(local_imports)}")

# Check if main calls utils
path = query.find_path("main", "utils.helper")
if path:
    print(f"Path from main to utils.helper: {' -> '.join(path)}")

# Get all nodes reachable from main
reachable = query.transitive_closure("main")
print(f"From main, can reach {len(reachable)} nodes")

# Find all nodes with high complexity (metadata filtering)
complex_nodes = [n for n in graph.nodes.values()
                 if n.metadata.get('cyclomatic_complexity', 0) > 10]
print(f"High-complexity functions: {[n.name for n in complex_nodes]}")
```

### Analyze the Graph

```python
from cogant.graph.analysis import GraphAnalyzer

analyzer = GraphAnalyzer(graph)

# Overall metrics
metrics = analyzer.compute_metrics()
print(f"Density: {metrics.density:.2f}")
print(f"Is DAG: {metrics.is_dag}")
print(f"Clustering coefficient: {metrics.clustering_coefficient:.2f}")

# Centrality: find important nodes
centrality = analyzer.compute_centrality()
top_betweenness = sorted(
    centrality.betweenness_centrality.items(),
    key=lambda x: x[1],
    reverse=True
)[:5]
print("Top bottlenecks (betweenness):")
for node_id, score in top_betweenness:
    print(f"  {node_id}: {score:.2f}")

# Community detection (optional, requires networkx)
try:
    communities = analyzer.detect_communities()
    for i, community in enumerate(communities):
        print(f"Community {i}: {community}")
except ImportError:
    print("NetworkX not available for community detection")

# Cycle detection
cycles = analyzer.detect_cycles()
if cycles.has_cycles:
    print(f"Found {len(cycles.cycles)} cycles")
    for cycle in cycles.cycles:
        print(f"  {' <- '.join(cycle)}")
else:
    print("Graph is acyclic (DAG)")

# Hotspot analysis
hotspots = analyzer.find_hotspots()
print("Hubs (high-degree nodes):")
for node_id, degree in hotspots.hubs[:3]:
    print(f"  {node_id}: degree {degree}")

print("Bottlenecks (high betweenness):")
for node_id, score in hotspots.bottlenecks[:3]:
    print(f"  {node_id}: {score:.2f}")

# Path analysis
source, target = "main", "database.query"
paths = analyzer.analyze_paths(source, target)
if paths.shortest_path:
    print(f"Shortest path from {source} to {target}:")
    print(f"  {' -> '.join(paths.shortest_path)}")
else:
    print(f"No path from {source} to {target}")
```

### Merge Static and Dynamic Graphs

```python
from cogant.graph.merge import GraphMerger

# Assume static_graph and dynamic_graph are both ProgramGraph instances

merger = GraphMerger()
merged = merger.merge_graphs(
    static_graph,
    dynamic_graph,
    conflict_resolution='dynamic_priority'  # Prefer dynamic facts
)

print(f"Merged graph: {len(merged.nodes)} nodes")
print(f"Provenance: {merged.metadata.get('provenance', {})}")
```

### Find Functions by Complexity Threshold

```python
query = GraphQuery(graph)

# All functions with CC > 10
high_cc = [
    n for n in graph.nodes.values()
    if n.kind.value == 'FUNCTION'
    and n.metadata.get('cyclomatic_complexity', 0) > 10
]
print(f"High cyclomatic complexity: {len(high_cc)}")
for node in sorted(high_cc, key=lambda n: n.metadata['cyclomatic_complexity'], reverse=True)[:5]:
    print(f"  {node.name}: CC={node.metadata['cyclomatic_complexity']}")

# All nodes in zone of pain (high instability + concrete)
unstable = [
    n for n in graph.nodes.values()
    if n.metadata.get('instability', 0) > 0.8
    and n.metadata.get('distance_from_main_sequence', 0) > 0.3
]
print(f"Zone of pain (unstable): {len(unstable)}")
```

## Coordination

### Input Sources
- **static/** — SymbolInfo, ImportEdge, CallEdge, TypeInfo, DataFlowEdge, ComplexityEntry, CouplingMetrics
- **dynamic/** (optional) — runtime call traces, execution profiles
- **normalize/** — LanguageFact (canonical form of all facts)

### Output Sinks
- **translate/** — ProgramGraph for translation rule application
- **statespace/** — graph metadata feeds into state space construction
- **export/** — serialized graphs (JSON, GraphML, Parquet)
- **validate/** — scoring and quality checks
- **viz/** — visualization of graph structure and properties

### Guarantees
- **Deterministic**: same source → same graph (stable IDs)
- **Deduplicatable**: same node appears once (by ID)
- **Queryable**: all node kinds, edge kinds, and metadata accessible
- **Analyzable**: rich metrics (density, centrality, cycles, communities)
- **Mergeable**: static + dynamic graphs can be combined with conflict resolution

## How to Extend

### Add a New Node Kind
1. Extend `NodeKind` enum in `py/cogant/schemas/core.py`
2. Update `ProgramGraphBuilder` to recognize new kind from LanguageFact
3. Update tests with fixtures containing new kind
4. Update `GraphQuery` filters if needed (e.g., `find_by_role()`)

### Add a New Edge Kind
1. Extend `EdgeKind` enum in `py/cogant/schemas/core.py`
2. Update `ProgramGraphBuilder.add_edge()` to handle new kind
3. Update analysis methods that traverse edges (e.g., `compute_centrality()`)
4. Update merge strategies if conflict resolution differs for new kind

### Add a New Graph Query Method
1. Add method to `GraphQuery` class
2. Implement using existing graph structure (nodes, edges, metadata)
3. For NetworkX-based queries, check if `nx` is available and provide pure-Python fallback
4. Add tests with fixtures

### Add a New Analysis Algorithm
1. Add method to `GraphAnalyzer` class
2. Implement pure-Python version (no external deps)
3. Optionally use NetworkX if available for acceleration
4. Return a dataclass result (e.g., `CommunityDetectionResult`)
5. Document expected graph properties (e.g., "Works only on DAGs")

## Performance & Optimization

- **Graph size**: Typical medium projects 1000-10000 nodes, 5000-50000 edges
- **Query performance**: O(V+E) for traversals, O(V^2) for all-pairs analysis
- **Optional NetworkX acceleration**: ~2-5× speedup for dense graphs if installed
- **Incremental updates**: GraphMerger supports selective re-merging without full rebuild

## See Also

- `py/cogant/graph/README.md` — module overview
- `py/cogant/schemas/` — Node, Edge, ProgramGraph, NodeKind, EdgeKind definitions
- `py/cogant/static/` — produces facts that feed into graph construction
- `py/cogant/translate/` — consumes graph and applies translation rules
- `py/cogant/export/` — serializes graph to JSON, GraphML, Parquet, etc.
