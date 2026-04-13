# Schemas reference

Quick reference for every intermediate representation (IR) and export schema used by COGANT. Authoritative source is `py/cogant/schemas/` — this document is a human-readable index intended to be stable across minor versions.

> COGANT's "GNN" is the Active Inference Institute's **Generalized Notation Notation**, a structured notation for state-space / process models. It is not graph neural networks.

### Versioning

- Each IR family has an independent `schema_version` (`MAJOR.MINOR.PATCH`).
- **Minor** bumps are backward-compatible additions.
- **Major** bumps break field shape and require a migration rule.
- Every exported artifact carries the COGANT version and a config hash for reproducibility.

### Schema families

| Family | Module | Top-level class | Purpose |
|---|---|---|---|
| Core | `cogant.schemas.core` | `Node`, `Edge`, `NodeKind`, `EdgeKind` | Typed nodes/edges used across the pipeline |
| Program graph | `cogant.schemas.graph` | `ProgramGraph`, `GraphMetadata` | The primary program representation |
| Semantic mapping | `cogant.schemas.semantic` | `SemanticMapping`, `MappingRole`, `Confidence` | Code-to-GNN semantic bridge |
| State space | `cogant.schemas.statespace` | `StateVariable`, `Observation`, `Action`, `Transition`, `Likelihood`, `Preference` | Active Inference state-space model |
| Process | `cogant.schemas.process` | `ProcessStage`, `Connection`, `Policy` | Extracted workflow / scheduler |
| Provenance | `cogant.schemas.provenance` | `Evidence`, `EvidenceKind` | Source-level evidence records |
| Validation | `cogant.schemas.validation` | `ValidationIssue`, `ValidationReport` | Schema/provenance/confidence check results |
| GNN export | `cogant.schemas.gnn_export` | `GNNExportBundle`, `GNNMetadata` | Bundle shape emitted to disk |
| Bundle | `cogant.api.bundle` | `Bundle` | Pipeline-wide container with `artifacts` and `stage_results` |

### Core: nodes and edges

#### `NodeKind` (enum, 18 kinds)

`REPO`, `MODULE`, `FILE`, `CLASS`, `FUNCTION`, `METHOD`, `VARIABLE`, `ENDPOINT`, `EVENT`, `PARAMETER`, `RETURN_VALUE`, `DATA_STRUCTURE`, `CONFIGURATION`, `FEATURE_FLAG`, `TEST`, `ASSERTION`, `POLICY`, `ACTION`.

#### `EdgeKind` (enum, 18 relations)

`CONTAINS`, `IMPORTS`, `INHERITS`, `IMPLEMENTS`, `DEPENDS_ON`, `READS`, `WRITES`, `RETURNS`, `CALLS`, `THROWS`, `CATCHES`, `YIELDS`, `OBSERVES`, `MUTATES`, `GUARDS`, `TRIGGERS`, `EVIDENCE_FROM_STATIC`, `EVIDENCE_FROM_DYNAMIC`.

#### `Node`

```python
@dataclass
class Node:
    id: str                      # stable hash of kind + qualified_name
    kind: NodeKind
    name: str
    qualified_name: str | None
    path: str | None
    language: str | None
    span: SourceSpan | None      # start/end line numbers
    type_info: TypeInfo | None   # declared + inferred types
    attributes: dict[str, Any]
    provenance: list[Evidence]
    created_at: datetime
```

#### `Edge`

```python
@dataclass
class Edge:
    id: str                      # hash of source + target + kind + line
    source_id: str
    target_id: str
    kind: EdgeKind
    directed: bool
    weight: float | None
    attributes: dict[str, Any]
    provenance: list[Evidence]
```

### Program graph

```python
@dataclass
class GraphMetadata:
    repo_uri: str
    languages: set[str]
    version: str
    created_at: datetime

@dataclass
class ProgramGraph:
    id: str
    metadata: GraphMetadata
    nodes: dict[str, Node]     # keyed by node.id
    edges: dict[str, Edge]     # keyed by edge.id
```

Exported as `program_graph.json`, `typed_graph.json`, and replicated in GraphML (`program_graph.graphml`) and Parquet (`parquet/nodes.parquet`, `parquet/edges.parquet`).

### Semantic mapping

```python
@dataclass
class SemanticMapping:
    id: str
    source_graph_elements: list[str]     # node/edge IDs
    role: MappingRole                    # hidden_state | observation | action | policy | preference | context | factor
    kind: str                            # rule name ("ReadOnlyInputRule", etc.)
    confidence: Confidence
    evidence: list[Evidence]
    metadata: dict[str, Any]
```

Exported as `semantic_mappings.json` (grouped by `mappings_by_role`).

### State space model

