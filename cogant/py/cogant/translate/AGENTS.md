# Agents — py/cogant/translate

## Owner
Semantic Lead

## Responsibilities
- Apply 22 concrete TranslationRule subclasses to discover semantic mappings in program graphs
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
Add new `TranslationRule` subclass to the appropriate family module under `rules/` (e.g. `structural.py`, `semantic.py`). Each rule implements:
- `matches(graph: ProgramGraph, query: GraphQuery) -> list[dict]` — returns matching fragments
- `apply(...) -> Optional[SemanticMapping]` — produces the mapping with confidence/provenance
- `name`, `mapping_kind`, `priority`, `confidence_weight` properties

Register with `engine.register_rule(MyRule())` in `__init__.py` or family module. The fixpoint `TranslationEngine.translate()` applies rules iteratively until convergence.

## Files
- `rules/` — 22 `TranslationRule` implementations across 5 family modules (structural.py, semantic.py, behavioral.py, control.py, resilience.py)
- `engine.py` — `TranslationRule` (ABC), `TranslationEngine` (registration, fixpoint loop, conflict resolution)
- `confidence.py` — `ConfidenceModel` (score computation, tier determination, batch scoring)
- `review.py` — `ReviewManager` (curation operations)
- `__init__.py` — exports and rule registration
