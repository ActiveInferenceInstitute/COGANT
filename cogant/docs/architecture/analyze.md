## Analyze
obs_mappings = engine.get_mappings_by_kind(MappingKind.OBSERVATION)
stats = engine.get_statistics()
```

#### 3.2 Translation Rules (`cogant/translate/rules.py`)

**8 Concrete Rule Implementations:**

##### ReadOnlyInputRule
- **Pattern:** Modules with many read operations, no writes
- **Mapping:** OBSERVATION
- **Semantic:** System observes/reads from this module
- **Use Case:** Data sources, sensors, external APIs

##### MutatingSubsystemRule
- **Pattern:** Classes with frequent internal mutations (3+ WRITES/MUTATES edges)
- **Mapping:** HIDDEN_STATE
- **Semantic:** Maintains internal stateful behavior
- **Use Case:** Stateful objects, databases, caches

##### OrchestratorRule
- **Pattern:** Functions/classes with high call fan-out (5+ calls)
- **Mapping:** ORCHESTRATION
- **Semantic:** Coordinates/controls multiple subsystems
- **Use Case:** Controllers, schedulers, dispatchers

##### TestAssertionRule
- **Pattern:** Test functions with assertion calls
- **Mapping:** CONSTRAINT
- **Semantic:** Defines system constraints and invariants
- **Use Case:** Expected behavior, safety properties

##### RetryPatternRule
- **Pattern:** Functions matching "retry", "backoff", "circuit", "breaker", "timeout", "fallback"
- **Mapping:** POLICY
- **Semantic:** Policy for handling uncertainty/failures
- **Use Case:** Resilience, fault tolerance

##### EventBusRule
- **Pattern:** Event nodes with subscribers/triggers
- **Mapping:** OBSERVATION
- **Semantic:** Couples observations to actions
- **Use Case:** Event-driven systems, pub-sub

##### ConfigRule
- **Pattern:** CONFIGURATION nodes
- **Mapping:** CONTEXT
- **Semantic:** Provides system context/parameters
- **Use Case:** Settings, environment variables

##### FeatureFlagRule
- **Pattern:** FEATURE_FLAG nodes
- **Mapping:** CONTEXT
- **Semantic:** Selects system context/behavior
- **Use Case:** Feature toggles, A/B tests, rollouts

#### 3.3 ConfidenceModel (`cogant/translate/confidence.py`)

**Purpose:** Score and tier semantic mappings by evidence quality.

**Confidence Tiers:**
- `STATIC_ONLY` - From static analysis alone (threshold: 0.5)
- `STATIC_PLUS_RUNTIME` - Combined static + dynamic (threshold: 0.65)
- `RUNTIME_ONLY` - From runtime/dynamic (threshold: 0.4)
- `HUMAN_REVIEWED` - Manually validated (threshold: 0.9)

**Confidence Computation:**
```
score = (avg_evidence + diversity_bonus) * parser_certainty - conflict_penalty

where:
  - avg_evidence = average confidence of all evidence pieces
  - diversity_bonus = up to 0.1 based on evidence source diversity
  - parser_certainty = static analysis parser confidence
  - conflict_penalty = penalties for conflicting evidence
```

**Key Methods:**
- `compute_confidence_score()` - Overall confidence (0.0-1.0)
- `determine_confidence_tier()` - Assign tier based on sources
- `score_evidence_diversity()` - Measure source diversity
- `detect_conflicts()` - Find and score conflicts
- `update_mapping_confidence()` - Update all fields
- `score_batch()` - Score multiple mappings
- `get_high_confidence_mappings()` - Filter by threshold
- `get_scoring_report()` - Statistics

**Example:**
```python
from cogant.translate.confidence import ConfidenceModel

model = ConfidenceModel()
