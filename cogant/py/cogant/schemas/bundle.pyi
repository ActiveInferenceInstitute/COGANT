from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from _typeshed import Incomplete as Incomplete

from .base import CogantBaseModel as CogantBaseModel
from .base import EvidenceRef as EvidenceRef
from .base import SemanticVersion as SemanticVersion

class TargetLanguage(StrEnum):
    PYTHON = 'python'
    JAVASCRIPT = 'javascript'
    TYPESCRIPT = 'typescript'
    JAVA = 'java'
    CPP = 'cpp'
    CSHARP = 'csharp'
    GO = 'go'
    RUST = 'rust'
    RUBY = 'ruby'
    PHP = 'php'

class TargetInfo(CogantBaseModel):
    name: str
    version: str
    primary_language: TargetLanguage
    supported_languages: list[TargetLanguage]
    repository_url: str | None
    commit_hash: str | None
    analysis_scope: str | None

class ProvenanceOrigin(CogantBaseModel):
    analyzer_name: str
    analyzer_version: str
    ingest_timestamp: datetime
    ingest_host: str | None
    ingest_user: str | None
    command_line: str | None
    parameters: dict[str, Any]

class ArtifactPaths(CogantBaseModel):
    program_graph_path: str
    semantic_mappings_path: str
    state_space_models_path: str
    process_models_path: str
    provenance_store_path: str
    validation_report_path: str
    gnn_export_path: str
    metadata_path: str

class CoreBundleSchema(CogantBaseModel):
    bundle_id: str
    schema_version: str
    cogant_version: SemanticVersion
    created_at: datetime
    updated_at: datetime | None
    title: str | None
    description: str | None
    target: TargetInfo
    provenance: ProvenanceOrigin
    artifacts: ArtifactPaths
    tags: list[str]
    annotations: dict[str, Any]
    evidence_references: list[EvidenceRef]
    model_config: ClassVar[Incomplete]
