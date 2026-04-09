# Scope and related work

## COGANT in the program-analysis landscape

COGANT sits at the intersection of three established research areas: machine learning for source code, graph-based program representations, and active-inference behavioral modeling. The following subsections place it against each, emphasizing what COGANT provides as infrastructure rather than as a novel model or benchmark.

**Machine learning for big code** surveys cover naturalness, representation learning, and task taxonomy [@allamanis2018survey]. COGANT contributes **infrastructure**: a documented IR, pipeline, and export contract rather than a new benchmark or model architecture.

**Graph neural networks** unify message-passing frameworks for relational data [@wu2020comprehensive; @scarselli2009graph]. Although COGANT's primary output is the Active Inference Institute's Generalized Notation Notation, its program graph can be materialised as optional tensor views compatible with these frameworks (PyG, DGL) so that graph-neural-network model papers can cite a specific tensor layout.

**Code property graphs** and related security-oriented graph constructions show how to merge syntactic and semantic edges for analysis [@yamaguchi2014modeling]. COGANT’s program graph is cognate but emphasizes **ML export**, confidence scoring, and multi-stage IR refinement.

## Related tool categories

- **Compiler and LLVM IRs** — richer semantics, heavier toolchain; COGANT favors lightweight extraction for dataset building.
- **SCA and linters** — rule enforcement focus; COGANT focuses on graph generation for downstream learning.
- **Neural code models** (code2vec, CodeBERT, etc.) — often consume tokens or AST paths; COGANT supplies **explicit program graphs** that graph-neural-network-centric research can ingest directly.

## Program analysis for ML

Several systems address the intersection of program analysis and machine learning that COGANT operates in:

**code2seq and code2vec** [@alon2019code2vec] represent programs as sets of AST paths between terminal nodes. These path-based representations are effective for method naming and code summarization but discard the full graph topology that graph-neural-network-based models exploit. COGANT preserves the complete program graph — including control-flow and data-flow edges — and can export it in tensor form, enabling downstream architectures that reason over richer relational structure.

**Learning to Represent Programs with Graphs** [@allamanis2018learning] is the closest conceptual neighbour: it constructs typed graphs fusing AST, control, and data-flow edges and feeds them to a gated graph neural network for variable-misuse and variable-naming tasks. COGANT's program graph IR generalises that construction into a pluggable and confidence-annotated pipeline, and its export contract is designed so that the tensor output remains directly compatible with gated-message-passing architectures in the same family.

**Gated Graph Neural Networks (GGNN)** [@li2016gated] introduced gated recurrent propagation for graph-structured program representations, demonstrating strong results on variable misuse detection and other code tasks. COGANT's export contract (PyG `Data` objects with typed `edge_index` and `edge_attr` [@fey2019pyg]) is directly compatible with GGNN-style models; the kind and role indices provide the discrete node and edge types that typed message-passing layers require.

**Typilus** [@allamanis2020typilus] and **LambdaNet** [@wei2020lambdanet] use graph neural networks to predict type annotations from structural program graphs. Both consume exactly the kind of typed adjacency structure COGANT emits, and both rely on message passing over node kinds similar to COGANT's `NodeKind` taxonomy, so COGANT's exports can serve as an upstream graph generator for Typilus- and LambdaNet-style type inference.

**CodeQL** (Semmle/GitHub), whose declarative query language QL is formalised in [@avgustinov2016ql], provides a declarative query language over relational representations of code. While CodeQL excels at security analysis with hand-written queries, its outputs are query results rather than tensor-ready graph bundles. COGANT occupies the complementary niche: it produces the graph data that learned models consume, and could ingest CodeQL query results as an additional evidence source feeding the confidence model.

**CodeBERT** [@feng2020codebert] and related pre-trained models operate at the token level, learning representations from natural language and code jointly. **GraphCodeBERT** [@guo2021graphcodebert] extends this line by injecting data-flow edges into the pre-training objective, which shows that even token-level models benefit from the kinds of data-flow relationships COGANT surfaces first-class in its program graph. These models are complementary to COGANT's graph-centric approach: their embeddings can serve as optional node features in COGANT's Generalized Notation Notation (GNN) export (the export schema already reserves dimensions for text embeddings as documented in `../cogant/docs/GNN_EXPORT.md`).

### Feature matrix: COGANT vs. related tools

The following matrix contrasts COGANT's capabilities with the related tools discussed in this section. Entries marked "yes" indicate first-class support; "partial" indicates limited or indirect support; "no" indicates the feature is out of scope for that tool.

**Table 8. Feature comparison of program-to-model toolchains.**

| Feature | COGANT | code2vec | GGNN | CodeQL | CodeBERT |
|---------|:------:|:--------:|:----:|:------:|:--------:|
| Full program graph (AST + CFG + DFG) | yes | no | input-only | yes | no |
| Typed node/edge taxonomy | yes | no | partial | yes | no |
| Confidence scoring per assertion | yes | no | no | no | no |
| Provenance tracking | yes | no | no | partial | no |
| State-space extraction | yes | no | no | no | no |
| Temporal regime classification | yes | no | no | no | no |
| Dynamic enrichment (coverage, traces) | yes | no | no | partial | no |
| Generalized Notation Notation output | yes | no | no | no | no |
| Tensor export (PyG, DGL, HDF5) | yes | partial | input-only | no | no |
| Pluggable translation rules | yes | no | no | yes | no |
| Human review loop | yes | no | no | partial | no |
| Multi-language front-ends | roadmap | yes | no | yes | yes |

COGANT is distinct from the other toolchains in three ways: first, it explicitly models uncertainty through confidence tiers tied to evidence provenance; second, it produces a structured Active Inference notation as its primary output rather than an opaque tensor; and third, it composes static and dynamic evidence in a single pipeline rather than specializing to one.

