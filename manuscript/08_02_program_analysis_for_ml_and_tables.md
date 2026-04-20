# Program analysis for machine learning and comparison tables {#sec:08-02-program-analysis-for-ml-and-tables}

## Program analysis for ML

Several systems address the intersection of program analysis and machine learning that COGANT operates in:

**code2seq and code2vec** [@alon2019code2vec] represent programs as sets of AST paths between terminal nodes. These path-based representations are effective for method naming and code summarization but discard the full graph topology that graph-neural-network-based models exploit. COGANT preserves the complete program graph — including control-flow and data-flow edges — and can export it in tensor form, enabling downstream architectures that reason over richer relational structure.

**Learning to Represent Programs with Graphs** [@allamanis2018learning] is the closest conceptual neighbour: it constructs typed graphs fusing AST, control, and data-flow edges and feeds them to a gated graph neural network for variable-misuse and variable-naming tasks. COGANT's program graph IR generalises that construction into a pluggable and confidence-annotated pipeline, and its export contract is designed so that the tensor output remains directly compatible with gated-message-passing architectures in the same family.

**Gated Graph Neural Networks (GGNN)** [@li2016gated] introduced gated recurrent propagation for graph-structured program representations, demonstrating strong results on variable misuse detection and other code tasks. COGANT's export contract (PyG `Data` objects with typed `edge_index` and `edge_attr` [@fey2019pyg]) is directly compatible with GGNN-style models; the kind and role indices provide the discrete node and edge types that typed message-passing layers require.

**Typilus** [@allamanis2020typilus] and **LambdaNet** [@wei2020lambdanet] use graph neural networks to predict type annotations from structural program graphs. Both consume exactly the kind of typed adjacency structure COGANT emits, and both rely on message passing over node kinds similar to COGANT's `NodeKind` taxonomy, so COGANT's exports can serve as an upstream graph generator for Typilus- and LambdaNet-style type inference.

**CodeQL** (Semmle/GitHub), whose declarative query language QL is formalised in [@avgustinov2016ql], provides a declarative query language over relational representations of code. While CodeQL excels at security analysis with hand-written queries, its outputs are query results rather than tensor-ready graph bundles. COGANT occupies the complementary niche: it produces the graph data that learned models consume, and could ingest CodeQL query results as an additional evidence source feeding the confidence model.

**CodeBERT** [@feng2020codebert] and related pre-trained models operate at the token level, learning representations from natural language and code jointly. **GraphCodeBERT** [@guo2021graphcodebert] extends this line by injecting data-flow edges into the pre-training objective, which shows that even token-level models benefit from the kinds of data-flow relationships COGANT surfaces first-class in its program graph. These models are complementary to COGANT's graph-centric approach: their embeddings can serve as optional node features in COGANT's Generalized Notation Notation (GNN) export (the export schema already reserves dimensions for text embeddings as documented in `../cogant/docs/export/README.md`).

### Feature matrix: COGANT vs. related tools

The following matrix contrasts COGANT's capabilities with the related tools discussed in this section. Entries marked "yes" indicate first-class support; "partial" indicates limited or indirect support; "no" indicates the feature is out of scope for that tool.

**Table 15. Feature comparison of program-to-model toolchains.**

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
| Multi-language front-ends | partial (Python; JS/TS optional) | yes | no | yes | yes |

COGANT is distinct from the other toolchains in three ways: first, it explicitly models uncertainty through confidence tiers tied to evidence provenance; second, it produces a structured Active Inference notation as its primary output rather than an opaque tensor; and third, it composes static and dynamic evidence in a single pipeline rather than specializing to one.

### Input/output comparison vs prior art

Table 15 contrasts fine-grained feature flags; Table 16 expands the frame to include the *input/output contract* of each approach, because the most consequential difference between COGANT and its neighbours is what a user has to supply (training data, hand-written queries, manual modelling) and what they get back (vector, query table, simulator-ready model). The comparison covers code-representation learning (code2vec), learned graph models for programs (GGNN, Typilus, LambdaNet), code-property-graph-based analysers (CodeQL, the original Joern/CPG line), compiler IRs (PDG, LLVM IR, MLIR), and Active Inference tooling (hand-authored GNN with PyMDP as the downstream runtime).

