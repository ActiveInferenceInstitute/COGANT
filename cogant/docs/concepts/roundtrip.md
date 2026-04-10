# The forward-reverse cycle

COGANT's most ambitious claim is that the mapping between source code and Active Inference models is not one-way. The forward pipeline translates code into a [GNN](gnn.md). The reverse pipeline synthesizes code back from a GNN. Together they form a cycle:

```
code --forward--> GNN --reverse--> code'
```

This page explains both directions, the theoretical bound on roundtrip fidelity, and the Galois connection framing that makes the claim precise.

## Forward: code to GNN

The forward pipeline is a six-stage content-preserving transformation:

1. **Source to graph.** Tree-sitter parses the source code into an AST, then COGANT's graph builder extracts a typed [program graph](program_graph.md) with nodes (MODULE, CLASS, FUNCTION, METHOD, VARIABLE) and edges (CALLS, READS, WRITES, IMPORTS, CONTAINS). Information is re-indexed, not discarded -- the graph preserves every structural relationship in the AST except whitespace and comments.

2. **Graph to semantic mappings.** The [rule engine](role_assignment.md) runs 19 translation rules against the graph. Each rule that fires produces a `SemanticMapping` with a confidence score. Conflicts are resolved by `(priority, confidence)` ordering.

3. **Mappings to state space.** The state-space compiler projects the role assignments onto an ordered basis of hidden states, observations, and actions. Each basis element corresponds to a node in the graph.

4. **State space to A/B/C/D matrices.** The [matrix builder](active_inference.md) counts evidence edges and normalizes to produce well-formed probability distributions. The result is a complete Active Inference model.

5. **Matrices to GNN markdown.** The `GNNMarkdownFormatter` emits a valid upstream GNN v1.1 file with `StateSpaceBlock`, `Connections`, `InitialParameterization`, and `ActInfOntologyAnnotation` sections.

6. **GNN package.** The `GNNPackageBuilder` writes `model.gnn.md`, `model.gnn.json`, satellite matrix files, the [Markov blanket](markov_blanket.md) partition, and provenance metadata into a self-contained directory.

Each stage is content-preserving: the output contains at least as much semantic information as the input, plus the new structure imposed by that stage. The GNN file is not a summary of the code -- it is a re-encoding.

## Reverse: GNN to code

The reverse pipeline reads a GNN package and synthesizes a Python package that, when analyzed by a forward run, would produce an isomorphic GNN. The current v0.1.0 implementation provides scaffolding in `py/cogant/reverse/`:

```python
from pathlib import Path
from cogant.gnn.runner import load_gnn_package
from cogant.simulate.runner import SimulationRunner

# Load a forward-produced GNN package
gnn = load_gnn_package(Path("output/calculator/gnn_package"))

# The matrices define the synthesized package's behavior
print("Hidden states:", [s.name for s in gnn.state_space.variables.values()])
# ['display', 'accumulator', 'history_len']

print("Observations:", [o.name for o in gnn.state_space.observations.values()])
# ['get_display', 'get_history', 'assert_display']

print("Actions:", [a.name for a in gnn.state_space.actions.values()])
# ['_execute_operation']
```

The synthesized `code'` has:

- One class per hidden-state cluster (each mutable attribute group becomes a class)
- One method per action (each ACTION mapping becomes a method that writes to the state variables it is connected to in the B matrix)
- One getter per observation (each OBSERVATION mapping becomes a read-only method)
- Module-level constants for preferences and priors (C and D vectors)

The synthesized code is not a copy of the original -- it is a **minimal implementation** that preserves the generative model structure. Variable names come from the GNN labels, not the original source.

## The isomorphism measure

How do you know the roundtrip worked? COGANT defines the isomorphism measure as a comparison of two GNN bundles:

```
epsilon = distance(GNN_original, GNN_roundtrip)
```

where `distance` compares:

1. **State space dimensionality** -- same number of hidden states, observations, actions
2. **A matrix structure** -- same non-zero pattern in the likelihood matrix
3. **B matrix structure** -- same non-zero pattern in the transition matrix
4. **C vector** -- same preference ordering
5. **D vector** -- same prior distribution
6. **Blanket partition** -- same internal/sensory/active/external assignment

A perfect roundtrip has epsilon = 0. In practice, the forward pipeline discards information that cannot be recovered:

- **Whitespace and comments** are lost at stage 1 (AST extraction)
- **Dead code** that has no edges in the program graph is invisible to the rule engine
- **Name choices** are preserved as labels but the synthesizer may normalize them
- **Control flow ordering** within a function body is not captured by the graph

These losses establish a theoretical lower bound on epsilon. The roundtrip is idempotent **up to these losses**: `forward(reverse(forward(code)))` produces the same GNN as `forward(code)`.

## The Galois connection framing

The formal version (documented in the codebase's theory pages) frames the forward and reverse pipelines as a Galois connection between two partially ordered sets:

- **Programs**, ordered by behavioral refinement (P1 refines P2 if P1 can do everything P2 can do)
- **Generative models**, ordered by model inclusion (M1 includes M2 if M1's state space contains M2's)

The forward pipeline `F` is the **lower adjoint**: it maps a program to the smallest generative model that captures its structure. The reverse pipeline `R` is the **upper adjoint**: it maps a generative model to the largest program that is consistent with it.

The Galois connection guarantees:

```
F(R(F(code))) = F(code)     -- forward is idempotent after one roundtrip
R(F(R(gnn)))  = R(gnn)      -- reverse is idempotent after one roundtrip
```

This is why COGANT claims the mapping is an isomorphism "up to epsilon" rather than an exact bijection. The Galois connection is the strongest claim that can be made when the forward pipeline is information-lossy (as all compilers are).

## A concrete GNN roundtrip example

Given the Calculator fixture, forward analysis produces a GNN with:

```
## StateSpaceBlock
- s_f0: display (int, cardinality=10)
- s_f1: accumulator (float, cardinality=1)

## ActInfOntologyAnnotation
- display: HiddenState
- get_display: Observation
- _execute_operation: Action
```

Reverse synthesis produces a Python package with:

```python
class CalculatorModel:
    """Synthesized from GNN StateSpaceBlock."""
    def __init__(self):
        self.display: int = 0         # s_f0
        self.accumulator: float = 0.0  # s_f1

    def get_display(self) -> int:
        """Observation modality for display."""
        return self.display

    def execute_operation(self, op: str, value: float):
        """Action: transitions display and accumulator."""
        self.accumulator = self.accumulator  # B matrix placeholder
        self.display = self.display          # B matrix placeholder
```

Running `cogant forward` on this synthesized code produces a GNN with the same `StateSpaceBlock` dimensions, the same A matrix non-zero pattern, and the same blanket partition -- confirming epsilon is near zero for this fixture.

## Current limitations

- `cogant reverse` and `cogant roundtrip` are available CLI subcommands as of v0.5.0.
- Only Python synthesis output is supported.
- The B matrix placeholder code does not implement real transition logic -- it preserves the structural skeleton.
- Complex control flow (loops, conditionals, exception handling) is not synthesized.

## Further reading

- [What is a GNN?](gnn.md) -- the format that the roundtrip preserves
- [Active Inference from a programmer's perspective](active_inference.md) -- the A/B/C/D matrices being compared
- [Program graphs in COGANT](program_graph.md) -- the intermediate representation in the forward pipeline
- [How COGANT assigns roles](role_assignment.md) -- the rule engine that populates the GNN