### Input/output comparison vs prior art

Table 8 contrasts fine-grained feature flags; Table 9 expands the frame to include the *input/output contract* of each approach, because the most consequential difference between COGANT and its neighbours is what a user has to supply (training data, hand-written queries, manual modelling) and what they get back (vector, query table, simulator-ready model). The comparison covers code-representation learning (code2vec), learned graph models for programs (GGNN, Typilus, LambdaNet), code-property-graph-based analysers (CodeQL, the original Joern/CPG line), compiler IRs (PDG, LLVM IR, MLIR), and Active Inference tooling (hand-authored GNN with PyMDP as the downstream runtime).

**Table 9. Input/output comparison of COGANT and prior approaches.**

| Approach | Primary input | Primary output | Requires training | Languages (as shipped) | Produces Active Inference model |
|---|---|---|:---:|---|:---:|
| **COGANT** (this work) | Source repository (checkout or URL) | Generalized Notation Notation bundle (A/B/C/D, state space, Markov blanket, tensor views) | no | Python (JS/TS roadmap) | yes (end-to-end) |
| code2vec / code2seq [@alon2019code2vec] | Single method or function body | Fixed-size embedding vector (predicted method name or tag) | yes (14M-method corpus) | Java (primary), C\#, Python (partial) | no |
| Gated GNN for programs [@allamanis2018learning; @li2016gated] | Typed program graph (AST + control + data-flow) | Task-specific prediction (variable misuse, variable naming) | yes (task-specific labels) | C\# (original), Java | no |
| Typilus [@allamanis2020typilus] / LambdaNet [@wei2020lambdanet] | Typed program graph | Predicted type annotations | yes | Python / TypeScript | no |
| Program Dependence Graph [ferrante1987pdg; horwitz1990slicing] | Single procedure or interprocedural bundle | PDG / System Dependence Graph | no | Any (formalism-level) | no |
| LLVM / MLIR IR [@lattner2004llvm; @lattner2021mlir] | Source in supported front-end language | SSA-form compiler IR, optimisation passes, code generation | no | C/C++/Rust/Swift/many via LLVM | no |
| CodeQL / QL [@avgustinov2016ql] | Source repository + hand-written query | Query result table (alerts, findings) | no | Python, JS/TS, Java, C\#, Go, C/C++ | no |
| CodeBERT / GraphCodeBERT [@feng2020codebert; @guo2021graphcodebert] | Token (and DFG) sequence for a code fragment | Contextual embeddings for downstream tasks | yes (multi-million-pair corpus) | Python, Java, JS, PHP, Ruby, Go | no |
| PyMDP [@heins2022pymdp] | Hand-authored A/B/C/D matrices (Python objects) | Active Inference simulation trajectories | no | N/A (runtime, not extractor) | yes (consumer of hand-authored input) |
| Generalized Notation Notation reference [@friedman2024gnn] | Hand-authored GNN Markdown or JSON | State-space/process model artifacts | no | N/A (notation + validator) | yes (format, not extractor) |

Three things are visible in this table that the fine-grained feature matrix does not capture. First, **COGANT is the only row whose input is a raw repository and whose output is a simulator-ready Active Inference model**: every other Active-Inference entry in the rightmost column (PyMDP, the GNN reference) requires a human to author the model by hand, and every code-modelling entry (code2vec through CodeBERT) produces either a vector, a type annotation, or a query result rather than a generative model. Second, **COGANT's rule-based pipeline does not require training**, which places it alongside the compiler-IR and code-property-graph lines rather than the learned-embedding lines in Section 8's "training" column. Third, **the languages column highlights that COGANT's Python-only v0.1.x front end is a deliberate scope choice, not a structural limitation**: the rule engine and state-space compiler consume a language-agnostic `ProgramGraph` IR, so adding a JavaScript/TypeScript parser is a matter of implementing the plugin interface in `../cogant/docs/PLUGIN_API.md` and does not touch the translation, matrix, or export layers.

## Active inference and program behavior

The state-space IR in COGANT's pipeline (states, actions, transitions, observations) shares structural parallels with **active inference** formulations [@friston2010free; @parr2022active], where an agent maintains beliefs about hidden states and selects actions to minimize prediction error. The discrete-state synthesis presented in [@dacosta2020active] is the closest formal target of COGANT's compilation: variables, actions, observation modalities, and transition structures in the Generalized Notation Notation bundle map directly onto the tuples required by a discrete-state active inference agent, and the step-by-step construction protocol of [@smith2022stepbystep] can be followed literally against those bundles. PyMDP [@heins2022pymdp] provides a reference Python runtime that executes exactly this form of agent, making it a natural downstream consumer of COGANT exports. In the program analysis context, the "agent" is the analysis pipeline itself: it observes code artifacts, maintains beliefs about program behavior (the state-space model), and refines those beliefs as new evidence (dynamic traces, coverage data) arrives.

This connection is analogical: the `ConfidenceModel` in `../cogant/py/cogant/translate/confidence.py` aggregates evidence and penalties in a way that suggests belief revision, but it is not a Bayesian posterior. Future work could formalize a tighter link by casting rule application as variational inference, where a fixpoint would represent an approximate posterior over program semantics.

## Boundaries

COGANT does not subsume formal verification, interactive theorem proving, or full interprocedural pointer analysis unless implemented as explicit future stages. The SPEC marks Rust acceleration and additional parsers as staged; the manuscript should be read together with that table for up-to-date scope.

## Forward compatibility

Promoting COGANT into [`../../../projects/`](../../../projects/) integrates manuscript PDF rendering with the template’s validation gates. Cross-references in this folder use paths **relative to these Markdown files** (for example [`../cogant/docs/`](../cogant/docs/)) so links stay stable when the tree moves.
