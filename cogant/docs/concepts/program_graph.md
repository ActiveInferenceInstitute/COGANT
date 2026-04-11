# Program graphs in COGANT

> **What this page is:** A reference to COGANT's central IR — what nodes and edges exist, how tree-sitter extracts them, and the JSON schema downstream stages consume.
>
> **Prerequisites:** Familiarity with abstract syntax trees and call graphs is helpful but not required.
>
> **Reading time:** ~12 minutes
>
> **Next steps:** [How COGANT assigns roles](role_assignment.md) · [Markov blankets in codebases](markov_blanket.md) · [Tutorial: Small repo walkthrough](../tutorials/02_small_repo_walkthrough.md)

The program graph is COGANT's central data structure. Every analysis -- [role assignment](role_assignment.md), [Markov blanket extraction](markov_blanket.md), [matrix derivation](active_inference.md), and [GNN emission](gnn.md) -- operates on this graph. This page explains what nodes and edges exist, how tree-sitter extracts them, and what the JSON schema looks like.

## What is a program graph?

A program graph is a directed, typed multigraph where:

- **Nodes** represent code entities: modules, classes, functions, methods, variables, configurations, events
- **Edges** represent relationships: calls, reads, writes, imports, containment, inheritance, error handling

Unlike an AST (which represents syntax), a program graph represents semantics: it captures what calls what, what reads what, and what contains what, regardless of how the code is formatted.

The `ProgramGraph` dataclass lives in `py/cogant/schemas/graph.py`. It holds two dictionaries -- `nodes: Dict[str, Node]` and `edges: Dict[str, Edge]` -- plus metadata about the repository, languages, and analysis timestamp.

## Node kinds

Every node has a `NodeKind` enum value from `py/cogant/schemas/core.py`. The primary kinds for source code analysis are:

| Kind | What it represents | Example |
| --- | --- | --- |
| MODULE | A Python file or package | `auth.py`, `utils/__init__.py` |
| CLASS | A class definition | `class UserService` |
| FUNCTION | A top-level function | `def validate_email()` |
| METHOD | A method inside a class | `def get_user(self)` |
| VARIABLE | A named value (attribute, constant) | `self._cache`, `MAX_RETRIES` |

Additional kinds for specialized nodes:

| Kind | What it represents |
| --- | --- |
| ENDPOINT | An API route or handler |
| EVENT | A pub/sub event definition |
| PARAMETER | A function parameter |
| RETURN_VALUE | A return type or value |
| DATA_STRUCTURE | A container type (dict, list, dataclass) |
| CONFIGURATION | A config file or settings class |
| FEATURE_FLAG | A feature toggle |
| TEST | A test function |
| ASSERTION | An assert statement |

Each node carries:

```python
@dataclass
class Node:
    id: str                              # Deterministic hash of (repo, path, qualified_name)
    kind: NodeKind                       # Type enum
    name: str                            # Human-readable name
    qualified_name: str                  # Fully qualified (e.g., "auth.UserService.get_user")
    path: Optional[str]                  # File path
    language: Optional[str]              # "python", "javascript", etc.
    source_range: Optional[Dict]         # Start/end line and column
    metadata: Dict[str, Any]             # Decorators, visibility, docstrings, etc.
```

## Edge kinds

Edges are typed by `EdgeKind`. The categories are:

### Structural edges

| Kind | Meaning | Example |
| --- | --- | --- |
| CONTAINS | Parent contains child | Module CONTAINS Class, Class CONTAINS Method |
| IMPORTS | Module imports from another | `auth.py` IMPORTS `utils.py` |
| INHERITS | Class extends another | `Admin` INHERITS `User` |
| IMPLEMENTS | Class implements interface | (used in typed languages) |
| DEPENDS_ON | General dependency | Module DEPENDS_ON external package |

### Data flow edges

| Kind | Meaning | Example |
| --- | --- | --- |
| READS | Function reads a variable | `get_user` READS `self._cache` |
| WRITES | Function writes a variable | `update_user` WRITES `self._cache` |
| RETURNS | Function returns a value | `get_user` RETURNS `User` |
| CALLS | Function calls another | `main` CALLS `get_user` |

