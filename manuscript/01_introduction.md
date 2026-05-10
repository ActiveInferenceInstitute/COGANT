# Introduction and Scope {#sec:01-introduction}

Machine learning on source code has matured alongside static analysis: both need structured representations of programs, but learning pipelines additionally need fixed feature layouts, batchable graphs, and reproducible exports [@allamanis2018survey]. COGANT addresses that gap by making the path from repository checkout to **Generalized Notation Notation (GNN) bundles** explicit, inspectable, and configurable.

## Terminology: "GNN" in this manuscript

In this manuscript, **GNN** refers to the Active Inference Institute's **Generalized Notation Notation** ([repository](https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation)) [@friedman2024gnn], a structured notation for state-space and process models---*not* graph neural networks. COGANT translates source code into this notation, producing program-graph and state-space artifacts (state space, observation modalities, actions/policies, likelihood structure, preferences, time settings, parameterization) that downstream tools can consume. Those downstream tools include graph neural network training pipelines, which can ingest the exported tensor views of the program graph, but such neural networks are a *consumer* of COGANT's output, not its output format. Where the manuscript discusses graph neural networks as related work, it uses the phrase "graph neural networks" in full; the acronym GNN always refers to Generalized Notation Notation.

## How to read this document

Readers can follow one primary lane; cross-links point to the others.

| Lane | Audience | Emphasis | Primary sections |
|------|----------|----------|------------------|
| A — Systems and ML | Engineers building datasets or GNN / graph-learning pipelines | Export contract, program graph, confidence, failure modes, benchmarks | 3, 4, 6, 7 |
| B — Formal and Active Inference | Readers who want definitions, theorems, and A/B/C/D / round-trip | Program graph IR, fixpoint engine, appendices, notation supplement | 2, 7, 8, 9, `98_`, S01–S06 |
| C — Operations and reproducibility | CI, packaging, validation | Config, tests, coverage table, recording | 6, 7, `../cogant/docs/CI.md` |

**Start here (package docs):** [`../cogant/docs/index.md`](../cogant/docs/index.md). **Live scope and staged features** (what is wired vs planned): [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md)---when this manuscript and the package disagree on behaviour or API names, the package docs and code win; the manuscript is updated to match ([`AGENTS.md`](AGENTS.md)).

## Non-goals (explicit)

- **Not** a full compiler IR, a theorem prover, or a stand-in security product: COGANT **extracts and serializes** program graphs and behavioural sketches; verification and security conclusions remain external unless you add tools downstream.
- **Not** a guarantee of complete semantics: rule coverage, parsers, and state-space compilation are **partial** and repository-dependent; always validate on your own corpora.
- **Not** a single global ranking of all program-analysis tools: related work in @sec:08-scope-and-related-work uses matrices and citations for comparison; the manuscript does not claim uniqueness except where @sec:08-scope-and-related-work feature tables back the statement[^positioning-footnote].

[^positioning-footnote]: Section 8 assembles a feature and I/O matrix against surveyed tools. The **Positioning** paragraph in this section is consistent with that table rather than a blanket claim over all unlisted software.

## Problem

A research or engineering group typically has:

- **Source code** in one or more languages.
- **Analysis goals** that combine classical queries (who calls whom?) with learned models (bug detection, retrieval, summarization).
- **Tooling fragmentation**: compilers and linters produce one shape of facts; PyTorch or JAX expect another.

COGANT unifies these behind a single pipeline whose intermediate artifacts are documented as a progression of IRs (repo IR, program graph, semantic mapping, state space, process model, validation), as described in `../cogant/docs/architecture/README.md` and `../cogant/docs/reference/implementation_status.md`.

Language coverage and rule depth follow [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md): Python is the primary front end at v0.5.x. JavaScript/TypeScript run through optional `cogant[multilang]` plus `tree-sitter` grammars (including a JS-grammar fallback path for `.ts` on mixed repositories) when installed. Rust acceleration is partially wired — `cogant._rust` exposes a PyO3 `connected_components` FFI behind the `COGANT_USE_RUST` feature flag, with a pure-Python fallback for all other code paths as documented there.

## Positioning

COGANT occupies a specific niche in the program-analysis and code-modelling landscape. Unlike learned code-embedding approaches such as code2vec and code2seq [@alon2019code2vec], which map programs to opaque distributed representations via AST path attention, COGANT produces **interpretable rule-based role assignments** that a human reviewer can inspect, edit, or reject through the `ReviewAPI` and that require no training corpus, no GPU budget, and no curated supervision signal. Every mapping carries a provenance record and a confidence score derived from a transparent rule (Equation \ref{eq:confidence-core}), so the output can be audited in the same way a conventional static analyser's findings are audited [@yamaguchi2014modeling]. While graph-learning methods such as gated graph neural networks for programs [@allamanis2018learning; @li2016gated] train supervised models to predict variable names or detect bugs from raw graph topology, COGANT complements that line by supplying a typed, confidence-annotated program graph in a documented export contract that such models can consume directly (Section 2 and `../cogant/docs/export/README.md`).

