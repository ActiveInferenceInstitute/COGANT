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
        ConfidenceMetric,
        EvidenceRef,
        LocationInfo,
        SemanticVersion,
        Span,
        StableID,
        TypeInfo,
        generate_stable_id,
    )
    from .bundle import (
        ArtifactPaths,
        CoreBundleSchema,
        ProvenanceOrigin,
        TargetInfo,
        TargetLanguage,
    )
    from .gnn_export import (
        ActionPolicySection,
        ConfidenceSection,
        ConnectionSection,
        FactorSection,
        GNNExportBundle,
        GNNMetadata,
        GraphSection,
        LikelihoodStructureSection,
        ObservationModalitySection,
        OntologyMappingSection,
        ParameterizationSection,
        PreferenceConstraintSection,
        ProvenanceSection,
        RenderingHints,
        RepositoryMetadata,
        SourceCoverage,
        TimeSettingSection,
        TransitionStructureSection,
        ValidationNotes,
    )
    from .process_model import (
        ProcessKind,
        ProcessModel,
        ProcessPolicy,
        ProcessStage,
        ProcessTimeline,
        SideEffect,
        TriggerKind,
    )
    from .program_graph import (
        Edge,
        EdgeKind,
        Node,
        NodeKind,
        ProgramGraph,
    )
    from .provenance import (
        EvidenceKind,
        ProvenanceRecord,
        ProvenanceStore,
    )
    from .semantic import MappingKind  # noqa: F401 — re-exported for backwards compat
    from .semantic_mapping import (
        MappingRule,
        ReviewStatus,
        SemanticMapping,
        SemanticMappingCollection,
        SemanticRole,
        SourceGraphElement,
        TargetSemanticElement,
    )
    from .state_space import (
        Action,
        Likelihood,
        ObservationModality,
        StateSpaceKind,
        StateSpaceModel,
        StateVariable,
        Transition,
    )
    from .validation import (
        CheckLevel,
        CheckStatus,
        ValidationCheck,
        ValidationMetrics,
        ValidationRecommendation,
        ValidationReport,
    )
    _extended_available = True
except (ImportError, ModuleNotFoundError):
    # Fall back to basic implementations. The fallback types are
    # intentionally distinct from the extended ones; mypy sees two
    # incompatible "Node"/"Edge"/"ProgramGraph"/"SemanticMapping"/
    # "ProvenanceRecord" definitions at package-import time, so we
    # silence the assignment diagnostic here.
    from cogant.schemas.core import (  # type: ignore[assignment]
        Edge,
        EdgeKind,
        Node,
        NodeKind,
    )
    from cogant.schemas.graph import (  # type: ignore[assignment]
        GraphMetadata,
        ProgramGraph,
    )
    from cogant.schemas.semantic import (  # type: ignore[assignment]
        ConfidenceTier,
        MappingKind,
        ProvenanceRecord,
        SemanticMapping,
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
        "MappingKind",
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
