"""
COGANT Schemas Package

Comprehensive schema definitions for all COGANT analysis artifacts,
including program graphs, semantic mappings, state space models, process models,
provenance tracking, validation reports, and GNN export bundles.

This module provides graceful fallback to basic implementations if Pydantic
extended schemas are not available.
"""

# Try to import from extended Pydantic schemas first
_extended_available = False
try:
    from .base import (
        CogantBaseModel,
        StableID,
        SemanticVersion,
        Span,
        EvidenceRef,
        TypeInfo,
        ConfidenceMetric,
        LocationInfo,
        generate_stable_id,
    )
    from .bundle import (
        CoreBundleSchema,
        TargetInfo,
        TargetLanguage,
        ProvenanceOrigin,
        ArtifactPaths,
    )
    from .program_graph import (
        ProgramGraph,
        Node,
        NodeKind,
        Edge,
        EdgeKind,
    )
    from .semantic_mapping import (
        SemanticMapping,
        SemanticMappingCollection,
        SemanticRole,
        MappingRule,
        SourceGraphElement,
        TargetSemanticElement,
        ReviewStatus,
    )
    from .state_space import (
        StateSpaceModel,
        StateSpaceKind,
        StateVariable,
        ObservationModality,
        Action,
        Transition,
        Likelihood,
    )
    from .process_model import (
        ProcessModel,
        ProcessKind,
        ProcessStage,
        ProcessPolicy,
        ProcessTimeline,
        TriggerKind,
        SideEffect,
    )
    from .provenance import (
        ProvenanceRecord,
        ProvenanceStore,
        EvidenceKind,
    )
    from .validation import (
        ValidationReport,
        ValidationCheck,
        ValidationMetrics,
        ValidationRecommendation,
        CheckLevel,
        CheckStatus,
    )
    from .gnn_export import (
        GNNExportBundle,
        GNNMetadata,
        RepositoryMetadata,
        SourceCoverage,
        GraphSection,
        ObservationModalitySection,
        ActionPolicySection,
        ConnectionSection,
        FactorSection,
        TransitionStructureSection,
        LikelihoodStructureSection,
        PreferenceConstraintSection,
        TimeSettingSection,
        ParameterizationSection,
        OntologyMappingSection,
        ProvenanceSection,
        ConfidenceSection,
        RenderingHints,
        ValidationNotes,
    )
    _extended_available = True
except (ImportError, ModuleNotFoundError):
    # Fall back to basic implementations. The fallback types are
    # intentionally distinct from the extended ones; mypy sees two
    # incompatible "Node"/"Edge"/"ProgramGraph"/"SemanticMapping"/
    # "ProvenanceRecord" definitions at package-import time, so we
    # silence the assignment diagnostic here.
    from cogant.schemas.core import (  # type: ignore[assignment]
        Node,
        Edge,
        NodeKind,
        EdgeKind,
    )
    from cogant.schemas.graph import (  # type: ignore[assignment]
        ProgramGraph,
        GraphMetadata,
    )
    from cogant.schemas.semantic import (  # type: ignore[assignment]
        SemanticMapping,
        MappingKind,
        ConfidenceTier,
        ProvenanceRecord,
    )

if _extended_available:
    __all__ = [
        # Base
        "CogantBaseModel",
        "StableID",
        "SemanticVersion",
        "Span",
        "EvidenceRef",
        "TypeInfo",
        "ConfidenceMetric",
        "LocationInfo",
        "generate_stable_id",
        # Bundle
        "CoreBundleSchema",
        "TargetInfo",
        "TargetLanguage",
        "ProvenanceOrigin",
        "ArtifactPaths",
        # Program Graph
        "ProgramGraph",
        "Node",
        "NodeKind",
        "Edge",
        "EdgeKind",
        # Semantic Mapping
        "SemanticMapping",
        "SemanticMappingCollection",
        "SemanticRole",
        "MappingRule",
        "SourceGraphElement",
        "TargetSemanticElement",
        "ReviewStatus",
        # State Space
        "StateSpaceModel",
        "StateSpaceKind",
        "StateVariable",
        "ObservationModality",
        "Action",
        "Transition",
        "Likelihood",
        # Process Model
        "ProcessModel",
        "ProcessKind",
        "ProcessStage",
        "ProcessPolicy",
        "ProcessTimeline",
        "TriggerKind",
        "SideEffect",
        # Provenance
        "ProvenanceRecord",
        "ProvenanceStore",
        "EvidenceKind",
        # Validation
        "ValidationReport",
        "ValidationCheck",
        "ValidationMetrics",
        "ValidationRecommendation",
        "CheckLevel",
        "CheckStatus",
        # GNN Export
        "GNNExportBundle",
        "GNNMetadata",
        "RepositoryMetadata",
        "SourceCoverage",
        "GraphSection",
        "ObservationModalitySection",
        "ActionPolicySection",
        "ConnectionSection",
        "FactorSection",
        "TransitionStructureSection",
        "LikelihoodStructureSection",
        "PreferenceConstraintSection",
        "TimeSettingSection",
        "ParameterizationSection",
        "OntologyMappingSection",
        "ProvenanceSection",
        "ConfidenceSection",
        "RenderingHints",
        "ValidationNotes",
    ]
else:
    __all__ = [
        "Node",
        "Edge",
        "NodeKind",
        "EdgeKind",
        "ProgramGraph",
        "GraphMetadata",
        "SemanticMapping",
        "MappingKind",
        "ConfidenceTier",
        "ProvenanceRecord",
    ]
