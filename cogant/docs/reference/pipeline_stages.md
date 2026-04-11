## Pipeline Stages

> **Canonical source:** `cogant/evaluation/METRICS.yaml` (`pipeline.stage_count`, `pipeline.stages`).
> The current pipeline has **8 stages**: `ingest → parse → graph → translate → statespace → markov → gnn → reverse`.
> Earlier R&D drafts described a 9- or 10-stage layout (with separate `static`, `normalize`, `dynamic`, `process`, `export`, `validate` stages); those have been merged into the current 8-stage DAG. The legacy stage numbering still appears in some `docs/architecture/` and `docs/evaluation/` pages and is being progressively updated.

### Stage 1: Ingest

**Input**: Directory path or git URL
**Output**: File manifest with metadata

Load target codebase, enumerate files, detect languages, load configuration.

### Stage 2: Parse

**Input**: File manifest + source files
**Output**: AST + types + symbols + imports + call graph + data flow per file

Extract AST, types, symbols, imports, call graph, and data flow per file using language-specific parsers (tree-sitter, Python AST, etc.). This stage absorbs the legacy `static` and `normalize` steps: identities are resolved and entities canonicalized inline.

### Stage 3: Graph

**Input**: Parsed entities
**Output**: `ProgramGraph` IR

Build the program graph: nodes, edges, confidence, provenance. The `ProgramGraph` is the lower lattice of the COGANT Galois connection.

### Stage 4: Translate

**Input**: `ProgramGraph` IR
**Output**: Translated graph + semantic role assignments

Apply the **19 translation rules** via fixpoint iteration, resolve conflicts, assign semantic roles (HIDDEN_STATE, OBSERVATION, ACTION, POLICY, CONSTRAINT, CONTEXT, DATA_FLOW), compute per-mapping confidence.

### Stage 5: Statespace

**Input**: Translated graph
**Output**: State-space model

Compile state-space model: identify hidden-state variables, extract actions, infer transitions, collect observations.

### Stage 6: Markov

**Input**: Translated graph + state-space model
**Output**: Markov blanket partition

Partition the program graph into the four Markov blanket sets: internal states (HIDDEN_STATE), sensory states (OBSERVATION), active states (ACTION), external states (CONTEXT).

### Stage 7: GNN

**Input**: Statespace + Markov partition
**Output**: GNN package directory (Generalized Notation Notation, Active Inference Institute spec — **not** graph neural networks)

Emit the GNN model artifact: `model.gnn.json`, `model.gnn.md`, A/B/C/D matrices, ontology annotations. This is the upper lattice of the Galois connection.

### Stage 8: Reverse

**Input**: GNN package
**Output**: Synthesized Python `PackagePlan`

Run the reverse pipeline: `GNNModel → ReverseGNNModel → PackagePlan → synthesized Python source`. The reverse pipeline closes the Galois loop. Roundtrip fidelity is measured by ε = `|roles_preserved| / |roles_original|`; ε ≥ 0.8 = ISOMORPHIC. Current benchmark: **23/23 ISOMORPHIC, mean ε = 1.0** (see `cogant/evaluation/METRICS.yaml`).
