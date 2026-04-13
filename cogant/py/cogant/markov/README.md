# cogant.markov — Markov blanket extraction

`cogant.markov` turns a COGANT program graph into an Active-Inference-style
Markov blanket: the four-role `(internal, sensory, active, external)`
partition that identifies the minimal set of boundary nodes which
render the interior conditionally independent of the environment.

## What is a Markov blanket here?

Given a program graph and a seed set *S* that represents the "system
of interest", every node is assigned exactly one role:

| Role       | Symbol | Definition in COGANT                                          |
|------------|:------:|---------------------------------------------------------------|
| Internal   |   μ    | Node in *S* whose only neighbours are also in *S*.            |
| Sensory    |   s    | Node in *S* with at least one incoming edge from outside *S*. |
| Active     |   a    | Node in *S* with at least one outgoing edge to outside *S*.   |
| External   |   η    | Node not in *S*.                                              |

The boundary `B = s ∪ a` is the Markov blanket: *μ* is conditionally
independent of *η* given *B*.

## Public API

```python
from cogant.markov import (
    MarkovBlanketExtractor,
    partition_by_seeds,
    serialize_blanket,
    build_blanket_network,
)
```

Typical workflow:

```python
extractor = MarkovBlanketExtractor(program_graph)
blanket = extractor.extract(strategy="auto")               # pick a module automatically
# or extractor.extract(strategy="module", module_names=["core"])
# or extractor.extract(strategy="mapping_kind", mapping_kinds=["hidden_state"],
#                     semantic_mappings=bundle.artifacts["_semantic_mappings"])

network = build_blanket_network(program_graph, blanket)
record  = serialize_blanket(blanket, program_graph)
```

## Seed strategies

| Strategy        | What it does                                                                |
|-----------------|-----------------------------------------------------------------------------|
| `explicit`      | Use the caller-supplied set of node ids verbatim.                           |
| `module`        | Take one or more named modules and their `CONTAINS` closure.                |
| `kind`          | Aggregate every node of a given `NodeKind` (e.g. every CLASS).              |
| `mapping_kind`  | Use the `graph_fragment_node_ids` of every semantic mapping with one of the requested kinds (default: `hidden_state`). |
| `auto`          | Pick the module with the highest cohesion/(cohesion+coupling+1) score. Deterministic. |

## Integration points

- `cogant.gnn.package.GNNPackageBuilder` emits `markov_blanket.json` and
  `markov_network.json` in the bundle when a graph is present.
- `cogant.gnn.formatter` adds a `# Markov Blanket` section to the
  canonical markdown export.
- `cogant.viz.boundary` consumes the blanket to render a Mermaid
  diagram of the collapsed four-role network.

## Files

- `blanket.py`   — `MarkovBlanket`, `BlanketRole`, `partition_by_seeds`, `serialize_blanket`.
- `extractor.py` — `MarkovBlanketExtractor` with seed-selection strategies.
- `network.py`   — `BlanketNetwork`, `build_blanket_network`, Mermaid renderer.

Every function is pure with respect to the input graph; no global state
is held. The partitioner is O(V + E) thanks to a single precomputed
bidirectional adjacency map.
