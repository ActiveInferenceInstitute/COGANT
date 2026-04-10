# Markov blankets in codebases

A Markov blanket is a boundary in a graph that makes one set of nodes conditionally independent from another. In COGANT, it is the formal mechanism for answering the question: "Where does this module end and the rest of the system begin?" This page explains the mathematics, the COGANT implementation, and why the result matters for software architecture.

## The mathematical definition

Given a graph of random variables, the **Markov blanket** of a set S is the minimal set of nodes B such that S is conditionally independent of everything outside S given B. In simpler terms: if you know the values of every node in B, learning about nodes outside B tells you nothing new about nodes inside S.

In Active Inference, the blanket is further partitioned into:

- **Sensory states (s)** -- blanket nodes that receive information from outside (edges pointing inward)
- **Active states (a)** -- blanket nodes that send information outward (edges pointing outward)

The full partition is:

```
External (eta)  --->  Sensory (s)  --->  Internal (mu)
                <---  Active  (a)  <---
```

Internal nodes only talk to the outside world through sensory and active nodes. This is the Markov property.

## How COGANT partitions code nodes

COGANT's `partition_by_seeds` function in `py/cogant/markov/blanket.py` implements a pure graph-theoretic partitioning algorithm. It takes two inputs: a `ProgramGraph` and a seed set S (the "system of interest"). Every node in the graph is assigned exactly one role:

```python
from cogant.markov.blanket import partition_by_seeds, BlanketRole
from cogant.markov.extractor import MarkovBlanketExtractor

# Extract automatically -- picks the module with best cohesion
extractor = MarkovBlanketExtractor(graph)
blanket = extractor.extract(strategy="auto")

# Inspect the partition
for node_id, role in blanket.roles.items():
    node = graph.get_node(node_id)
    print(f"{node.name}: {role.value}")
    # Output:
    # Calculator: internal
    # get_display: sensory
    # _execute_operation: active
    # __main__: external
```

The algorithm works on the undirected projection of the program graph:

1. A node `n` in S with **no neighbours outside S** is **internal**. It is fully encapsulated -- nothing outside the seed set touches it directly.

2. A node `n` in S with **at least one external neighbour** is a boundary node. COGANT then checks directed edges:
   - If an external node has a directed edge **into** `n` (information flowing in), `n` is **sensory**.
   - If `n` has a directed edge **out to** an external node (information flowing out), `n` is **active**.
   - If both directions exist, `n` defaults to **active** (it has causal influence outward) and is flagged as `bidirectional` in metadata.

3. A node `n` **outside S** is **external**. If it is adjacent to at least one node in S, it is tagged with `neighbour` metadata.

The partition is deterministic: same graph and same seeds always produce the same result.

## Seed selection strategies

The `MarkovBlanketExtractor` offers five strategies for choosing the seed set:

The default **auto** strategy scores every module by its cohesion-to-coupling ratio:

```
score(module) = internal_edges / (internal_edges + boundary_edges + 1)
```

The module with the highest score becomes the seed set. This naturally selects the most self-contained module -- the one whose blanket is the tightest boundary.

## Why this matters for software architecture

The Markov blanket partition is a formal measurement of encapsulation quality:

**Internal ratio** measures how much of the system of interest is truly private. A high internal ratio (e.g., 0.83 for the Calculator fixture) means most nodes are fully encapsulated. A low ratio (e.g., 0.13 for the event-pipeline fixture) means almost every node is on the boundary -- the module leaks its internals.

**Boundary ratio** measures the surface area of the public API relative to the system size. A small boundary ratio indicates a narrow, well-defined interface. A large ratio indicates a "god class" or "leaky abstraction" where too many internal details are exposed.

These are not subjective assessments. They are computed directly from the [program graph](program_graph.md) edges. COGANT's validation results on control-positive fixtures demonstrate the range:

| Fixture | Total nodes | Internal | Sensory | Active | External | Internal ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| calculator | 12 | 10 | 1 | 0 | 1 | 0.833 |
| event_pipeline | 23 | 3 | 1 | 1 | 18 | 0.130 |
| flask_mini | 26 | 4 | 1 | 2 | 19 | 0.154 |

The calculator has excellent encapsulation -- nearly all its state is internal, with a single sensory node (the getter) as the observation channel. The event pipeline and Flask app have far more porous boundaries, which matches architectural intuition: event-driven systems intentionally expose many connection points.

## The Markov blanket in the GNN output

The blanket partition is written to `markov_blanket.json` in the [GNN package](gnn.md). It populates the Active Inference model's four-way split: internal nodes become hidden state variables in the `StateSpaceBlock`, sensory nodes become observation modalities, active nodes become action variables, and external nodes are the environment.

This connection between the graph-theoretic partition and the [A/B/C/D matrices](active_inference.md) is what makes COGANT's analysis more than a visualization -- the blanket defines the system boundary that the entire generative model is built around.

## A practical example

Consider a module `auth.py` that has a `SessionManager` class with private fields `_token_cache` and `_refresh_timer`, a public `verify_token()` method that reads the cache, and a `refresh()` method that calls an external OAuth provider:

```python
class SessionManager:
    def __init__(self):
        self._token_cache = {}     # Internal (mu) -- no external edges
        self._refresh_timer = 0    # Internal (mu) -- no external edges

    def verify_token(self, token: str) -> bool:
        # Sensory (s) -- external callers read through this
        return token in self._token_cache

    def refresh(self):
        # Active (a) -- calls out to external OAuth provider
        new_tokens = self.oauth_client.fetch_tokens()
        self._token_cache = new_tokens
```

COGANT's blanket extractor would partition this as: `_token_cache` and `_refresh_timer` are **internal**, `verify_token` is **sensory** (incoming information flow from callers), and `refresh` is **active** (outgoing information flow to the OAuth provider). The OAuth client itself is **external**. This partition exactly captures the module's architectural role.

## Further reading

- [Active Inference from a programmer's perspective](active_inference.md) -- how the blanket feeds into A/B/C/D matrices
- [How COGANT assigns roles](role_assignment.md) -- the rule engine that complements blanket partitioning
- [Program graphs in COGANT](program_graph.md) -- the graph structure that blanket extraction operates on
