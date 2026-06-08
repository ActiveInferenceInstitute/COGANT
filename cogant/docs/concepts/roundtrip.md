# The forward-reverse cycle

> **What this page is:** A conceptual overview of COGANT's bidirectional pipeline — code-to-GNN, GNN-to-code, and the round-trip that closes the loop with diff-based equivalence checks.
>
> **Prerequisites:** [What is a GNN?](gnn.md), [How COGANT assigns roles](role_assignment.md).
>
> **Reading time:** ~10 minutes
>
> **Next steps:** [Tutorial: Reverse mode — GNN to code](../tutorials/06_reverse_mode.md) · [Markov blankets in codebases](markov_blanket.md) · [Active Inference for programmers](active_inference.md)

COGANT's most ambitious claim is that the mapping between source code and Active Inference models is not one-way. The forward pipeline translates code into a [GNN](gnn.md). The reverse pipeline synthesizes code back from a GNN. Together they form a cycle:

```
code --forward--> GNN --reverse--> code'
```

This page explains both directions, the role-preservation score, and the stricter invariant
ledger that determines the current v0.6 roundtrip status.

## Forward: code to GNN

The forward pipeline is a six-layer evidence transformation:

1. **Source to graph.** Tree-sitter or the Python AST front end parses source code, then COGANT's graph builder extracts a typed [program graph](program_graph.md) with nodes (MODULE, CLASS, FUNCTION, METHOD, VARIABLE) and edges (CALLS, READS, WRITES, IMPORTS, CONTAINS). The graph preserves the relationships the front end extracts; whitespace, comments, unsupported constructs, and dynamic effects remain outside the graph unless a later stage adds evidence.

2. **Graph to semantic mappings.** The [rule engine](role_assignment.md) runs 22 translation rules against the graph. Each rule that fires produces a `SemanticMapping` with a confidence score. Conflicts are resolved by `(priority, confidence)` ordering.

3. **Mappings to state space.** The state-space compiler projects the role assignments onto an ordered basis of hidden states, observations, and actions. Each basis element corresponds to a node in the graph.

4. **State space to A/B/C/D matrices.** The [matrix builder](active_inference.md) counts evidence edges and normalizes to produce well-formed probability distributions. The result is a complete Active Inference model.

5. **Matrices to GNN markdown.** The `GNNMarkdownFormatter` emits a valid upstream GNN v1.1 file with `StateSpaceBlock`, `Connections`, `InitialParameterization`, and `ActInfOntologyAnnotation` sections.

6. **GNN package.** The `GNNPackageBuilder` writes `model.gnn.md`, `model.gnn.json`, satellite matrix files, the [Markov blanket](markov_blanket.md) partition, and provenance metadata into a self-contained directory.

Each stage is traceable: the output records the source artifact, rule evidence, fallback paths,
and validation status needed to inspect what was preserved and what was approximated. The GNN
file is not a behavioral proof of the source code; it is a structured export of the extracted
program graph, semantic mappings, state-space model, and matrix defaults.

## Reverse: GNN to code

The reverse pipeline reads a GNN package and synthesizes a Python package that, when analyzed by a forward run, is compared against the original GNN through the v0.6 invariant ledger. The implementation in `py/cogant/reverse/` is exposed through the `cogant reverse` and `cogant roundtrip` CLI subcommands and emits POLICY / CONTEXT scaffolding proportional to the origin GNN's role counts:

