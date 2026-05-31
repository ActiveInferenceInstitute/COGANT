# GNN export and error-handling philosophy {#sec:02-04-gnn-export-and-error-handling}

This section closes the four-part method core (program graph IR in
@sec:02-01-program-graph-and-formal-foundations, rule progression in
@sec:02-02-ir-progression-translation-engine, confidence and state-space
in @sec:02-03-confidence-state-space-and-behavior) by describing the
durable interchange boundary — Generalized Notation Notation — and the
error-handling discipline that prevents one bad rule firing from
poisoning the rest of an export. From here, @sec:03-api-and-workflows
explains how the API surfaces these artifacts to Python and CLI
consumers.

## GNN export (Generalized Notation Notation)

Exports package the program graph and compiled state-space model into the Active Inference Institute's **Generalized Notation Notation** plus a small set of interop targets. The upstream GNN repository describes Generalized Notation Notation as a text-based language for Active Inference generative models and provides a broader validation, visualization, and execution pipeline around those files [@friedman2024gnn]; COGANT's export layer treats that format as the durable interchange boundary.

- **GNN Markdown (`model.gnn.md`)** — canonical, human-readable Generalized Notation Notation organized into 19 canonical sections in the specification order defined in `../cogant/docs/export/README.md`.
- **GNN JSON (`model.gnn.json`)** — machine-readable equivalent of the markdown sections, plus companion JSON files per section (`state_space.json`, `observations.json`, `actions.json`, `transitions.json`, and so on).
- **Interop exports** — GraphML and Parquet for analysis in Gephi/yEd and DuckDB, and optional tensor views (PyTorch Geometric `Data` objects [@fey2019pyg], DGL graphs [@wang2019dgl], HDF5 tables [@hdfgroup2026hdf5spec]) for downstream graph neural network training pipelines that consume the program graph as a relational tensor. The JSON sidecars are validated by COGANT's package-native schema checks; they are not advertised as normative JSON Schema, JSON-LD, or SHACL artifacts unless an adapter explicitly emits those forms [@jsonSchema2020; @jsonLd11; @w3cShacl2017].

