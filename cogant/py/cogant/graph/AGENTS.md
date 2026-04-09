# Agents — py/cogant/graph

## Owner
Graph Construction

## Responsibilities
ProgramGraphBuilder accumulates nodes and edges, assigns stable IDs via IdentityResolver, and deduplicates. GraphQuery filters and traverses: find by kind/language, path finding, reachability, transitive closure, centrality. GraphMerger combines static and dynamic graphs with conflict strategies (union, static_priority, dynamic_priority) and records provenance.

## Coordination
Input: Normalized facts and analyzed code (nodes and edges from static/dynamic analysis converted by normalize/). Output: ProgramGraph consumed by validation, export, and visualization. The graph is the central artifact.

## How to Extend
Add node kind: extend NodeKind enum in schemas/core.py. Add edge kind: extend EdgeKind enum. Add query: extend GraphQuery with new filter_* or analysis_* methods. Add merge strategy: extend GraphMerger.merge_graphs conflict_resolution handling.
