"""
CoreBundleSchema: Top-level bundle container for COGANT analysis results.

Defines the structure for packaging all analysis artifacts, metadata,
and provenance into a single portable bundle.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict

from .base import CogantBaseModel, SemanticVersion, StableID, EvidenceRef, generate_stable_id


class TargetLanguage(str, Enum):
    """Programming languages supported as analysis targets."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"


class TargetInfo(CogantBaseModel):
    """
    Metadata about the target codebase being analyzed.
    """

    name: str = Field(..., description="Project/repository name")
    version: str = Field(..., description="Project version")
    primary_language: TargetLanguage = Field(..., description="Primary programming language")
    supported_languages: List[TargetLanguage] = Field(
        default_factory=list,
        description="All languages detected in codebase",
    )
    repository_url: Optional[str] = Field(
        default=None, description="URL of source repository (e.g., GitHub)"
    )
    commit_hash: Optional[str] = Field(
        default=None, description="Git commit hash of analyzed version"
    )
    analysis_scope: Optional[str] = Field(
        default=None,
        description="Scope of analysis (e.g., 'full', 'public_api', 'main_branch')",
    )


class ProvenanceOrigin(CogantBaseModel):
    """
    Provenance information about how the bundle was created.
    """

    analyzer_name: str = Field(..., description="Name of analysis tool/framework")
    analyzer_version: str = Field(..., description="Version of analyzer")
    ingest_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When analysis was performed",
    )
    ingest_host: Optional[str] = Field(
        default=None, description="Hostname of analysis environment"
    )
    ingest_user: Optional[str] = Field(
        default=None, description="User who initiated analysis"
    )
    command_line: Optional[str] = Field(
        default=None, description="Command used to invoke analyzer"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Analysis configuration parameters",
    )


class ArtifactPaths(CogantBaseModel):
    """
    Relative paths to artifact files within the bundle.
    Enables flexible bundle organization without hard-coded paths.
    """

    program_graph_path: str = Field(
        default="artifacts/program_graph.json",
        description="Path to serialized ProgramGraph",
    )
    semantic_mappings_path: str = Field(
        default="artifacts/semantic_mappings.json",
        description="Path to serialized SemanticMappings",
    )
    state_space_models_path: str = Field(
        default="artifacts/state_space_models.json",
        description="Path to serialized StateSpaceModels",
    )
    process_models_path: str = Field(
        default="artifacts/process_models.json",
        description="Path to serialized ProcessModels",
    )
    provenance_store_path: str = Field(
        default="artifacts/provenance.db",
        description="Path to provenance evidence store",
    )
    validation_report_path: str = Field(
        default="artifacts/validation_report.json",
        description="Path to validation report",
    )
    gnn_export_path: str = Field(
        default="artifacts/gnn_export.json",
        description="Path to GNN-format export",
    )
    metadata_path: str = Field(
        default="metadata.json",
        description="Path to this bundle metadata",
    )


class CoreBundleSchema(CogantBaseModel):
    """
    Top-level container for a complete COGANT analysis bundle.

    Packages all artifacts, metadata, provenance, and configuration
    needed to reproduce, validate, and utilize analysis results.
    """

    bundle_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this bundle",
    )
    schema_version: str = Field(
        default="2.0.0",
        description="Version of this schema specification",
    )
    cogant_version: SemanticVersion = Field(
        default=SemanticVersion("1.0.0"),
        description="Version of COGANT framework used",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO 8601 timestamp of bundle creation",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="ISO 8601 timestamp of last update",
    )
    title: Optional[str] = Field(
        default=None, description="Human-readable bundle title"
    )
    description: Optional[str] = Field(
        default=None, description="Detailed description of bundle contents"
    )

    # Core metadata
    target: TargetInfo = Field(..., description="Information about analyzed target")
    provenance: ProvenanceOrigin = Field(
        default_factory=ProvenanceOrigin,
        description="Provenance of bundle creation",
    )

    # Artifact locations
    artifacts: ArtifactPaths = Field(
        default_factory=ArtifactPaths,
        description="Paths to artifact files within bundle",
    )

    # Optional metadata
    tags: List[str] = Field(
        default_factory=list, description="User-defined tags for bundle categorization"
    )
    annotations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom annotations/metadata",
    )

    # Evidence references for bundle-level provenance
    evidence_references: List[EvidenceRef] = Field(
        default_factory=list,
        description="Evidence supporting bundle metadata",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bundle_id": "550e8400-e29b-41d4-a716-446655440000",
                "schema_version": "2.0.0",
                "cogant_version": "1.0.0",
                "created_at": "2024-01-15T10:30:00Z",
                "title": "FastAPI Microservice Analysis",
                "target": {
                    "name": "fastapi-auth-service",
                    "version": "2.1.0",
                    "primary_language": "python",
                    "repository_url": "https://github.com/example/fastapi-auth",
                    "commit_hash": "abc1234def5678",
                },
                "provenance": {
                    "analyzer_name": "cogant-cli",
                    "analyzer_version": "1.0.0",
                    "ingest_timestamp": "2024-01-15T10:30:00Z",
                },
            }
        }
    )
