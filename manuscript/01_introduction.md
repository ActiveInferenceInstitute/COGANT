# Introduction and Scope {#sec:01-introduction}

Machine learning on source code has matured alongside static analysis: both need structured representations of programs, but learning pipelines additionally need fixed feature layouts, batchable graphs, and reproducible exports [@allamanis2018survey]. COGANT addresses that gap by making the path from repository checkout to **Generalized Notation Notation (GNN) bundles** explicit, inspectable, and configurable.

The contribution is best read as an **evidence compiler** rather than as a new neural architecture. COGANT takes the long-standing program-analysis idea that program facts can be propagated to a stable fixpoint over finite graphs [@kildall1973unified; @cousot1977abstract], combines it with graph-first code representations from code property graphs and graph-learning-for-code work [@yamaguchi2014modeling; @allamanis2018learning], and emits an active-inference model artifact whose matrices and state-space sections can be checked, visualized, and roundtripped. That positioning matters: the system's scientific output is not an opaque embedding or a proof of full semantics, but a reproducible bundle of typed graph facts, rule evidence, confidence scores, matrix defaults, visual diagnostics, and validation status that a reviewer can inspect.

## Terminology: "GNN" in this manuscript

In this manuscript, **GNN** refers to the Active Inference Institute's **Generalized Notation Notation** ([repository](https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation)) [@friedman2024gnn], a structured notation for state-space and process models---*not* graph neural networks. COGANT translates source code into this notation, producing program-graph and state-space artifacts (state space, observation modalities, actions/policies, likelihood structure, preferences, time settings, parameterization) that downstream tools can consume. Those downstream tools include graph neural network training pipelines, which can ingest the exported tensor views of the program graph, but such neural networks are a *consumer* of COGANT's output, not its output format. Where the manuscript discusses graph neural networks as related work, it uses the phrase "graph neural networks" in full; the acronym GNN always refers to Generalized Notation Notation.

## How to read this document

Readers can follow one primary lane; cross-links point to the others.

| Lane | Audience | Emphasis | Primary sections |
|------|----------|----------|------------------|
| A — Systems and ML | Engineers building datasets or GNN / graph-learning pipelines | Export contract, program graph, confidence, failure modes, benchmarks | @sec:03-api-and-workflows, @sec:04-examples-and-failure-modes, @sec:06-experimental-setup, @sec:07-reproducibility |
| B — Formal and Active Inference | Readers who want definitions, theorems, and A/B/C/D / round-trip | Program graph IR, fixpoint engine, appendices, notation supplement | @sec:02-01-program-graph-and-formal-foundations, @sec:08-scope-and-related-work, @sec:09-ablation, @sec:98-notation-supplement, and the supplementary sections |
| C — Operations and reproducibility | CI, packaging, validation | Config, tests, coverage table, recording | @sec:06-experimental-setup, @sec:07-reproducibility, `../cogant/docs/CI.md` |

**Start here (package docs):** [`../cogant/docs/index.md`](../cogant/docs/index.md). **Live scope and staged features** (what is wired vs planned): [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md)---when this manuscript and the package disagree on behaviour or API names, the package docs and code win; the manuscript is updated to match ([`AGENTS.md`](AGENTS.md)).

## Visual interpretability first

COGANT's primary human interface is not a single score. It is the set of rendered artifacts that let a reviewer inspect each conversion boundary: source symbols become a typed program graph, translation rules assign semantic roles, state-space compilation emits variables/observations/actions and A/B/C/D tensors, the Markov blanket view exposes the internal/sensory/active/external interface, and the roundtrip trace records whether a reverse code artifact is present. This follows the information-visualization pattern of giving an overview, then supporting filtering and details on demand [@shneiderman1996eyes; @heer2012interactive], and it treats visualization as part of the method rather than post-hoc decoration [@munzner2009nested; @brehmer2013typology; @hohman2019visual]. @fig:cogant-graphical-abstract is copied from the package's real calculator run under `../cogant/output/`; its confidence tile is a run-evidence completeness score over source coverage, validation, roundtrip status, and required figure presence, while the exported GNN JSON retains the separate calibrated semantic confidence values. @sec:04-examples-and-failure-modes then expands the same run into the detailed one-way and roundtrip visual chain.