```python
@dataclass
class StateVariable:
    id: str
    name: str
    cardinality: int | None
    domain: list[str]
    factor: str | None
    provenance: list[Evidence]

@dataclass
class Observation:
    id: str
    name: str
    values: list[str]
    source_node_id: str          # which graph node this observation channels
    evidence: list[Evidence]

@dataclass
class Action:
    id: str
    name: str
    actor: str | None
    preconditions: list[str]
    effects: list[str]
    control_scope: list[str]
    evidence: list[Evidence]

@dataclass
class Transition:
    id: str
    from_states: list[str]
    to_states: list[str]
    action_id: str | None        # which action triggers this transition
    conditions: list[str]
    probability: float
    evidence: list[Evidence]

@dataclass
class Likelihood:
    id: str
    observations: list[str]
    conditioned_on: list[str]
    evidence: list[Evidence]

@dataclass
class Preference:
    id: str
    over: list[str]
    source: str                  # test | config | policy | annotation
    evidence: list[Evidence]

@dataclass
class StateSpaceModel:
    id: str
    schema_name: str
    kind: str                    # discrete | continuous | hybrid
    time: TimeSettings
    variables: dict[str, StateVariable]
    observations: dict[str, Observation]
    actions: dict[str, Action]
    transitions: dict[str, Transition]
    likelihoods: dict[str, Likelihood]
    preferences: dict[str, Preference]
    metadata: dict[str, Any]
```

Exported as `state_space.json`, `observations.json`, `actions.json`, `transitions.json`, `preferences.json`, `factors.json`.

### Process model

```python
@dataclass
class ProcessStage:
    id: str
    name: str
    type: str                    # function | service | job | workflow | external_event
    predecessors: list[str]
    successors: list[str]
    triggers: list[str]
    side_effects: list[str]

@dataclass
class Policy:
    id: str
    actor: str
    decision_points: list[str]
    retry_logic: str | None

@dataclass
class ProcessModel:
    id: str
    schema_name: str
    stages: dict[str, ProcessStage]
    connections: dict[str, Connection]
    policies: dict[str, Policy]
    timelines: list[Timeline]
```

Exported as `process_model.json`, `process_gantt.html`, `process_timeline.mermaid`.

### Provenance

```python
class EvidenceKind(Enum):
    SOURCE_SPAN = "source_span"
    AST_FACT = "ast_fact"
    TRACE_EVENT = "trace_event"
    TEST_ASSERTION = "test_assertion"
    CONFIG_ENTRY = "config_entry"
    COMMIT_EVENT = "commit_event"
    REVIEW_ACTION = "review_action"

@dataclass
class Evidence:
    id: str
    kind: EvidenceKind
    uri: str
    file: str | None
    line_start: int | None
    line_end: int | None
    symbol: str | None
    excerpt_hash: str | None
    generated_by_stage: str
    generated_by_rule: str
    timestamp: datetime
```

Every `Node`, `Edge`, `SemanticMapping`, state-space component, and process element carries a `provenance` list. **No element may be exported without provenance.**

### Validation report

```python
@dataclass
class ValidationIssue:
    name: str
    level: str                   # info | warning | error
    status: str                  # pass | fail | skipped
    category: str
    message: str
    details: dict[str, Any]

@dataclass
class ValidationReport:
    report_id: str
    bundle_id: str
    checks: list[ValidationIssue]
    metrics: dict[str, float]    # node_count, edge_count, mapping_count,
                                 # unresolved_count, provenance_coverage, confidence_mean
    recommendations: list[str]
```

Exported as `validation_report.json`, `gnn_validation_report.json`.

### GNN export bundle

See `py/cogant/schemas/gnn_export.py` for the Pydantic model. The on-disk shape is one `gnn_package/` directory per build containing 14+ files:

```
gnn_package/
├── manifest.json
├── model.gnn.md              # canonical 18-section Markdown
├── model.gnn.json            # machine-readable equivalent
├── state_space.json
├── observations.json
├── actions.json
├── transitions.json
├── preferences.json
├── factors.json
├── provenance.json
├── ontology.json
├── connections.json
├── actions_policies.json
├── preferences_constraints.json
├── visualizations/
└── diagrams/
```

The 18 canonical Markdown sections, in order:

1. Model Metadata
2. Repository Metadata
3. Source Coverage
4. State Space
5. Observation Modalities
6. Actions / Policies
7. Connections
8. Factors
9. Transition Structure
10. Likelihood Structure
11. Preferences / Constraints
12. Time Settings
13. Parameterization
14. Ontology Mapping
15. Provenance
16. Confidence Scores
17. Rendering Hints
18. Validation Notes

### Stability guarantees

- **Core schemas** (`Node`, `Edge`, `ProgramGraph`, `SemanticMapping`): stable since v0.1.0.
- **State-space schema**: stable since v0.1.0.
- **GNN export contract (18 sections)**: locked in `gnn.validator.GNNValidator.CANONICAL_SECTIONS`. Do not add or remove sections without a major-version bump.
- **Provenance schema**: stable since v0.1.0. New `EvidenceKind` values may be added in minor versions but existing values must never be renamed.

### Cross-references

- `docs/SPEC.md` — prose specification
- `docs/ARCHITECTURE.md` — layered architecture
- `docs/GNN_EXPORT.md` — GNN export contract detail
- `docs/VALIDATION.md` — validation check list
- `specs/schemas/` — machine-readable schema fragments