**Table 16. Input/output comparison of COGANT and prior approaches.**

| Approach | Primary input | Primary output | Requires training | Languages (as shipped) | Produces Active Inference model |
|---|---|---|:---:|---|:---:|
| **COGANT** (this work) | Source repository (checkout or URL) | Generalized Notation Notation bundle (A/B/C/D, state space, Markov blanket, tensor views) | no | Python; JS/TS optional (`cogant[multilang]` + grammars) | yes (end-to-end) |
| code2vec / code2seq [@alon2019code2vec] | Single method or function body | Fixed-size embedding vector (predicted method name or tag) | yes (14M-method corpus) | Java (primary), C\#, Python (partial) | no |
| Gated GNN for programs [@allamanis2018learning; @li2016gated] | Typed program graph (AST + control + data-flow) | Task-specific prediction (variable misuse, variable naming) | yes (task-specific labels) | C\# (original), Java | no |
| Typilus [@allamanis2020typilus] / LambdaNet [@wei2020lambdanet] | Typed program graph | Predicted type annotations | yes | Python / TypeScript | no |
| Program Dependence Graph [ferrante1987pdg; horwitz1990slicing] | Single procedure or interprocedural bundle | PDG / System Dependence Graph | no | Any (formalism-level) | no |
| LLVM / MLIR IR [@lattner2004llvm; @lattner2021mlir] | Source in supported front-end language | SSA-form compiler IR, optimisation passes, code generation | no | C/C++/Rust/Swift/many via LLVM | no |
| CodeQL / QL [@avgustinov2016ql] | Source repository + hand-written query | Query result table (alerts, findings) | no | Python, JS/TS, Java, C\#, Go, C/C++ | no |
| CodeBERT / GraphCodeBERT [@feng2020codebert; @guo2021graphcodebert] | Token (and DFG) sequence for a code fragment | Contextual embeddings for downstream tasks | yes (multi-million-pair corpus) | Python, Java, JS, PHP, Ruby, Go | no |
| PyMDP [@heins2022pymdp] | Hand-authored A/B/C/D matrices (Python objects) | Active Inference simulation trajectories | no | N/A (runtime, not extractor) | yes (consumer of hand-authored input) |
| Generalized Notation Notation reference [@friedman2024gnn] | Hand-authored GNN Markdown or JSON | State-space/process model artifacts | no | N/A (notation + validator) | yes (format, not extractor) |

Three things are visible in this table that the fine-grained feature matrix does not capture. First, **COGANT is the only row whose input is a raw repository and whose output is a simulator-ready Active Inference model**: every other Active-Inference entry in the rightmost column (PyMDP, the GNN reference) requires a human to author the model by hand, and every code-modelling entry (code2vec through CodeBERT) produces either a vector, a type annotation, or a query result rather than a generative model. Second, **COGANT's rule-based pipeline does not require training**, which places it alongside the compiler-IR and code-property-graph lines rather than the learned-embedding lines in @sec:08-scope-and-related-work's "training" column. Third, **the languages column highlights that COGANT's v0.5.x front-end set (Python first-class; JavaScript / TypeScript via optional `cogant[multilang]` and `tree-sitter` when installed) is a deliberate scope choice, not a structural limitation**: the rule engine and state-space compiler consume a language-agnostic `ProgramGraph` IR, so adding a further parser (Java, Go, Rust, C/C++) is a matter of implementing the plugin interface in `../cogant/docs/plugins/README.md` and does not touch the translation, matrix, or export layers. The `examples/zoo/13_js_observer` cross-language round-trip (§5 and `cogant/docs/evaluation/ROUNDTRIP_IMPROVEMENT.md`) establishes the template for validating new parsers before release.

## See also (MkDocs)

Export / tensor interop details: [`../cogant/docs/export/README.md`](../cogant/docs/export/README.md).

