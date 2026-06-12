# Scope and related work {#sec:08-scope-and-related-work}

This chapter is organized as an overview plus four cross-referenced subsections. @sec:08-01-landscape-and-tool-categories maps tool categories and compiler-adjacent landscapes; @sec:08-02-program-analysis-for-ml-and-tables positions COGANT against machine-learning-for-code systems and tabulates feature / input-output contracts; @sec:08-03-lenses-and-synthesis treats bidirectional lenses, synthesis, and categorical framings; @sec:08-04-world-models-boundaries-and-compatibility connects world models, active inference, and compatibility boundaries; and @sec:08-05-threats-to-validity consolidates, in one adversarial place, the construct-, external-, and abstraction-validity threats and the deterministic-vs-LLM positioning rationale.

COGANT sits at the intersection of four established research areas: classical program analysis, machine learning for source code, graph-based program representations, and active-inference behavioral modeling. The landscape positioning and tool-category breakdown are developed in @sec:08-01-landscape-and-tool-categories; this overview only states the chapter scope and routes to the detail subsections below.

The chapter is also a scholarship audit: every adjacent field creates a different failure mode if the manuscript overclaims. @tbl:related-work-scholarship-map records the load-bearing anchor for each field and where the answer lives in the manuscript.

| Adjacent field | Canonical pressure | Manuscript response |
|---|---|---|
| Program analysis and CPGs | COGANT must not pretend that repository graph extraction, dataflow, or fact databases are new. | @sec:08-01-landscape-and-tool-categories and @sec:08-02-program-analysis-for-ml-and-tables position COGANT as an export/evidence compiler built on those traditions. |
| Graph learning for code | Tensor exports need typed nodes/edges and downstream compatibility without claiming trained-model accuracy. | @tbl:feature-comparison-toolchains, @tbl:io-comparison-prior-art, and the export docs separate data generation from model performance. |
| Code language models | LLM-based mappers are plausible competitors, especially for long-tail idioms. | @sec:08-05-threats-to-validity frames deterministic rules as a reproducibility/provenance trade-off rather than an accuracy superiority claim. |
| Active inference and POMDPs | A/B/C/D matrices and Markov blankets require formal discipline, not metaphor alone. | @sec:02-01-program-graph-and-formal-foundations, @sec:08-04-world-models-boundaries-and-compatibility, and @sec:09-ablation distinguish structural validity from semantic adequacy. |
| Lenses and synthesis | Roundtrip claims need to be weaker than full bidirectional-transformation laws unless proved. | @sec:08-03-lenses-and-synthesis and @sec:S01-appendix-roundtrip-epsilon define measured self-consistency and strict-isomorphism gates. |
| Reproducible SE and visual analytics | Figures and dashboards must be generated evidence, not hand-made persuasion. | @sec:07-reproducibility and @tbl:figure-reading-order tie every promoted figure to source artifacts, sidecars, and limitations. |

: Scholarship pressure map for the related-work chapter. {#tbl:related-work-scholarship-map}

## Where the full comparison lives

The detailed related-work comparison is split by topic so the overview does not duplicate tables and formal framing:

- @sec:08-01-landscape-and-tool-categories — landscape overview and tool categories.
- @sec:08-02-program-analysis-for-ml-and-tables — program analysis for ML, @tbl:feature-comparison-toolchains, @tbl:io-comparison-prior-art, and scoped positioning.
- @sec:08-03-lenses-and-synthesis — bidirectional lenses, edit lenses, incremental analysis, categorical framing, and synthesis positioning.
- @sec:08-04-world-models-boundaries-and-compatibility — world models from code, active inference, boundaries, and forward compatibility.

Authoritative **implementation scope** (languages, parsers, Rust acceleration) is recorded in `../cogant/docs/reference/implementation_status.md`.