### Control flow edges

| Kind | Meaning | Example |
| --- | --- | --- |
| THROWS | Function raises exception | `validate` THROWS `ValueError` |
| CATCHES | Function catches exception | `handle_request` CATCHES `TimeoutError` |
| YIELDS | Generator yields value | `stream_data` YIELDS `chunk` |

### Semantic edges

| Kind | Meaning | Example |
| --- | --- | --- |
| OBSERVES | Node observes another | Logger OBSERVES EventBus |
| MUTATES | Node mutates another's state | Setter MUTATES `self._state` |
| GUARDS | Node protects another | CircuitBreaker GUARDS `api_call` |
| TRIGGERS | Node triggers another | Event TRIGGERS Handler |

## How tree-sitter extracts graphs

COGANT uses tree-sitter as its primary parser. The extraction pipeline in `py/cogant/parsers/tree_sitter_base.py` works in three passes:

**Pass 1 -- Node extraction.** Tree-sitter parses the source file into a concrete syntax tree. COGANT walks the tree looking for `class_definition`, `function_definition`, `assignment`, and `import_statement` nodes. Each becomes a `Node` in the program graph with its `source_range`, `qualified_name`, and language-specific metadata (decorators, visibility modifiers, type annotations).

**Pass 2 -- Edge extraction.** A second walk identifies relationships between nodes. When a function body contains `self.x = value`, that creates a WRITES edge from the function to the variable `x`. When a function body contains `other_func()`, that creates a CALLS edge. When a function reads `self.y` without assignment, that creates a READS edge.

**Pass 3 -- Cross-file linking.** Import statements create IMPORTS edges between modules. Inheritance declarations create INHERITS edges. After all files are parsed, the graph builder resolves qualified names across files to connect the full dependency graph.

Here is a concrete example:

```python
# Input: auth.py
class UserService:
    def __init__(self):
        self._cache = {}

    def get_user(self, user_id: str) -> dict:
        return self._cache.get(user_id)

    def update_user(self, user_id: str, data: dict):
        self._cache[user_id] = data
```

COGANT produces:

- **Nodes:** `auth` (MODULE), `UserService` (CLASS), `__init__` (METHOD), `get_user` (METHOD), `update_user` (METHOD), `_cache` (VARIABLE)
- **Edges:**
  - `auth` CONTAINS `UserService`
  - `UserService` CONTAINS `__init__`, `get_user`, `update_user`
  - `__init__` WRITES `_cache`
  - `get_user` READS `_cache`
  - `update_user` WRITES `_cache`

## The JSON schema

When serialized, a program graph looks like:

```json
{
  "metadata": {
    "repo_uri": "/path/to/repo",
    "languages": ["python"],
    "version": "1.0",
    "evidence_sources": ["static_analysis"]
  },
  "nodes": {
    "abc123": {
      "id": "abc123",
      "kind": "class",
      "name": "UserService",
      "qualified_name": "auth.UserService",
      "path": "auth.py",
      "language": "python",
      "source_range": {"start_line": 1, "end_line": 10},
      "metadata": {"decorators": [], "bases": []}
    }
  },
  "edges": {
    "edge_001": {
      "id": "edge_001",
      "kind": "contains",
      "source_id": "mod_auth",
      "target_id": "abc123",
      "metadata": {}
    }
  }
}
```

Node IDs are deterministic hashes of `(repo, path, qualified_name)`, which means the same code always produces the same graph regardless of when or where the analysis runs.

## Parser certainty

Not all edges are equally reliable. COGANT tracks `parser_certainty` (0.0 to 1.0) on each semantic mapping derived from graph edges:

- **0.90-0.95** -- Names extracted by Python AST (class names, function names, config node classification). Highest precision.
- **0.80-0.85** -- CALLS and CONTAINS edges extracted by tree-sitter. High precision.
- **0.70-0.75** -- READS/WRITES edges, CATCHES/THROWS edges, cross-module resolution. Lower precision because tree-sitter sometimes over-reports attribute accesses or misses exception hierarchies.

