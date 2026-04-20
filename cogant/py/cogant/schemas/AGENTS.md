# Agents — py/cogant/schemas

## Owner
Semantic Lead

## Responsibilities
- Define ~70 Pydantic/dataclass models for entire COGANT pipeline
- Ensure type safety and validation across all subpackages
- Maintain backward compatibility and semantic versioning
- Stabilize public API via __init__.py exports

## Coordination
- All downstream modules depend on schemas; breaking changes require Architecture Lead approval
- ProgramGraph is the canonical intermediate representation (source of truth for code structure)
- SemanticMapping represents discovered concepts; drives all downstream export/execution
- StateSpaceModel, ProcessModel, and GNNExportBundle are derived views for specific use cases
- Each class encodes provenance and confidence metadata

## How to extend
Add new types to appropriate module files (state_space.py for state concepts, semantic.py for semantic types, etc.). Update __init__.py to export. Use CogantBaseModel for Pydantic models, @dataclass for lightweight records.

## Files
- base.py — CogantBaseModel (Pydantic v2 base), StableID, SemanticVersion, Span, EvidenceRef, TypeInfo, ConfidenceMetric, LocationInfo
- core.py — NodeKind, EdgeKind enums (MODULE, CLASS, FUNCTION, etc.; CALLS, READS, WRITES, etc.)
- graph.py — GraphMetadata, ProgramGraph (core graph container)
- program_graph.py — Node, Edge, ProgramGraph (legacy/extended graph schema with attributes)
- bundle.py — TargetLanguage, TargetInfo, ProvenanceOrigin, ArtifactPaths, CoreBundleSchema
- semantic.py — MappingKind, ConfidenceTier enums; ProvenanceRecord, SemanticMapping (dataclasses)
- semantic_mapping.py — SemanticRole, MappingRule, SourceGraphElement, TargetSemanticElement, ReviewStatus, SemanticMapping, SemanticMappingCollection (Pydantic models)
- state_space.py — StateSpaceKind, StateVariable, ObservationModality, Action, Transition, Likelihood, StateSpaceModel
- process_model.py — ProcessKind, TriggerKind, SideEffect, ProcessStage, ProcessPolicy, ProcessTimeline, ProcessModel
- provenance.py — EvidenceKind enum; ProvenanceRecord, ProvenanceStore (Pydantic models)
- gnn_export.py — 19 canonical sections (13 Section classes + RenderingHints + ValidationNotes + GNNMetadata + RepositoryMetadata + SourceCoverage + GNNExportBundle): GNNMetadata, RepositoryMetadata, SourceCoverage, GraphSection, ObservationModalitySection, ActionPolicySection, ConnectionSection, FactorSection, TransitionStructureSection, LikelihoodStructureSection, PreferenceConstraintSection, TimeSettingSection, ParameterizationSection, OntologyMappingSection, ProvenanceSection, ConfidenceSection, RenderingHints, ValidationNotes, GNNExportBundle
- validation.py — CheckLevel, CheckStatus, ValidationCheck, ValidationMetrics, ValidationRecommendation, ValidationReport
- __init__.py — Public type aliases and exports