On the Active Inference side, Friston et al.'s free energy principle [@friston2010free] and the discrete-state synthesis of [@dacosta2020active] provide the theoretical foundation for the A/B/C/D matrix formalism, and the PyMDP runtime [@heins2022pymdp] implements the simulation side of that formalism. COGANT sits between those layers: it extracts the same matrices directly from an existing codebase --- rather than asking a human to hand-author them, as [@smith2022stepbystep] walks through for small examples --- and emits them in the Active Inference Institute's Generalized Notation Notation [@friedman2024gnn] so that PyMDP and compatible runtimes can execute them without manual translation. The combination of declarative role assignment, typed program-graph extraction, and GNN / A/B/C/D export to an active-inference-friendly bundle is related to other tools in the program-analysis and modelling literature; @sec:08-scope-and-related-work makes the overlap and differences explicit in tables.

## Manuscript versus package docs

This manuscript is a single linear narrative. The package tree holds authoritative API, CLI, export, and status detail. The table below replaces a long per-file bullet list; every path is under [`../cogant/docs/`](../cogant/docs/).

| Hub | Role | When to read |
|-----|------|--------------|
| [`index.md`](../cogant/docs/index.md) | Entry and quick links | First visit |
| [`api/README.md`](../cogant/docs/api/README.md) | Session, `PipelineRunner`, `Bundle`, `ReviewAPI` | Programmatic use |
| [`cli/README.md`](../cogant/docs/cli/README.md) + [`cli_reference.md`](../cogant/docs/cli_reference.md) | Commands and flags | Shell / automation |
| [`export/README.md`](../cogant/docs/export/README.md) | GNN schema, tensor interop | Downstream consumers |
| [`plugins/README.md`](../cogant/docs/plugins/README.md) | Parsers, rules, validators, exporters | Extensions |
| [`architecture/README.md`](../cogant/docs/architecture/README.md) | Layers, crates, data flow | System picture |
| [`reference/README.md`](../cogant/docs/reference/README.md) | Implementation status, how-tos | Onboarding, scope |
| [`rules/README.md`](../cogant/docs/rules/README.md) | Translation rules | Rule authors |
| [`validation/README.md`](../cogant/docs/validation/README.md) | Integrity and provenance | Quality gates |
| [`security/README.md`](../cogant/docs/security/README.md) | Threat model, sandboxing | Deployment |
| [`roadmap/README.md`](../cogant/docs/roadmap/README.md) | Releases and backlog | Planning |
| [`specs/README.md`](../cogant/specs/README.md) | Machine-readable IR contracts | Integrators |
| [`reference/documentation_modules.md`](../cogant/docs/reference/documentation_modules.md) | Full `docs/<module>` index | Deep navigation |

## Dual Python/Rust architecture

COGANT employs a dual-language architecture. The **Python orchestration layer** handles session management, pipeline coordination, configuration, file discovery, AST parsing, and the plugin interface -- tasks where developer ergonomics and extensibility matter more than raw throughput. The **Rust core**, organized as a workspace of eight crates (`cogant-core`, `cogant-graph`, `cogant-translate`, `cogant-statespace`, `cogant-store`, `cogant-trace`, `cogant-gnn`, `cogant-ffi`), implements typed graph operations, translation internals, trace-oriented plumbing, state-space structures, and Generalized Notation Notation (GNN) formatting -- tasks where memory layout and cache locality dominate wall-clock time. Communication between layers flows through PyO3 bindings (`cogant-ffi`), which release the Python GIL during Rust execution to permit concurrent stage processing. The current Rust-wired paths (`connected_components`, graph traversal) are enumerated in `../cogant/docs/reference/implementation_status.md`; remaining Python-only paths are gated behind `COGANT_USE_RUST=0` (the default), enabling benchmarking on both execution paths without changing pipeline results.

## Non-technical summary

COGANT turns a checked-out codebase into a structured, reviewable graph plus an Active-Inference-style bundle (matrices and notation the runtime can use), with confidence on each mapping, instead of a single opaque vector. It is meant for teams that need both static-analysis-style auditability and machine-learning-style tensor exports. Optional languages and services are documented in the package; the manuscript explains the core theory and the evaluation story.

## Roadmap of the following sections

Section 2 formalizes the program graph and IR progression, and states the five formal definitions and three termination/completeness/validity theorems that govern the rest of the manuscript. Section 3 describes the realized pipeline behavior and artifacts. Section 4 provides concrete examples and failure modes. Section 5 closes with limitations and roadmap. Section 6 covers experimental setup, Section 7 reproducibility, Section 8 related work and the COGANT-vs-prior-art feature and input/output comparison tables, and Section 9 an ablation study over rule families, fixpoint iterations, and A/B/C/D fallback paths.
