# Code as a generative-model artifact

> **Thesis.** COGANT treats a software repository as an inspectable artifact that can be
> projected into an Active Inference-style generative model. The projection is useful because
> it preserves explicit graph, role, state-space, and matrix evidence, not because every
> program is literally a probabilistic agent.

This page gives the current operational reading. The historical categorical sketch lives in
[`../evaluation/ISOMORPHISM_THEOREM.md`](https://github.com/docxology/cogant/blob/main/docs/evaluation/ISOMORPHISM_THEOREM.md);
it is preserved for provenance, while the live contract is the role-preservation and
strict-invariant taxonomy in [the roundtrip concept page](../concepts/roundtrip.md).

## The core claim

An Active Inference model partitions the world into four sets: **internal states** (μ),
**sensory states** (s), **active states** (a), and **external states** (η). A Markov blanket
(s ∪ a) separates internal from external.

A running program is structurally identical:

| Active Inference | Software |
| --- | --- |
| Internal state μ | Private fields, caches, buffers, accumulators |
| Sensory state s | Getters, read APIs, loggers, metric readers |
| Active state a | Setters, mutators, request handlers, event publishers |
| External state η | Other processes, databases, network, user input |
| Generative model p(o, s, a) | The program's control flow + side-effect structure |
| Variational free energy | The error-handling / retry / validation surface |
| Expected free energy | The planner / scheduler / policy layer |

The left column is the Active Inference vocabulary. The right column is the software surface
COGANT can inspect. COGANT rewrites selected, machine-extracted evidence from the right column
into the left-column notation.

## Why this analogy is operational

Three concrete reasons the mapping is useful enough to test:

### 1. Both are graphs with typed, directed edges

Active Inference is usually written as a factor graph: circles for random variables, squares
for factors, directed edges for conditional dependencies. A program dependence graph is
**exactly** that — nodes for symbols (functions, classes, variables), edges for typed
dependencies (`CALLS`, `READS`, `WRITES`, `IMPORTS`, `INHERITS`). COGANT constructs a
`ProgramGraph`, then emits factor-graph-like state-space and matrix artifacts whose sidecars
record the source counts and layout metadata.

### 2. Both are deterministic transducers of belief

A generative model takes observations and produces a posterior over hidden states:
`p(s | o) ∝ p(o | s) · p(s)`. A program takes input and produces a state mutation:
`state_{t+1} = f(state_t, input_t)`. Both are deterministic mechanisms for updating
uncertainty. The program is the posterior — not its description, but the actual
inference procedure when run.

### 3. Both satisfy the Markov blanket property

A Markov blanket is a conditional-independence boundary: internal states are conditionally
independent of the environment given the blanket (s ∪ a). A well-engineered module has the
**same** property: internal fields are conditionally independent of the rest of the program
given the module's public API. COGANT's blanket extractor (`py/cogant/markov/blanket.py`) is
an O(V + E) primitive that computes this partition directly from the graph, without requiring
any Active Inference concepts at the implementation level.

## The pipeline, in evidence-preservation language

```mermaid
flowchart LR
    A[Source code\nconcrete syntax tree] --> B[Program graph\nfactor graph]
    B --> C[Semantic mappings\nrandom variable types]
    C --> D[State space model\ncompiled p(s, o, a)]
    D --> E[A/B/C/D matrices\nconditional distributions]
    E --> F[GNN markdown\nAII reference format]
    F --> G[Simulation /\n belief-update loop]
    E -.->|inverse| H[Package plan\nsynthesized code]
    H -.-> A
    classDef hot fill:#6B21A8,color:#fff
    classDef cool fill:#1D4ED8,color:#fff
    class F hot
    class H cool
```

Each arrow has an **evidence-preservation contract**:

- **source → graph**: AST evidence is re-indexed into graph nodes and typed edges. Whitespace,
  comments, and unsupported language constructs are intentionally outside this graph.
- **graph → mappings**: the 22 translation rules assign each node a role in the generative
  model. A rule fires only when the graph carries enough evidence to justify the assignment.
- **mappings → state space**: the compiler projects the role assignments onto an ordered
  state / observation / action basis.
- **state space → A/B/C/D**: the matrix builder counts evidence edges and normalizes. The
  result is a well-formed probabilistic model suitable for `pymdp` or any Active Inference
  simulator.
- **A/B/C/D → GNN**: the formatter emits the AII reference bracket notation plus JSON twins.
  This is a schema-preserving export of COGANT's compiled model, not a proof that the source
  code was fully captured.
- **GNN → code**: the reverse module synthesizes a Python package and the roundtrip command
  re-runs the forward pipeline. Trust the emitted invariant ledger: `ROLE_PRESERVED` is weaker
  than `STRUCTURALLY_ISOMORPHIC`.

## What this buys you

1. **Program understanding as auditable evidence.** Confidence scores on semantic mappings
   are calibrated rule-evidence scores. They should be read as review priorities unless a
   labelled calibration corpus is available.
2. **Refactoring hypotheses from model diagnostics.** Sparse or fallback-heavy A/B/C/D
   matrices can flag places where the source graph lacks explicit evidence. The hypothesis is
   that those gaps correlate with hidden coupling or underspecified interfaces; the
   `../evaluation/CALIBRATION.md` plan is the empirical check.
3. **Active Inference agents from real code.** Once a codebase is represented as A/B/C/D, a
   PyMDP agent can plan over it immediately. This is the reverse-mode end-goal: synthesize a
   runnable agent whose generative model **is** the analyzed codebase.

## Caveats

- **Not every program has a clean blanket.** A codebase with no cohesive modules, no visibility
  boundaries, and no typed state will produce a partition that is technically valid but
  uninformative. COGANT reports this via internal / boundary ratios rather than failing.
- **Identifier evidence still matters.** Rules like `ObservationRule` and `ActionRule` combine
  naming cues with structural evidence. Obfuscated or non-English identifiers lean more heavily
  on graph evidence, which can lower confidence or leave mappings unresolved.
- **Uniform C / D fallbacks are honest defaults, not learned parameters.** When the program
  lacks `CONSTRAINT` or `CONFIGURATION` evidence, the preference vector and initial prior are
  uniform. The validator surfaces this as a warning so downstream consumers know not to treat
  the matrices as learned posteriors.

## Further reading

- [The forward-reverse cycle](../concepts/roundtrip.md) — current status taxonomy and invariant
  ledger.
- [`../evaluation/ISOMORPHISM_THEOREM.md`](https://github.com/docxology/cogant/blob/main/docs/evaluation/ISOMORPHISM_THEOREM.md) —
  historical proof sketch and terminology.
- [Active Inference primer](active_inference_primer.md) — three-paragraph background if the
  neuroscience vocabulary is new.
- [Active Inference mapping](active_inference.md) — the mechanical rule-by-rule version of
  this page.
- [GNN format reference](gnn_format_reference.md) — the exact bracket-notation output.