```python
# doctest: +SKIP  # requires a pre-generated GNN package on disk
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

## The roundtrip measure

How do you know the roundtrip worked? COGANT defines the role-preservation fidelity metric as:

```
s_role = |roles_preserved| / |roles_original|
```

where the numerator counts semantic-role assignments preserved across the `forward → reverse → forward` roundtrip and the denominator counts the roles in the original GNN bundle. A perfect role-preservation score has **s_role = 1.0** (all roles preserved), and the public ROLE_PRESERVED threshold is **s_role >= 0.5**.

The v0.6 invariant ledger separately checks stronger properties:

1. **State-space shape preservation** — same hidden-state, observation, and action dimensions.
2. **A/B/C/D matrix preservation** — same matrix shapes and value deltas within tolerance.
3. **GNN-section preservation** — same required section coverage and comparable section content.
4. **Program-graph preservation** — same node/edge counts and edge-kind distributions.
5. **Generated-code health** — synthesized package imports, compiles, and passes smoke checks.

Strict `STRUCTURALLY_ISOMORPHIC` status requires those ledger checks in addition to role preservation (canonical source `cogant/evaluation/METRICS.yaml`).

> **Compatibility note:** Earlier drafts used a complementary "error" formulation in
> `ISOMORPHISM_THEOREM.md`, where ε_max = 0 meant exact recovery. The current project-wide
> convention is the role-preservation ratio above, where 1.0 is exact.

In practice, the forward pipeline discards information that cannot be recovered:

- **Whitespace and comments** are lost at stage 1 (AST extraction)
- **Dead code** that has no edges in the program graph is invisible to the rule engine
- **Name choices** are preserved as labels but the synthesizer may normalize them
- **Control flow ordering** within a function body is not captured by the graph

These losses explain why role preservation can pass while stricter graph, matrix, or generated-code invariants fail. Treat `ROLE_PRESERVED` as a useful semantic-regression tier and `STRUCTURALLY_ISOMORPHIC` as the strict tier.

## Galois Connection Framing

The theory sketch frames the forward and reverse pipelines as a restricted Galois-style relation between two partially ordered sets:

- **Programs**, ordered by behavioral refinement (P1 refines P2 if P1 can do everything P2 can do)
- **Generative models**, ordered by model inclusion (M1 includes M2 if M1's state space contains M2's)

The forward pipeline `F` is the **lower adjoint**: it maps a program to the smallest generative model that captures its structure. The reverse pipeline `R` is the **upper adjoint**: it maps a generative model to the largest program that is consistent with it.

Under that restricted role-quotient reading, the intended equations are:

```
F(R(F(code))) = F(code)     -- forward is idempotent after one roundtrip
R(F(R(gnn)))  = R(gnn)      -- reverse is idempotent after one roundtrip
```

The current package does not use "epsilon-isomorphism" as a CLI or manuscript success tier. It reports `roundtrip_status`, `role_preservation_score`, and the invariant ledger described above.

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

Running `cogant translate` on this synthesized code produces a GNN whose `StateSpaceBlock` dimensions, A matrix non-zero pattern, and blanket partition can be inspected by the roundtrip invariant ledger.

## Current limitations

- `cogant reverse` and `cogant roundtrip` are available CLI subcommands in v0.6.0.
- Only Python synthesis output is supported.
- The B matrix placeholder code does not implement real transition logic -- it preserves the structural skeleton.
- Complex control flow (loops, conditionals, exception handling) is not synthesized.

## Implementation

The forward stages live across `cogant.static`, `cogant.translate`, `cogant.statespace`, and `cogant.gnn`; the reverse stages and the ε metric live in `cogant.reverse`:

| Concept on this page | Module (`py/cogant/...`) | API reference | Key class / function |
| --- | --- | --- | --- |
| Forward stage 1 — source → AST → program graph | `static/parser.py`, `static/treesitter_parser.py`, `graph/builder.py` | [`cogant.static`](../api/static.md) | `TreeSitterParser`, graph builder |
| Forward stage 2 — graph → semantic mappings (rule fixpoint) | `translate/engine.py`, `translate/rules/` | [`cogant.translate` → Engine](../api/translate.md#engine), [`cogant.translate` → Rules](../api/translate.md#rules) | `TranslationEngine` — see [translation rules reference](../reference/translation_rules.md) |
| Forward stage 3 — mappings → state-space basis | `statespace/compiler.py` | [`cogant.statespace` → Compiler](../api/statespace.md#compiler) | `StateSpaceCompiler` |
| Forward stage 4 — state space → A/B/C/D matrices | `gnn/matrices.py` | [`cogant.gnn` → Matrix builder](../api/gnn.md#matrix-builder) | `build_matrices` |
| Forward stage 5 — matrices → GNN markdown (`model.gnn.md`) | `gnn/formatter/` | [`cogant.gnn`](../api/gnn.md) | `GNNMarkdownFormatter` |
| Forward stage 6 — `GNNPackageBuilder` writes the package directory | `gnn/package.py` | [`cogant.gnn` → Package builder](../api/gnn.md#package-builder) | `GNNPackageBuilder` |
| Reverse — `load_gnn_package()` and parser tolerant of canonical + extended sections | `gnn/runner.py`, `reverse/parser.py` | [`cogant.gnn` → Runner](../api/gnn.md#runner), [`cogant.reverse` → Parser](../api/reverse.md#parser) | `load_gnn_package`, `ReverseGNNModel` |
| Reverse — synthesis planning | `reverse/planner.py` | [`cogant.reverse` → Planner](../api/reverse.md#planner) | planner classes |
| Reverse — Python package synthesis (`synthesize_package`) | `reverse/synthesizer.py`, `reverse/matrices.py` | [`cogant.reverse` → Synthesizer](../api/reverse.md#synthesizer) | `synthesize_package` |
| Reverse — runtime-callable closures (`MatrixFunctions`) | `reverse/callable.py` | [`cogant.reverse` → Callable](../api/reverse.md#callable) | `MatrixFunctions` |
| Roundtrip role-preservation metric and idempotency checks | `reverse/metrics.py`, `reverse/idempotency.py` | [`cogant.reverse` → Metrics](../api/reverse.md#metrics), [`cogant.reverse` → Idempotency](../api/reverse.md#idempotency) | v0.6 invariant ledger plus compatibility helpers |
| Forward-pipeline orchestration consumed by `cogant roundtrip` | `pipeline/`, `cli/` | [`cogant.gnn` → Runner](../api/gnn.md#runner), [pipelinerunner_api](../api/pipelinerunner_api.md) | pipeline runner |

## Further reading

- [What is a GNN?](gnn.md) -- the format that the roundtrip preserves
- [Active Inference from a programmer's perspective](active_inference.md) -- the A/B/C/D matrices being compared
- [Program graphs in COGANT](program_graph.md) -- the intermediate representation in the forward pipeline
- [How COGANT assigns roles](role_assignment.md) -- the rule engine that populates the GNN
- [`cogant.reverse` API reference](../api/reverse.md) -- module-by-module class and function index for the reverse pipeline
- [`cogant.gnn` API reference](../api/gnn.md) -- the forward output that the reverse pipeline consumes
