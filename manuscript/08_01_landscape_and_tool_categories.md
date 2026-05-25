# Scope and related work: landscape and tool categories {#sec:08-01-landscape-and-tool-categories}

## COGANT in the program-analysis landscape

COGANT sits at the intersection of four established research areas: classical program analysis, machine learning for source code, graph-based program representations, and active-inference behavioral modeling. The following subsections place it against each, emphasizing what COGANT provides as infrastructure rather than as a novel model, compiler, theorem prover, or benchmark.

**Classical program analysis** supplies the fixpoint and abstraction discipline. Kildall's global data-flow framework and the Cousots' abstract interpretation both model analysis as iteration over finite or suitably ordered abstract states [@kildall1973unified; @cousot1977abstract]. COGANT adopts that shape for rule application over a finite program graph, while making the deliberate engineering trade-off that mappings are evidence records rather than sound abstract semantics for all executions.

**Machine learning for big code** surveys cover naturalness, representation learning, and task taxonomy [@allamanis2018survey]. COGANT contributes **infrastructure**: a documented IR, pipeline, and export contract rather than a new benchmark or model architecture.

**Graph neural networks** unify message-passing frameworks for relational data [@wu2020comprehensive; @scarselli2009graph]. Although COGANT's primary output is the Active Inference Institute's Generalized Notation Notation, its program graph can be materialised as optional tensor views compatible with these frameworks (PyG [@fey2019pyg], DGL [@wang2019dgl]) so that graph-neural-network model papers can cite a specific tensor layout.

**Code property graphs** and related security-oriented graph constructions show how to merge syntactic and semantic edges for analysis [@yamaguchi2014modeling]. COGANT’s program graph is cognate but emphasizes **ML export**, confidence scoring, and multi-stage IR refinement.

**Visualization and graph drawing** supply the inspection discipline for COGANT's human-facing artifacts. Software visualization has long been framed as graphical representation of otherwise intangible program structures and process data [@gracanin2005software], and program-comprehension research stresses that navigation and orientation support are evaluation questions, not just rendering questions [@storey2005program]. Graph-visualization surveys emphasize that navigation, clustering, and scale management are method choices rather than decorative afterthoughts [@herman2000graph]. Layered directed layouts make hierarchy legible when containment dominates [@sugiyama1981methods; @gansner1993technique], force-directed layouts remain useful for less hierarchical relation clusters [@fruchterman1991graph], and node-link versus matrix readability depends on graph size, density, and task [@ghoniem2004comparison]. Interactive visual-analytics work stresses that useful views should support overview, filtering, drill-down, and task-specific inspection rather than a single static picture [@shneiderman1996eyes; @heer2012interactive; @brehmer2013typology; @bostock2011d3; @hohman2019visual]. COGANT adopts this as an artifact contract: a figure should expose the source JSON, role or relation encoding, limitation boundary, and count/digest sidecar needed to audit a conversion stage. CodeCity's software-city work is an instructive caution: visual metaphors become useful only when source facts are mapped meaningfully, not merely because the picture is polished [@wettel2007cities].

## Related tool categories

- **Compiler and LLVM IRs** — richer semantics, heavier toolchain; COGANT favors lightweight extraction for dataset building.
- **SCA and linters** — rule enforcement focus; COGANT focuses on graph generation for downstream learning.
- **Neural code models** (code2vec, CodeBERT, etc.) — often consume tokens or AST paths; COGANT supplies **explicit program graphs** that graph-neural-network-centric research can ingest directly.
