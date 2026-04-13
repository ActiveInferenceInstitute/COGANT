# Graph — Program Graph Construction and Querying

The graph module constructs and queries a unified program graph from normalized static and dynamic analysis. Nodes represent code entities (modules, classes, functions, variables). Edges represent relationships (calls, imports, data flow, coverage).

## Module Overview

ProgramGraphBuilder constructs the graph incrementally. It accepts repo_uri and provides methods to add nodes (kind, name, qualified_name, optional path/language/source_range/metadata) and edges (source_id, target_id, kind, optional weight/metadata/evidence_sources). Each node receives a stable ID via IdentityResolver; edges are deduplicated and merged by ID. Nodes track languages; metadata is updated on finalize().

ProgramGraph is the result: a dict-based storage of Node and Edge objects, GraphMetadata (repo_uri, analysis_timestamp, languages, edges_per_kind counts), and query support.

GraphQuery provides filtering and analysis: find_nodes_by_kind(), filter_nodes() by kind/language/name_pattern/metadata, filter_edges() by kind/source/target/weight. Additional methods support path finding, centrality (betweenness, closeness), and reachability analysis (reachable_from, transitive_closure).

GraphMerger combines multiple graphs (static + dynamic) with conflict resolution. It supports "union" (combine all edges), "static_priority" (static overrides dynamic), and "dynamic_priority" (dynamic overrides). MergeConflict records conflicts (edge_weight_mismatch, evidence_divergence, etc.). MergeProvenance documents the merge: timestamp, source graphs, conflicts, counts of added/updated nodes/edges.

## API Reference

ProgramGraphBuilder class with methods:
- add_node(kind, name, qualified_name, path=None, language=None, source_range=None, metadata=None) — Add node and return Node object
- add_edge(source_id, target_id, kind, weight=1.0, metadata=None, evidence_sources=None) — Add edge and return Edge object
- finalize() — Finalize graph and return ProgramGraph

GraphQuery class with methods:
- find_nodes_by_kind(kind) — Find all nodes of given kind
- filter_nodes(kind=None, language=None, name_pattern=None, metadata_filter=None) — Filter nodes by criteria
- filter_edges(kind=None, source_id=None, target_id=None, min_weight=0.0) — Filter edges by criteria
- reachable_from(node_id) — Find all nodes reachable from node_id
- shortest_path(source_id, target_id) — Compute shortest path between nodes
- transitive_closure(node_id) — Find all transitive dependencies

GraphMerger class with methods:
- merge(graphs, conflict_resolution="union") — Merge list of graphs (convenience method)
- merge_graphs(static_graph, dynamic_graph, conflict_resolution="union") — Merge two graphs and return (merged_graph, provenance)

Data classes:
- ProgramGraph(metadata, nodes, edges) — Graph: metadata and dicts of Node and Edge by ID
- GraphMetadata(repo_uri, analysis_timestamp, languages, edges_per_kind) — Graph-level metadata
- MergeConflict(conflict_type, source_graph, entity_id, details, resolution) — Conflict record
- MergeProvenance(timestamp, source_graphs, conflicts, edges_added, edges_updated, nodes_added) — Merge record
