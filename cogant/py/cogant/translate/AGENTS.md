# Agents — py/cogant/translate

## Owner
Semantic Lead

## Responsibilities
- Apply 19 concrete TranslationRule subclasses to discover semantic mappings in program graphs
- Generate SemanticMapping objects with confidence scores, provenance, and metadata
- Score mappings via ConfidenceModel based on evidence diversity, parser certainty, and conflicts
- Review and curate mappings using ReviewManager (accept, reject, edit, split, merge)
- Orchestrate fixpoint iteration until convergence for exhaustive pattern discovery

## Coordination
- Receives ProgramGraph from graph/
- Outputs List[SemanticMapping] with full provenance
- Confidence tiers (STATIC_ONLY, STATIC_PLUS_RUNTIME, RUNTIME_ONLY, HUMAN_REVIEWED) drive quality assessment
- Each mapping has a .kind (MappingKind enum: OBSERVATION, ACTION, HIDDEN_STATE, POLICY, CONSTRAINT, etc.)
- Integrates with gnn/ and schemas/ for export and validation

## How to extend
Add new TranslationRule subclasses to rules.py. Each rule must implement:
- matches(graph: ProgramGraph, query: GraphQuery) -> List[Dict] — find patterns
- apply(graph: ProgramGraph, match: Dict) -> Optional[SemanticMapping] — generate mapping
- name property — rule identifier
- mapping_kind property — the MappingKind produced

Register rules via engine.register_rule(). Fixpoint iteration applies all rules until convergence.

## Files
- rules.py — 19 TranslationRule subclasses (ReadOnlyInputRule, MutatingSubsystemRule, OrchestratorRule, TestAssertionRule, RetryPatternRule, EventBusRule, ConfigRule, FeatureFlagRule, ObservationRule, ActionRule, PolicyRule, PreferenceRule, ContextRule, InheritanceRule, ContainmentRule, DataPipelineRule, ErrorBoundaryRule, SingletonAccessRule, CircuitBreakerRule)
- engine.py — TranslationRule (ABC), TranslationEngine (register_rule, translate, fixpoint iteration)
- confidence.py — ConfidenceModel (compute_confidence_score, determine_confidence_tier, score_batch)
- review.py — ReviewManager (accept_mapping, reject_mapping, edit_mapping, split_mapping, merge_mappings)
- __init__.py — Public exports
