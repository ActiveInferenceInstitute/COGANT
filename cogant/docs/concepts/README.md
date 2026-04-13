# Concepts

> Theory and core ideas behind COGANT: Active Inference, Generalized Notation Notation (GNN), Markov blankets, the program graph abstraction, semantic role assignment, and the forward/reverse roundtrip. Read this section first if you want to understand *why* COGANT does what it does before learning *how* to use it.

## Contents

| Page | Description | Level |
|------|-------------|-------|
| [Active Inference](active_inference.md) | Free Energy Principle and the Active Inference roles COGANT assigns to code | Beginner |
| [Generalized Notation Notation (GNN)](gnn.md) | The GNN intermediate representation used as COGANT's interchange format | Beginner |
| [Markov Blanket](markov_blanket.md) | How sensory / active / internal / external partitions are derived from program graphs | Intermediate |
| [Program Graph](program_graph.md) | Static + dynamic program graph extraction model | Intermediate |
| [Role Assignment](role_assignment.md) | Code-to-role mapping rules and confidence model | Intermediate |
| [Roundtrip / Isomorphism](roundtrip.md) | Forward (code -> GNN) and reverse (GNN -> code) roundtrip and what isomorphism means here | Advanced |

## Recommended Reading Order

1. [Active Inference](active_inference.md) — establishes the vocabulary (sensory, active, internal, external) used everywhere else.
2. [Generalized Notation Notation (GNN)](gnn.md) — introduces the artifact COGANT produces and consumes.
3. [Program Graph](program_graph.md) — the structural abstraction that bridges code and GNN.
4. [Markov Blanket](markov_blanket.md) — partitioning the program graph into Active Inference compartments.
5. [Role Assignment](role_assignment.md) — how individual nodes get tagged with semantic roles.
6. [Roundtrip / Isomorphism](roundtrip.md) — closes the loop and explains the isomorphism criterion used by the evaluation suite.

## Related modules

- [../theory/README.md](../theory/README.md) — formal statements of the same ideas covered informally here.
- [../evaluation/README.md](../evaluation/README.md) — empirical evidence for the claims introduced here.
- [../tutorials/README.md](../tutorials/README.md) — hands-on walkthroughs that exercise these concepts.
- [../rules/README.md](../rules/README.md) — how role assignment is implemented in the rule engine.

Agent notes: [AGENTS.md](AGENTS.md) - Hub: [../index.md](../index.md)
