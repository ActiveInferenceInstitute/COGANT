## Core Concepts

> **What this page is:** A reference index of COGANT's core data-model concepts — entities, relationships, confidence, and provenance — with pointers into the deep-dive concept pages.
>
> **Prerequisites:** None for the high-level reading; concept pages assume Python literacy.
>
> **Reading time:** ~10 minutes
>
> **Next steps:** [Active Inference for programmers](../concepts/active_inference.md) · [Program graphs in COGANT](../concepts/program_graph.md) · [Glossary](glossary.md)

### Entities & Relationships

Code is represented as a directed graph:
- **Nodes** represent program entities (functions, variables, types, modules)
- **Edges** represent relationships (calls, uses, defines, inherits, etc.)
- **Roles** classify entities semantically (FunctionDef, VariableUse, etc.)

### Confidence & Provenance

Every assertion carries:
- **Confidence score** (0.0-1.0) indicating certainty
- **Provenance** tracking why it was inferred:
  - SourceCode: explicit in source
  - TypeSystem: from type checker
  - ControlFlow: from CFG analysis
  - Heuristic: rule-based inference
  - External: from external tool

### Internal Representations (IRs)

Six progressive IRs, each adding semantic detail:

1. **Repo IR**: Raw extracted entities (from parsers)
2. **Program Graph IR**: Semantic graph (nodes, edges, roles)
3. **Semantic Mapping IR**: Translation rules applied
4. **State Space IR**: Behavioral model
5. **Process Model IR**: High-level control structures
6. **Validation IR**: Quality metrics