![Rendered first page of the calculator fixture's `model.gnn.md` bundle. The figure is generated from `cogant/output/calculator/gnn_package/model.gnn.md` and shows the human-readable Generalized Notation Notation artifact that travels beside JSON sidecars, validation reports, and provenance metadata. Read it as readability and interchange evidence for the emitted package format; machine validation still comes from the structured JSON and validation artifacts, not from the rasterized page.](../figures/cogant_gnn_markdown_render.png){#fig:cogant-gnn-markdown-render width=82%}

@fig:cogant-gnn-markdown-render is included because interchange formats have a human-review surface as well as a machine-ingestion surface. The rendered page lets a reviewer inspect section ordering, labels, and prose-facing bundle structure; it does not by itself validate that the matrices, role mappings, or downstream semantics are correct.

The export split mirrors two adjacent traditions. ProGraML shows why compiler and ML systems benefit from portable graph representations that explicitly encode control, data, and call dependencies [@cummins2021programl]. The graph-network literature frames this as a relational inductive bias: entities, relations, and global state should remain explicit so downstream models can reason compositionally over them [@battaglia2018relational]. COGANT keeps those graph relations available, but its primary exported object is a Generalized Notation Notation bundle with state-space and active-inference semantics rather than only an optimization dataset or a neural-model input.

### The 19-section GNN bundle structure

The canonical GNN specification organizes metadata, semantics, and generative-model components into 19 sections, each carrying distinct semantic load:

1. **Model Metadata** — provenance, name, version, creation timestamp, source repository URL, project description, and authorship information.
2. **Repository Metadata** — VCS details (commit hash, branch, remote origin), file inventory, and module topology.
3. **Source Coverage** — which source files were ingested, coverage percentage per file or module, parser and language backend used (CPython `ast`, tree-sitter, etc.), and parse-error inventory.
4. **State Space** — list of hidden-state variables extracted by the `MutatingSubsystemRule` and other structural rules, their dimensionality, and categorical cardinality if applicable.
5. **Observation Modalities** — observable variables (methods, properties, getters, sensors in the metaphor), their sources on the program graph, and the subset of hidden states each can read.
6. **Actions/Policies** — action-typed nodes (setter methods, clear operations, API calls) and associated policy candidates emitted by the semantic family and behavioural family rules.
7. **Program Graph Connections** — edges in the original program graph reduced to the Markov-blanket partition (internal vs. boundary nodes). Specifies which internal nodes influence which observations and actions.
8. **Factors** — nodes in the program graph labeled with their primary semantic role. Mapping kinds drawn from the formal alphabet $\mathcal{K}_M$ (HIDDEN_STATE, OBSERVATION, ACTION, POLICY, PREFERENCE, CONSTRAINT, CONTEXT, DATA_FLOW, ERROR_HANDLING, CIRCUIT_BREAKER, ORCHESTRATION — see @sec:def-translation-rule and @sec:98-active-inference-roles) carry the generative-model semantics; broader graph-level role annotations (for example CONFIGURATION, and illustrative descriptive tags such as event-bus or resilience patterns) come from the separate `SemanticRole` vocabulary and are not part of $\mathcal{K}_M$.
9. **Transition Structure** — the state-transition component B of the generative model, compiled from WRITES and CALLS edges. Specifies which actions update which state dimensions.
10. **Likelihood Structure** — the observation likelihood A, compiled from READS/OBSERVES/DEPENDS_ON edges. Specifies which hidden states produce which observations.
11. **Preferences/Constraints** — C and D components: preference (reward) weights on observations from PREFERENCE and CONSTRAINT mappings, and initial-state priors from CONFIGURATION edges.
12. **Time Settings** — discretization interval, episode length, and whether the model assumes a fixed or variable-length horizon.
13. **Parameterization** — fixed hyperparameters of the generative model (e.g., temperature, inverse-temperature, concentration parameters) and which are learned vs. fixed during active-inference execution.
14. **Ontology Mapping** — the semantic mapping of each program node (function, class, variable) to its AII role(s), plus the confidence band and rule family responsible for the assignment.
15. **Markov Blanket** — the Active-Inference partition of the program graph into internal (μ), sensory (s), active (a), and external (η) states, with the seed strategy and per-node rationale.
16. **Provenance** — which rules (by name and version) emitted each mapping, including the conflict-resolution logic that selected a winner when multiple rules proposed the same role.
17. **Confidence Scores** — per-mapping confidence bands and the source rule's calibration (typically 0.65–0.90) from `../cogant/docs/evaluation/CALIBRATION.md`.
18. **Rendering Hints** — layout and visualization metadata (node positions, color coding by role, cluster membership) consumed by downstream graphical tools.
19. **Validation Notes** — the output of the `GNNValidator` (see **AII validator and scoring** above; implementation in `../cogant/py/cogant/gnn/validator.py`) with section-by-section pass/fail status, any missing sections, and the composite 0–100 score.

Node and edge feature breakdowns, section contracts, and optional framework targets are specified in `../cogant/docs/export/README.md`; they determine the structure of the emitted notation and the effective input dimensionality of any downstream model.

### A/B/C/D matrix derivation from edge kinds

The four matrices of the Active Inference generative model are compiled directly from the program graph's edge kinds in the `GNNMatrices` class (module `gnn/matrices.py`):

- **Matrix A (likelihood)** — derived from READS, OBSERVES, and DEPENDS_ON edges. For each observation, A[observation, hidden_state] = 1.0 if an edge exists from that observation to that hidden state, 0.0 otherwise. Rows with no incoming edges from hidden states fall back to uniform distributions (maximum entropy in the absence of evidence).
- **Matrix B (transition)** — derived from WRITES and CALLS edges from actions to hidden states. For each action, B[hidden_state, hidden_state, action] encodes the state update: B[s', s, a] = 1.0 if action a writes state s to value s', identity otherwise. Actions with no outgoing WRITES edges fall back to the identity tensor (action has no effect on state), preserving the stay-move property.
- **Matrix C (preferences)** — derived from PREFERENCE and CONSTRAINT mappings on observations. C is a column vector per observation indexed by the observation's discrete values; entries come from the confidence bands of PREFERENCE mappings. Observations with no preference evidence are initialized to zero (neutral).
- **Matrix D (initial prior)** — derived from CONFIGURATION edges pointing to hidden states. D[hidden_state] is uniform over the state's cardinality, unless CONFIGURATION nodes provide evidence for specific initial values. Configurations with zero evidence default to uniform (maximum entropy).

These fallback paths—identity B, uniform A/D, zero C—are **documented degraded-output modes** (see **Degraded-output semantics** above and the user-facing walkthrough in [`04_examples_and_failure_modes.md`](04_examples_and_failure_modes.md)). When the program graph provides no edge evidence for a matrix entry, the engine emits a validation finding and supplies the appropriate maximum-entropy or identity fallback. The pipeline validates that all fallback tensors satisfy shape, sum-to-one, and non-negativity invariants; all shipped fixtures validate at 100.0 even with extensive fallbacks (e.g., `json_stdlib`, where {{ABLATION_JSON_STDLIB_B_ACTIONS_IDENTITY}} of its {{ABLATION_JSON_STDLIB_B_ACTIONS_TOTAL}} action slices default to the identity B tensor because the corresponding functions carry no WRITES edges to hidden states, still produces a valid B tensor).

### AII validator and scoring

The `GNNValidator` class in `gnn/validator.py` gates the export step by checking the 19 canonical sections and their internal consistency. The validator produces a composite score from 0 to 100:

- **Score 100**: all 19 sections present, matrices satisfy sum-to-one and non-negativity, ontology mappings are present for all high-confidence rules, and no parse errors or conflicting assignments exist.
- **Score 75–99**: minor issues (missing optional sections like Rendering Hints, sparse confidence annotations) that do not prevent active-inference execution.
- **Score 50–74**: degraded output (heavy use of fallbacks, missing entire role families) that still validates structurally but may lack semantic coverage.
- **Score 0–49**: fatal errors (missing required sections, malformed matrices, unresolvable conflicts).

All fixtures in @tbl:repo-pipeline-metrics score 100.0, including `json_stdlib` which relies heavily on fallback distributions. The validator score travels with every bundle in section 19 (Validation Notes) and gates structural and matrix validity. Runtime or semantic adequacy is a separate evidence question: high validator scores mean the bundle is well formed and executable by compatible tooling, not that the extracted matrices fully capture source-code behavior.

## Error handling philosophy

The implementation distinguishes fatal configuration or parse failures from per-file errors that allow partial results. Validation aggregates warnings and inconsistencies into a report that travels with the bundle. This mirrors the layered error categories documented in the architecture (fatal, error, warning, info).

**Degraded-output semantics** are explicit: when the pipeline lacks evidence for a rule or matrix entry, it emits a validation finding and supplies a documented fallback (identity-biased B, uniform A/D, zero C) rather than silently guessing or failing. The `DegradedOutput` NamedTuple tracks the type and location of each fallback:

```
DegradedOutput = NamedTuple(
    "DegradedOutput",
    [
        ("category", str),          # "matrix_fallback", "rule_noevidence", etc.
        ("location", str),          # "B[s', s, a]", "A[o, s]", section name, etc.
        ("reason", str),            # "no WRITES edges", "no PREFERENCE edges", etc.
        ("fallback_value", object), # identity tensor, uniform dist, 0, etc.
    ],
)
```

Every fallback is recorded in Validation Notes (section 19) alongside the reason and the fallback strategy used. This transparency lets users and downstream tools distinguish high-confidence, evidence-backed assignments from maximum-entropy defaults.