![Graphical abstract generated by `cogant.viz.write_inspection_artifacts` for the calculator run. The panel summarizes source-code evidence, program graph size, semantic role mappings, state-space compilation, GNN matrix shapes, Markov blanket partition, and roundtrip artifact status; the accompanying sidecar records the source artifact, digest, displayed counts, visual QA, and known limitations. **Scope note**: `calculator` is the smallest shipped fixture ({{FIXTURE_CALCULATOR_ACTIONS}} ACTION mappings, {{FIXTURE_CALCULATOR_OBSERVATIONS}} OBSERVATION mappings, {{FIXTURE_CALCULATOR_STATE_VARIABLES}} HIDDEN_STATE) and its single hidden-state column in $A$ lands at the maximum-entropy fallback (see @sec:09-ablation matrix-fallback table); this orientation figure should be read as a *layout* of the artifact chain, **not** as a demonstration that the extracted active-inference model carries informative posterior structure. `flask_app` ({{ABLATION_FLASK_APP_A_COLS_TOTAL}} hidden-state columns in $A$, all carrying observation evidence; D non-uniform) is the smallest fixture with a fully informative likelihood and is the cited exemplar for matrix-fallback diagnostics in @sec:09-ablation.](../figures/cogant_graphical_abstract.png){#fig:cogant-graphical-abstract width=95%}

## Non-goals (explicit)

- **Not** a full compiler IR, a theorem prover, or a stand-in security product: COGANT **extracts and serializes** program graphs and behavioural sketches; verification and security conclusions remain external unless you add tools downstream.
- **Not** a guarantee of complete semantics: rule coverage, parsers, and state-space compilation are **partial** and repository-dependent; always validate on your own corpora.
- **Not** a single global ranking of all program-analysis tools: related work in @sec:08-scope-and-related-work uses matrices and citations for comparison; the manuscript does not claim uniqueness except where @sec:08-scope-and-related-work feature tables back the statement[^positioning-footnote].

[^positioning-footnote]: @sec:08-scope-and-related-work and @sec:08-02-program-analysis-for-ml-and-tables assemble the scoped feature and I/O matrices against surveyed tools. The **Positioning** paragraph in this section is consistent with those tables rather than a blanket claim over all unlisted software.

## Problem

A research or engineering group typically has:

- **Source code** in one or more languages.
- **Analysis goals** that combine classical queries (who calls whom?) with learned models (bug detection, retrieval, summarization).
- **Tooling fragmentation**: compilers and linters produce one shape of facts; PyTorch or JAX expect another.

COGANT unifies these behind a single pipeline whose intermediate artifacts are documented as a progression of IRs (repo IR, program graph, semantic mapping, state space, process model, validation), as described in `../cogant/docs/architecture/README.md` and `../cogant/docs/reference/implementation_status.md`.

Language coverage and rule depth follow [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md): Python is the primary front end at v{{VERSION}}. JavaScript/TypeScript run through optional `cogant[multilang]` plus `tree-sitter` grammars [@treeSitterDocs2026] (including a JS-grammar fallback path for `.ts` on mixed repositories) when installed. Rust acceleration is partially wired — `cogant._rust` exposes a PyO3 `connected_components` FFI behind the `COGANT_USE_RUST` feature flag, with a pure-Python fallback for all other code paths as documented there.

## Positioning

COGANT occupies a specific niche in the program-analysis and code-modelling landscape. Unlike learned code-embedding approaches such as code2vec [@alon2019code2vec] and code2seq [@alon2018code2seq], which map programs to distributed representations or natural-language sequences through AST-path attention, COGANT produces **interpretable rule-based role assignments** that a human reviewer can inspect, edit, or reject through the `ReviewAPI` and that require no training corpus, no GPU budget, and no curated supervision signal. Every mapping carries a provenance record and a confidence score derived from a transparent rule (@eq:confidence-core), so the output can be audited in the same way a conventional static analyser's findings are audited [@yamaguchi2014modeling]. While graph-learning methods such as gated graph neural networks for programs [@allamanis2018learning; @li2016gated] train supervised models to predict variable names or detect bugs from raw graph topology, COGANT complements that line by supplying a typed, confidence-annotated program graph in a documented export contract that such models can consume directly (@sec:02-01-program-graph-and-formal-foundations and `../cogant/docs/export/README.md`).

On the Active Inference side, Friston et al.'s free energy principle [@friston2010free] and the discrete-state synthesis of [@dacosta2020active] provide the theoretical foundation for the A/B/C/D matrix formalism, and the PyMDP runtime [@heins2022pymdp] implements the simulation side of that formalism. COGANT sits between those layers: it extracts the same matrices directly from an existing codebase --- rather than asking a human to hand-author them, as [@smith2022stepbystep] walks through for small examples --- and emits them in the Active Inference Institute's Generalized Notation Notation [@friedman2024gnn] so that PyMDP and compatible runtimes can execute them without manual translation. The combination of declarative role assignment, typed program-graph extraction, and GNN / A/B/C/D export to an active-inference-friendly bundle is related to other tools in the program-analysis and modelling literature; @sec:08-scope-and-related-work makes the overlap and differences explicit in tables.

The practical research claim is therefore narrower, and stronger, than "code becomes cognition." COGANT says that a repository can be transformed into an **auditable generative-model candidate**: source evidence and optional runtime evidence produce graph facts; graph facts produce state-space variables, observations, actions, and preferences; matrix fallbacks expose what the code did not determine; dashboards show the conversion boundaries; and the roundtrip report measures how much of the generated artifact survives reverse synthesis. Each of those claims is tied either to package artifacts, `METRICS.yaml`, or the primary literature cited in this manuscript.

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

COGANT employs a dual-language architecture in which **Python is the
default production runtime** (`COGANT_USE_RUST=0`) and the **Rust
workspace is an opt-in acceleration scaffold** rather than the active
runtime path. The **Python orchestration layer** handles session
management, pipeline coordination, configuration, file discovery, AST
parsing, and the plugin interface — tasks where developer ergonomics
and extensibility matter more than raw throughput. The **Rust
workspace** is organized as eight crates (`cogant-core`,
`cogant-graph`, `cogant-translate`, `cogant-statespace`,
`cogant-store`, `cogant-trace`, `cogant-gnn`, `cogant-ffi`) with the
intent of moving typed graph operations, translation internals,
trace-oriented plumbing, state-space structures, and Generalized
Notation Notation (GNN) formatting into a Rust kernel once the
per-stage benchmarks justify the cross-language friction. **The single
Rust-wired production path today** is the `connected_components`
branch in `cogant/py/cogant/graph/builder.py` (FFI-exposed through
`cogant-ffi`); all other crates are scaffolds awaiting either
performance-pressure justification or upstream API stability.
Communication between layers flows through PyO3 bindings; these calls
are synchronous and hold the Python GIL (no GIL release or concurrent
stage processing is implemented in the current `cogant-ffi` surface).
The implementation status table at
`../cogant/docs/reference/implementation_status.md` is the
source-of-record for which Rust paths are call-sited from Python; the
manuscript treats the Rust workspace as an architectural capacity, not
as evidence of a Rust-default runtime. `COGANT_USE_RUST=1`
opt-in execution enables benchmarking the active path against the
default Python implementation without changing pipeline results.

## Non-technical summary

COGANT turns a checked-out codebase into a structured, reviewable graph plus an Active-Inference-style bundle (matrices and notation the runtime can use), with confidence on each mapping, instead of a single opaque vector. It is meant for teams that need both static-analysis-style auditability and machine-learning-style tensor exports. Optional languages and services are documented in the package; the manuscript explains the core theory and the evaluation story.

## Roadmap of the following sections

The formal core begins in @sec:02-01-program-graph-and-formal-foundations and @sec:02-02-ir-progression-translation-engine, then @sec:02-03-confidence-state-space-and-behavior and @sec:02-04-gnn-export-and-error-handling connect confidence, state-space compilation, export, and error handling. @sec:03-api-and-workflows describes runtime/API workflows; @sec:04-examples-and-failure-modes shows concrete artifacts and failure modes; @sec:06-experimental-setup through @sec:06-05-reproducible-recording define the evaluation protocol and measured tables; @sec:07-reproducibility covers artifact recording and validation; @sec:08-scope-and-related-work through @sec:08-04-world-models-boundaries-and-compatibility locate the work against prior systems; @sec:09-ablation probes rule-family and matrix-fallback sensitivity; and @sec:10-conclusion closes with shipped capabilities, limitations, and development directions.

Six appendices and one notation supplement support the body. @sec:S01-appendix-roundtrip-epsilon documents the native v0.6 roundtrip evaluation protocol and role-preservation metric; @sec:S02-appendix-ablation reports per-rule-family ablation deltas; @sec:S03-appendix-galois-sketch sketches the Galois-connection framing of the IR; @sec:S04-appendix-inference-mathematics records the canonical variational and expected-free-energy derivations exercised by the runtime; @sec:S05-appendix-extended-related-work extends the comparison tables in §8; and @sec:S06-appendix-source-references catalogues the source-of-record paths referenced from the body. The notation supplement (@sec:98-abcd-matrix-symbols) collects every symbol and confidence-tier threshold in one place so that any section can be read in isolation without recovering definitions from earlier text.
