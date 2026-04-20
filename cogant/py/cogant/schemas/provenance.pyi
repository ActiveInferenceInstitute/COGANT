from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from _typeshed import Incomplete

from .base import CogantBaseModel as CogantBaseModel
from .base import Span as Span

class EvidenceKind(StrEnum):
    SOURCE_SPAN = 'source_span'
    AST_FACT = 'ast_fact'
    TRACE_EVENT = 'trace_event'
    TEST_ASSERTION = 'test_assertion'
    CONFIG_ENTRY = 'config_entry'
    COMMIT_EVENT = 'commit_event'
    TYPE_SIGNATURE = 'type_signature'
    STATIC_ANALYSIS = 'static_analysis'
    DATAFLOW = 'dataflow'
    CONTROL_FLOW = 'control_flow'
    SEMANTIC_ANNOTATION = 'semantic_annotation'
    DOCUMENTATION = 'documentation'

class ProvenanceRecord(CogantBaseModel):
    evidence_id: str
    kind: EvidenceKind
    timestamp: datetime
    uri: str
    locator: str | None
    span: Span | None
    excerpt: str | None
    excerpt_hash: str | None
    context: dict[str, Any]
    confidence: float
    generated_by: str | None
    generator_version: str | None
    related_evidence_ids: list[str]
    element_id: str | None
    ast_node_type: str | None
    ast_properties: dict[str, Any]
    event_name: str | None
    event_data: dict[str, Any]
    event_timestamp: datetime | None
    test_name: str | None
    assertion_type: str | None
    assertion_passed: bool | None
    config_key: str | None
    config_value: str | None
    commit_hash: str | None
    commit_author: str | None
    commit_message: str | None
    tags: list[str]
    notes: str | None
    model_config: ClassVar[Incomplete]

class ProvenanceStore(CogantBaseModel):
    store_id: str
    records: list[ProvenanceRecord]
    evidence_index: dict[str, int]
    uri_index: dict[str, list[int]]
    kind_index: dict[str, list[int]]
    statistics: dict[str, Any]
    created_at: datetime
    def add_record(self, record: ProvenanceRecord) -> None: ...
    def get_record(self, evidence_id: str) -> ProvenanceRecord | None: ...
    def get_by_uri(self, uri: str) -> list[ProvenanceRecord]: ...
    def get_by_kind(self, kind: EvidenceKind) -> list[ProvenanceRecord]: ...
