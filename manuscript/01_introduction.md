# Introduction and Scope

Machine learning on source code has matured alongside static analysis: both need structured representations of programs, but learning pipelines additionally need fixed feature layouts, batchable graphs, and reproducible exports [@allamanis2018survey]. COGANT addresses that gap by making the path from repository checkout to **Generalized Notation Notation (GNN) bundles** explicit, inspectable, and configurable.

## Terminology: "GNN" in this manuscript

In this manuscript, **GNN** refers to the Active Inference Institute's **Generalized Notation Notation** ([repository](https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation)) [@friedman2024gnn], a structured notation for state-space and process models---*not* graph neural networks. COGANT translates source code into this notation, producing program-graph and state-space artifacts (state space, observation modalities, actions/policies, likelihood structure, preferences, time settings, parameterization) that downstream tools can consume. Those downstream tools include graph neural network training pipelines, which can ingest the exported tensor views of the program graph, but such neural networks are a *consumer* of COGANT's output, not its output format. Where the manuscript discusses graph neural networks as related work, it uses the phrase "graph neural networks" in full; the acronym GNN always refers to Generalized Notation Notation.

## Problem

A research or engineering group typically has:

- **Source code** in one or more languages.
- **Analysis goals** that combine classical queries (who calls whom?) with learned models (bug detection, retrieval, summarization).
- **Tooling fragmentation**: compilers and linters produce one shape of facts; PyTorch or JAX expect another.

COGANT unifies these behind a single pipeline whose intermediate artifacts are documented as a progression of IRs (repo IR, program graph, semantic mapping, state space, process model, validation), as described in `../cogant/docs/ARCHITECTURE.md` and `../cogant/docs/SPEC.md`.

## What COGANT is not

COGANT is not a replacement for a full compiler IR, a theorem prover, or a security scanner by itself. It **extracts and serializes** program graphs and behavioral sketches for downstream use. Language coverage and rule depth follow the implementation-status table in the SPEC: Python is the primary front end at v0.1.x; additional languages and Rust acceleration are staged as documented there.

## Manuscript versus package docs

The canonical API and CLI details live in:

- `../cogant/docs/API_GUIDE.md` — Session, `PipelineRunner`, `Bundle`, `ReviewAPI`
- `../cogant/docs/CLI_GUIDE.md` — commands and flags
- `../cogant/docs/GNN_EXPORT.md` — Generalized Notation Notation schema, section ordering, and companion interop field contracts (including optional PyG/DGL tensor views)
- `../cogant/docs/PLUGIN_API.md` — parsers, rules, validators, exporters
- `../cogant/docs/ARCHITECTURE.md` — layers, crates, data flow

This manuscript summarizes theory and practice for readers who want a single linear narrative before diving into those files.

## Dual Python/Rust architecture

COGANT employs a dual-language architecture. The **Python orchestration layer** handles session management, pipeline coordination, configuration, file discovery, AST parsing, and the plugin interface -- tasks where developer ergonomics and extensibility matter more than raw throughput. The **Rust core**, organized as a workspace of eight crates (`cogant-core`, `cogant-graph`, `cogant-translate`, `cogant-statespace`, `cogant-store`, `cogant-trace`, `cogant-gnn`, `cogant-ffi`), implements typed graph operations, translation internals, trace-oriented plumbing, state-space structures, and Generalized Notation Notation (GNN) formatting -- tasks where memory layout and cache locality dominate wall-clock time. Communication between layers flows through PyO3 bindings (`cogant-ffi`), which release the Python GIL during Rust execution to permit concurrent stage processing. Where Rust bindings are not yet wired for a code path (see the implementation-status table in `../cogant/docs/SPEC.md`), Python fallback implementations ensure the pipeline remains functional at the cost of higher latency on large repositories.

## Roadmap of the following sections

Section 2 formalizes the program graph and IR progression. Section 3 describes the realized pipeline behavior and artifacts. Section 4 provides concrete examples and failure modes. Section 5 closes with limitations and roadmap. Section 6 covers experimental setup, Section 7 reproducibility, and Section 8 related work.
