# Theory

> Formal theoretical background for COGANT: Active Inference, the
> "code as generative model" thesis, the Generalized Notation Notation
> (GNN) intermediate representation, and the roundtrip isomorphism
> theorem. Read this section when you need the formal statement rather
> than the conceptual primer — for the friendlier introduction see
> [../concepts/README.md](../concepts/README.md).

## Contents

| Page | Description | Level |
|------|-------------|-------|
| [Active Inference primer](active_inference_primer.md) | Short introduction to Active Inference for readers new to the framework | Beginner |
| [Active Inference mapping](active_inference.md) | Theoretical justification for how COGANT maps software constructs to Active Inference roles (HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONSTRAINT, CONTEXT) | Intermediate |
| [Code as generative model](code_as_generative_model.md) | The thesis that a repository *is*, not merely *describes*, an Active Inference generative model | Intermediate |
| [GNN format](gnn_format.md) | Short introduction to Generalized Notation Notation as COGANT uses it | Intermediate |
| [GNN format reference](gnn_format_reference.md) | Working reference for the 19 sections in a GNN package | Advanced |
| [Round-trip verification](roundtrip.md) | Forward→Reverse→Forward validation: what ISOMORPHIC/APPROXIMATE/DIVERGENT classifications mean and why ε=1.0 matters. v0.5.0 achieved 23/23 ISOMORPHIC. | Intermediate |
| [Isomorphism theorem](isomorphism.md) | Formal statement and proof sketch of the program-graph / generative-model isomorphism (Galois connection) | Advanced |

## Recommended Reading Order

1. [Active Inference primer](active_inference_primer.md) — minimum vocabulary if you have not encountered the framework before.
2. [Code as generative model](code_as_generative_model.md) — the thesis that motivates the rest of the module.
3. [Active Inference mapping](active_inference.md) — how the thesis is cashed out for concrete code patterns (the 22 translation rules and 7 core roles).
4. [GNN format](gnn_format.md) — the intermediate representation in which everything is expressed.
5. [GNN format reference](gnn_format_reference.md) — exhaustive reference for the 19-section package layout.
6. [Round-trip verification](roundtrip.md) — how the forward and reverse passes are validated to be semantically dual (23/23 ISOMORPHIC at v0.5.0).
7. [Isomorphism theorem](isomorphism.md) — formal closure of the loop: program-graph / generative-model duality as a Galois connection.

## Related modules

- [../concepts/README.md](../concepts/README.md) — friendlier primers on
  the same topics.
- [../evaluation/README.md](../evaluation/README.md) — empirical evidence
  for the claims stated here.
- [../reference/README.md](../reference/README.md) — canonical COGANT
  schema and API references.
- [../rnd/README.md](../rnd/README.md) — exploratory notes that have not
  yet been promoted into formal theory.

Agent notes: [AGENTS.md](AGENTS.md) - Hub: [../index.md](../index.md)