This certainty propagates into the [role assignment](role_assignment.md) confidence scores and ultimately into the [GNN](gnn.md) provenance metadata, so downstream consumers know how much to trust each part of the model.

## Querying the graph

The `GraphQuery` class provides convenience methods for common graph traversals:

```python
from cogant.graph.queries import GraphQuery

query = GraphQuery(graph)

# Find all classes
classes = graph.get_nodes_by_kind(NodeKind.CLASS)

# Get all outgoing edges from a node
edges = graph.get_edges_from(node.id)

# Filter edges by kind
reads = [e for e in edges if e.kind == EdgeKind.READS]
writes = [e for e in edges if e.kind == EdgeKind.WRITES]
```

The rule engine uses these queries extensively. For example, `MutatingSubsystemRule` finds all CLASS nodes, counts their WRITES/MUTATES edges, and fires when the count is at least 1. `OrchestratorRule` counts outgoing CALLS edges and fires when there are 3 or more.

## Implementation

The program-graph data type, the tree-sitter extraction passes, the cross-file linker, and the query helpers are all implemented across `cogant.ingest`, `cogant.static`, and `cogant.graph`:

| Concept on this page | Module (`py/cogant/...`) | API reference | Key class / function |
| --- | --- | --- | --- |
| Repository ingest (file enumeration, language sniff, repo manifest) | `ingest/repo.py`, `ingest/files.py`, `ingest/language_detect.py` | [`cogant.static`](../api/static.md) | `IngestRepo`, `enumerate_files` |
| Tree-sitter parser base + Python parser passes | `static/treesitter_parser.py`, `static/parser.py` | [`cogant.static` → Parser](../api/static.md#parser) | `TreeSitterParser` |
| Pass 1 — symbol / node extraction | `static/symbols.py` | [`cogant.static` → Symbols](../api/static.md#symbols) | symbol extractors |
| Pass 2 — type inference annotations | `static/types.py` | [`cogant.static` → Types](../api/static.md#types) | type inferrer |
| Pass 2 — call-graph (CALLS edges) | `static/calls.py` | [`cogant.static` → Calls](../api/static.md#calls) | call resolver |
| Pass 2 — READS / WRITES dataflow edges | `static/dataflow.py` | [`cogant.static` → Dataflow](../api/static.md#dataflow) | dataflow extractor |
| Pass 3 — IMPORTS / cross-file linking | `static/imports.py` | [`cogant.static` → Imports](../api/static.md#imports) | import resolver |
| `ProgramGraph` dataclass + `Node` / `Edge` / `NodeKind` / `EdgeKind` schemas | `schemas/graph.py`, `schemas/core.py` | [`cogant.gnn` → Package](../api/gnn.md#package) (consumer) | `ProgramGraph`, `Node`, `Edge`, `NodeKind`, `EdgeKind` |
| Graph builder (assembles the typed multigraph from extracted facts) | `graph/builder.py` | [`cogant.translate`](../api/translate.md) (consumer) | `GraphBuilder` |
| Static + dynamic graph merge | `graph/merge.py` | [dynamic_analysis_api](../api/dynamic_analysis_api.md) | `merge_graphs` |
| `GraphQuery` traversal helpers | `graph/queries.py` | [`cogant.translate` → Engine](../api/translate.md#engine) (primary consumer) | `GraphQuery` |
| Parser certainty propagation into mappings | `translate/confidence.py` | [`cogant.translate` → Confidence](../api/translate.md#confidence) | `ConfidenceTier` |

## Further reading

- [How COGANT assigns roles](role_assignment.md) -- the rules that analyze program graph structure
- [Markov blankets in codebases](markov_blanket.md) -- blanket extraction from the graph
- [What is a GNN?](gnn.md) -- the output format derived from the graph
- [The forward-reverse cycle](roundtrip.md) -- how graphs participate in the roundtrip pipeline
- [`cogant.static` API reference](../api/static.md) -- the parsing and edge-extraction modules
- [Data representations reference](../reference/data_representations.md) -- JSON schema for nodes and edges
