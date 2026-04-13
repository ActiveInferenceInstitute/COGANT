# Translate — Semantic Mapping via Pattern-Driven Rules

Applies 19 concrete TranslationRule subclasses to program graphs, discovering semantic concepts (observations, actions, policies, constraints, etc.) and scoring confidence via evidence combination.

## Core Classes

### TranslationEngine (engine.py)
Orchestrates rule application via fixpoint iteration until convergence. Provides register_rule(rule: TranslationRule) and translate(graph: ProgramGraph, rule_filter: Optional[List[str]]) -> List[SemanticMapping].

### TranslationRule (engine.py)
Abstract base class. Subclasses implement matches() (find patterns) and apply() (generate SemanticMapping).

### 22 Concrete Rules (rules.py)
1. ReadOnlyInputRule — read-only modules → OBSERVATION (prefix: `obs_`)
2. MutatingSubsystemRule — mutating state holders → HIDDEN_STATE (prefix: `hs_`)
3. OrchestratorRule — schedulers, controllers → ORCHESTRATION (prefix: `orch_`)
4. TestAssertionRule — test assertions → CONSTRAINT (prefix: `const_`)
5. RetryPatternRule — retry loops / backoff → POLICY (prefix: `policy_`)
6. EventBusRule — publish/subscribe systems → DATA_FLOW (prefix: `event_`)
7. ConfigRule — configuration files → CONTEXT (prefix: `ctx_`)
8. FeatureFlagRule — feature toggles → FEATURE_FLAG (prefix: `fflag_`)
9. ObservationRule — sensors / external inputs → OBSERVATION (prefix: `obs_`)
10. ActionRule — actuators / side-effect emitters → ACTION (prefix: `act_`)
11. PolicyRule — decision policies / strategies → POLICY (prefix: `pol_`)
12. PreferenceRule — goal and preference declarations → PREFERENCE (prefix: `pref_`)
13. ContextRule — contextual state holders → CONTEXT (prefix: `ctx_`)
14. InheritanceRule — class hierarchies → CONTROL_FLOW (prefix: `inh_`)
15. ContainmentRule — composition and nesting → CONTROL_FLOW (prefix: `cont_`)
16. DataPipelineRule — data transformation pipelines → DATA_FLOW (prefix: `dpipe_`)
17. ErrorBoundaryRule — error handling scopes → ERROR_HANDLING (prefix: `errbnd_`)
18. SingletonAccessRule — singleton access patterns → HIDDEN_STATE (prefix: `single_`)
19. CircuitBreakerRule — resilience / circuit breakers → CIRCUIT_BREAKER (prefix: `cb_`)

Note that ReadOnlyInputRule and ObservationRule share the `obs_` prefix because both produce OBSERVATION-kind mappings from different structural evidence; the tail hash disambiguates them.

### ConfidenceModel (confidence.py)
Scores SemanticMapping objects. compute_confidence_score(mapping: SemanticMapping) -> float combines evidence count, diversity bonus, parser certainty, and conflict penalties into 0.0-1.0 score. determine_confidence_tier() assigns ConfidenceTier (STATIC_ONLY, STATIC_PLUS_RUNTIME, RUNTIME_ONLY, HUMAN_REVIEWED).

### ReviewManager (review.py)
Curates mappings: accept_mapping(mapping_id, reviewer, feedback), reject_mapping(mapping_id, reviewer, reason), edit_mapping(mapping_id, updates), split_mapping(mapping_id, groups), merge_mappings(ids, merged_label). Tracks provenance of all changes.

## Data Model

### SemanticMapping (schemas/semantic.py)
- id: str — unique identifier
- kind: MappingKind — OBSERVATION, ACTION, HIDDEN_STATE, POLICY, CONSTRAINT, PREFERENCE, DATA_FLOW, CONTROL_FLOW, ERROR_HANDLING, ORCHESTRATION, RETRY_PATTERN, CIRCUIT_BREAKER, FEATURE_FLAG
- graph_fragment_node_ids: List[str] — graph nodes in this mapping
- semantic_label: str — human-readable label
- confidence_score: float — 0.0-1.0
- confidence_tier: ConfidenceTier — STATIC_ONLY, STATIC_PLUS_RUNTIME, RUNTIME_ONLY, HUMAN_REVIEWED
- provenance: List[ProvenanceRecord] — evidence chain
- evidence_count: int
- evidence_diversity: float — diversity of sources (0.0-1.0)
- parser_certainty: float — parser/static certainty (0.0-1.0)
- status: str — auto_proposed, accepted, rejected, edited, split, merged
- reviewed_by, reviewed_at, review_feedback — human review metadata

### ProvenanceRecord (schemas/semantic.py)
- source: str — "static_analysis", "dynamic_trace", "manual_review", etc.
- timestamp: datetime
- confidence: float — confidence of this evidence
- metadata: Dict[str, Any]

## Usage

```python
from cogant.translate.engine import TranslationEngine
from cogant.translate.rules import (
    ReadOnlyInputRule, MutatingSubsystemRule, OrchestratorRule,
    TestAssertionRule, RetryPatternRule, EventBusRule, ConfigRule,
    FeatureFlagRule, ObservationRule, ActionRule, PolicyRule,
    PreferenceRule, ContextRule, InheritanceRule, ContainmentRule,
    DataPipelineRule, ErrorBoundaryRule, SingletonAccessRule,
    CircuitBreakerRule
)
from cogant.translate.confidence import ConfidenceModel
from cogant.translate.review import ReviewManager

# Create engine and register rules
engine = TranslationEngine(max_iterations=10)
engine.register_rule(ReadOnlyInputRule())
engine.register_rule(MutatingSubsystemRule())
# ... register other rules

# Translate program graph
program_graph = ...  # ProgramGraph instance
mappings = engine.translate(program_graph)

# Score with ConfidenceModel
confidence_model = ConfidenceModel()
for mapping in mappings:
    score = confidence_model.compute_confidence_score(mapping)
    tier = confidence_model.determine_confidence_tier(mapping, score)
    mapping.confidence_score = score
    mapping.confidence_tier = tier

# Review mappings
reviewer = ReviewManager()
for mapping in mappings:
    reviewer.add_mapping(mapping)

# Accept/reject/edit mappings
reviewer.accept_mapping("obs_xyz", reviewer="alice", feedback="Looks good")
reviewer.reject_mapping("const_abc", reviewer="bob", reason="False positive")

# Export curated mappings
final_mappings = list(reviewer.mappings.values())
```

## Algorithm
TranslationEngine.translate() performs fixpoint iteration:
1. For each iteration (up to max_iterations):
   a. For each registered rule: find matches via rule.matches(graph, query)
   b. For each match: call rule.apply(graph, match) to generate SemanticMapping
   c. Deduplicate mappings by ID; count new_mappings
   d. If new_mappings == 0, break (convergence)
2. Return all accumulated mappings

## Dependencies
- schemas/ — ProgramGraph, SemanticMapping, MappingKind, ConfidenceTier, ProvenanceRecord
- graph/queries — GraphQuery for pattern matching
