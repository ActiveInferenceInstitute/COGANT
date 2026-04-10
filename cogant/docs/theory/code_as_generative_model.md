# Code as a generative model

> **Thesis.** A software repository is not merely *describable* as an Active Inference generative model — it **is** one. Program graphs, hidden states, observations, and actions are not analogies borrowed from neuroscience. They are the literal ontology a compiler produces and an interpreter executes.

This page is the informal companion to [`_rnd/ISOMORPHISM_THEOREM.md`](https://github.com/cogant-contributors/cogant/blob/main/_rnd/ISOMORPHISM_THEOREM.md),
which states the formal version.

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

The left column is the neuroscience vocabulary. The right column is what your IDE displays.
COGANT is the machine that rewrites one into the other.

## Why this is not an analogy

Three concrete reasons the mapping is a genuine isomorphism, not a metaphor:

### 1. Both are graphs with typed, directed edges

Active Inference is usually written as a factor graph: circles for random variables, squares
for factors, directed edges for conditional dependencies. A program dependence graph is
**exactly** that — nodes for symbols (functions, classes, variables), edges for typed
dependencies (`CALLS`, `READS`, `WRITES`, `IMPORTS`, `INHERITS`). COGANT constructs both
simultaneously: it calls the resulting object `ProgramGraph`, but a PyMDP practitioner would
recognize it as a factor graph.

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

## The pipeline, in isomorphism language

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

Each arrow is **content-preserving**:

- **source → graph**: AST is the syntactic form; graph is the semantic form. Information is
  re-indexed, not thrown away (except whitespace and comments).
- **graph → mappings**: the 19 translation rules assign each node a role in the generative
  model. A rule fires only when the graph carries enough evidence to justify the assignment.
- **mappings → state space**: the compiler projects the role assignments onto an ordered
  state / observation / action basis.
- **state space → A/B/C/D**: the matrix builder counts evidence edges and normalizes. The
  result is a well-formed probabilistic model suitable for `pymdp` or any Active Inference
  simulator.
- **A/B/C/D → GNN**: the formatter emits the AII reference bracket notation. This is a
  lossless re-encoding, not a summary.
- **GNN → code** *(prototype)*: the reverse module synthesizes a Python package whose forward
  run produces an isomorphic GNN. The round trip is idempotent up to whitespace and names.

## What this buys you

1. **Program understanding as Bayesian inference.** Confidence scores on semantic mappings
   are literal posteriors over role assignments. A mapping with confidence 0.82 is a
   probabilistic assertion that the rule's evidence implies its conclusion with that
   posterior probability.
2. **Refactoring as free-energy minimization.** A codebase whose A matrix is close to
   singular (no direct READS evidence on most observations) has high variational free energy
   — it is surprising in the Active Inference sense. That is also the measurable signature of
   "spaghetti code" or "hidden coupling." The thesis predicts the two should correlate, and
   the `_rnd/CALIBRATION.md` plan is the empirical check.
3. **Active Inference agents from real code.** Once a codebase is represented as A/B/C/D, a
   PyMDP agent can plan over it immediately. This is the reverse-mode end-goal: synthesize a
   runnable agent whose generative model **is** the analyzed codebase.

## Caveats

- **Not every program has a clean blanket.** A codebase with no cohesive modules, no visibility
  boundaries, and no typed state will produce a partition that is technically valid but
  uninformative. COGANT reports this via internal / boundary ratios rather than failing.
- **Keywords matter in v0.1.** Rules like `ObservationRule` and `ActionRule` use English
  keyword sets. Obfuscated or non-English identifiers fall back to purely structural evidence
  (edge degree, containment). This is an implementation limitation, not a theoretical one —
  structural rules are language-independent.
- **Uniform C / D fallbacks are honest defaults, not learned parameters.** When the program
  lacks `CONSTRAINT` or `CONFIGURATION` evidence, the preference vector and initial prior are
  uniform. The validator surfaces this as a warning so downstream consumers know not to treat
  the matrices as learned posteriors.

## Further reading

- [`_rnd/ISOMORPHISM_THEOREM.md`](https://github.com/cogant-contributors/cogant/blob/main/_rnd/ISOMORPHISM_THEOREM.md) — the formal statement
  with the proof sketch.
- [Active Inference primer](active_inference_primer.md) — three-paragraph background if the
  neuroscience vocabulary is new.
- [Active Inference mapping](active_inference.md) — the mechanical rule-by-rule version of
  this page.
- [GNN format reference](gnn_format_reference.md) — the exact bracket-notation output.
