# Schemas — ~70 Core Types for COGANT Pipeline

Canonical Pydantic and dataclass definitions for all data structures: program graphs, semantic mappings, state spaces, process models, GNN packages, and validation metadata. All types encode provenance and confidence.

## Base Types (base.py)
- CogantBaseModel — Pydantic BaseModel with COGANT defaults and validators
- StableID — opaque string ID for objects (immutable across revisions)
- SemanticVersion — SemVer string (major.minor.patch)
- Span — source location (file, line_start, line_end, col_start, col_end)
- EvidenceRef — reference to evidence item (source_type, source_id, confidence)
- TypeInfo — type annotation (type_name, is_generic, type_parameters, type_origin)
- ConfidenceMetric — confidence metadata (score: float, tier: str, provenance: List)
- LocationInfo — location in source (filename, line, column, context)

## Core Graph Types

### core.py
- NodeKind — enum (MODULE, CLASS, FUNCTION, VARIABLE, CONSTANT, PARAMETER, FIELD, IMPORT, INTERFACE, PACKAGE, TRAIT, TYPE_ALIAS, etc.)
- EdgeKind — enum (CALLS, READS, WRITES, INHERITS, IMPLEMENTS, CONTAINS, DEPENDS_ON, etc.)

### graph.py
- GraphMetadata — metadata for graph (name, version, language, source_root, created_at, updated_at)
- ProgramGraph — core graph container (nodes: Dict[str, Node], edges: Dict[str, Edge], metadata: GraphMetadata)

### program_graph.py (legacy/extended variant)
- Node — extended node with attributes (id, kind, name, type, position, attributes, metadata)
- Edge — extended edge with attributes (id, kind, source, target, weight, attributes, metadata)
- ProgramGraph — extended variant

## Semantic & Mapping Types

### semantic.py
- MappingKind — enum (OBSERVATION, ACTION, HIDDEN_STATE, CONTEXT, POLICY, CONSTRAINT, PREFERENCE, DATA_FLOW, CONTROL_FLOW, ERROR_HANDLING, ORCHESTRATION, RETRY_PATTERN, CIRCUIT_BREAKER, FEATURE_FLAG)
- ConfidenceTier — enum (STATIC_ONLY, STATIC_PLUS_RUNTIME, RUNTIME_ONLY, HUMAN_REVIEWED)
- ProvenanceRecord — dataclass (source: str, timestamp: datetime, metadata: Dict, confidence: float)
- SemanticMapping — dataclass (id, kind, graph_fragment_node_ids, semantic_label, description, confidence_score, confidence_tier, provenance, evidence_count, evidence_diversity, parser_certainty, conflict_penalties, status, reviewed_by, reviewed_at, created_at, updated_at)

### semantic_mapping.py (Pydantic variant)
- SemanticRole — enum (OBSERVATION, ACTION, HIDDEN_STATE, etc.)
- MappingRule — rule for creating mapping (rule_name, rule_parameters, evidence)
- SourceGraphElement — element in source graph (element_id, kind, attributes)
- TargetSemanticElement — element in semantic domain (semantic_type, semantic_label, properties)
- ReviewStatus — enum (PENDING, ACCEPTED, REJECTED, NEEDS_REVISION)
- SemanticMapping — Pydantic model (source_elements, target_element, rule, status, review_notes, confidence, created_at, updated_at)
- SemanticMappingCollection — collection of mappings (mappings: List[SemanticMapping])

## State Space Types (state_space.py)
- StateSpaceKind — enum (DISCRETE, CONTINUOUS, HYBRID)
- StateVariable — variable in state space (name, kind, domain, initial_value, bounds)
- ObservationModality — sensor/observation type (name, state_dependence, likelihood_type, parameters)
- Action — action in action space (name, preconditions, effects, cost)
- Transition — state transition (source, target, probability, guard_condition, effect)
- Likelihood — observation likelihood (observation, state, likelihood_type, parameters)
- StateSpaceModel — complete state space (state_variables, observation_modalities, actions, transitions, likelihoods)

## Process Model Types (process_model.py)
- ProcessKind — enum (SEQUENTIAL, PARALLEL, CONDITIONAL, LOOP, RECURSIVE)
- TriggerKind — enum (IMMEDIATE, EVENT_DRIVEN, TIME_DRIVEN, DATA_DRIVEN)
- SideEffect — side effect of process (kind, target, value)
- ProcessStage — stage in process (name, kind, trigger_kind, description, inputs, outputs, side_effects)
- ProcessPolicy — policy for process (name, condition, action, priority)
- ProcessTimeline — timeline metadata (start_time, end_time, duration, checkpoints)
- ProcessModel — complete process model (stages, policies, timeline)

## Bundle & Export Types

### bundle.py
- TargetLanguage — enum (PYTHON, JAVA, GO, RUST, JAVASCRIPT, etc.)
- TargetInfo — info for export target (language, version, framework)
- ProvenanceOrigin — origin of provenance (source_type, source_id, confidence)
- ArtifactPaths — paths to artifacts (graph_file, mappings_file, state_space_file, etc.)
- CoreBundleSchema — exported bundle (graph, semantic_mappings, state_space, process_model, target_info, artifact_paths)

### gnn_export.py (18 canonical GNN sections)
- GNNMetadata, RepositoryMetadata, SourceCoverage
- GraphSection, ObservationModalitySection, ActionPolicySection, ConnectionSection, FactorSection
- TransitionStructureSection, LikelihoodStructureSection, PreferenceConstraintSection
- TimeSettingSection, ParameterizationSection, OntologyMappingSection
- ProvenanceSection, ConfidenceSection, RenderingHints, ValidationNotes
- GNNExportBundle — complete GNN package (all 18 sections)

## Provenance Types (provenance.py)
- EvidenceKind — enum (STATIC_ANALYSIS, DYNAMIC_TRACE, HUMAN_REVIEW, TEST_CASE, DOCUMENTATION)
- ProvenanceRecord — evidence record (source: str, confidence: float, metadata: Dict, timestamp: datetime)
- ProvenanceStore — collection of provenance (records: List[ProvenanceRecord])

## Validation Types (validation.py)
- CheckLevel — enum (INFO, WARNING, ERROR)
- CheckStatus — enum (PASS, FAIL, SKIP)
- ValidationCheck — single check result (name, level, status, message)
- ValidationMetrics — summary metrics (total_checks, passed, failed, skipped, score_0_to_100)
- ValidationRecommendation — recommendation (category, message, priority, action_items)
- ValidationReport — full report (checks, metrics, recommendations)

## Usage

```python
from cogant.schemas import (
    ProgramGraph, Node, Edge, NodeKind, EdgeKind,
    SemanticMapping, MappingKind, ConfidenceTier,
    StateSpaceModel, StateVariable, ObservationModality,
    ProcessModel, ProcessStage,
    GNNExportBundle,
    ValidationReport
)

# Create graph
graph = ProgramGraph(
    nodes={"n1": Node(id="n1", kind=NodeKind.FUNCTION, name="foo")},
    edges={"e1": Edge(id="e1", kind=EdgeKind.CALLS, source="n1", target="n2")},
    metadata=GraphMetadata(name="example", language="python")
)

# Create mapping
mapping = SemanticMapping(
    id="obs_n1_abc123",
    kind=MappingKind.OBSERVATION,
    graph_fragment_node_ids=["n1"],
    semantic_label="foo - Read-Only Input",
    confidence_score=0.85,
    confidence_tier=ConfidenceTier.STATIC_PLUS_RUNTIME
)

# Create state space
state_space = StateSpaceModel(
    state_variables=[
        StateVariable(name="x", kind="continuous", bounds=[-1, 1])
    ],
    observation_modalities=[
        ObservationModality(name="sensor_obs", state_dependence=["x"])
    ]
)
```

## Design Principles
- Pydantic v2 for validation and serialization
- Dataclasses for lightweight, performance-critical records (ProvenanceRecord, SemanticMapping)
- Explicit confidence/provenance on every mapping and type
- Immutable where possible (StableID, SemanticVersion)
- Backward compatible via semantic versioning and deprecation flags

## Dependencies
- pydantic — validation and JSON serialization
- dataclasses — lightweight records
- typing — type hints
- datetime — timestamps and temporal types
- enum — enumerations
