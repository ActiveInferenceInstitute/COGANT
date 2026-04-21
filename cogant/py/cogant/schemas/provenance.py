"""
ProvenanceRecord: Evidence and traceability for analysis results.

Stores provenance information linking analysis artifacts back to their
source code, configurations, tests, and execution traces.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import ConfigDict, Field

from .base import CogantBaseModel, Span


class EvidenceKind(StrEnum):
    """Types of evidence supporting analysis results."""

    SOURCE_SPAN = "source_span"  # Code location (file, line, col)
    AST_FACT = "ast_fact"  # Abstract syntax tree fact
    TRACE_EVENT = "trace_event"  # Runtime trace event
    TEST_ASSERTION = "test_assertion"  # Test case assertion
    CONFIG_ENTRY = "config_entry"  # Configuration file entry
    COMMIT_EVENT = "commit_event"  # Git commit information
    TYPE_SIGNATURE = "type_signature"  # Type hint/signature
    STATIC_ANALYSIS = "static_analysis"  # Static analysis result
    DATAFLOW = "dataflow"  # Data flow analysis fact
    CONTROL_FLOW = "control_flow"  # Control flow fact
    SEMANTIC_ANNOTATION = "semantic_annotation"  # Semantic annotation
    DOCUMENTATION = "documentation"  # Documentation evidence


class ProvenanceRecord(CogantBaseModel):
    """
    A single piece of evidence supporting an analysis result.

    Enables traceability from schema elements back to their source evidence,
    supporting reproducibility and auditing.
    """

    evidence_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this evidence",
    )
    kind: EvidenceKind = Field(..., description="Type of evidence")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When evidence was collected",
    )

    # Location information
    uri: str = Field(
        ...,
        description="URI of evidence source (file path, URL, database location, etc.)",
    )
    locator: str | None = Field(
        default=None,
        description="Precise locator within source (line:col, query, offset, etc.)",
    )
    span: Span | None = Field(
        default=None,
        description="Source code span if applicable",
    )

    # Evidence content
    excerpt: str | None = Field(
        default=None,
        description="Short excerpt of evidence source (e.g., source line, test assertion)",
    )
    excerpt_hash: str | None = Field(
        default=None,
        description="SHA256 hash of excerpt for integrity",
    )

    # Metadata
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (e.g., AST node type, test name, config section)",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in evidence reliability [0, 1]",
    )

    # Generation info
    generated_by: str | None = Field(
        default=None,
        description="Tool/analyzer that generated evidence (e.g., 'ast_visitor', 'type_checker')",
    )
    generator_version: str | None = Field(
        default=None,
        description="Version of generator tool",
    )

    # Relationships
    related_evidence_ids: list[str] = Field(
        default_factory=list,
        description="IDs of related evidence items",
    )

    # Type-specific fields
    # For SOURCE_SPAN:
    element_id: str | None = Field(
        default=None,
        description="ID of program graph element (for SOURCE_SPAN)",
    )

    # For AST_FACT:
    ast_node_type: str | None = Field(
        default=None,
        description="Type of AST node (for AST_FACT)",
    )
    ast_properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Properties extracted from AST node",
    )

    # For TRACE_EVENT:
    event_name: str | None = Field(
        default=None,
        description="Name of trace event",
    )
    event_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload/data",
    )
    event_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp of trace event execution",
    )

    # For TEST_ASSERTION:
    test_name: str | None = Field(
        default=None,
        description="Name of test containing assertion",
    )
    assertion_type: str | None = Field(
        default=None,
        description="Type of assertion (e.g., 'equals', 'contains', 'raises')",
    )
    assertion_passed: bool | None = Field(
        default=None,
        description="Whether test assertion passed",
    )

    # For CONFIG_ENTRY:
    config_key: str | None = Field(
        default=None,
        description="Configuration key",
    )
    config_value: str | None = Field(
        default=None,
        description="Configuration value",
    )

    # For COMMIT_EVENT:
    commit_hash: str | None = Field(
        default=None,
        description="Git commit hash",
    )
    commit_author: str | None = Field(
        default=None,
        description="Commit author",
    )
    commit_message: str | None = Field(
        default=None,
        description="Commit message",
    )

    # Metadata
    tags: list[str] = Field(
        default_factory=list,
        description="User-defined tags",
    )
    notes: str | None = Field(
        default=None,
        description="Human notes about this evidence",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "evidence_id": "ev_abc123def456",
                "kind": "source_span",
                "uri": "src/auth.py",
                "locator": "42:8-42:35",
                "span": {
                    "start_line": 42,
                    "start_col": 8,
                    "end_line": 42,
                    "end_col": 35,
                },
                "excerpt": "def authenticate(token: str) -> bool:",
                "element_id": "func_authenticate",
                "generated_by": "ast_visitor",
                "confidence": 1.0,
            }
        }
    )


class ProvenanceStore(CogantBaseModel):
    """
    Collection of all provenance evidence for a bundle.
    """

    store_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for store",
    )
    records: list[ProvenanceRecord] = Field(
        default_factory=list,
        description="All provenance records",
    )

    # Indices
    evidence_index: dict[str, int] = Field(
        default_factory=dict,
        description="Map evidence_id to record index",
    )
    uri_index: dict[str, list[int]] = Field(
        default_factory=dict,
        description="Map URI to record indices",
    )
    kind_index: dict[str, list[int]] = Field(
        default_factory=dict,
        description="Map kind to record indices",
    )

    # Statistics
    statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="Store statistics (record counts, coverage, etc.)",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When store was created",
    )

    def add_record(self, record: ProvenanceRecord) -> None:
        """Add a record to the store and update indices."""
        idx = len(self.records)
        self.records.append(record)
        self.evidence_index[record.evidence_id] = idx

        # Update URI index
        if record.uri not in self.uri_index:
            self.uri_index[record.uri] = []
        self.uri_index[record.uri].append(idx)

        # Update kind index
        kind_str = record.kind.value
        if kind_str not in self.kind_index:
            self.kind_index[kind_str] = []
        self.kind_index[kind_str].append(idx)

    def get_record(self, evidence_id: str) -> ProvenanceRecord | None:
        """Retrieve record by evidence ID."""
        if evidence_id in self.evidence_index:
            return self.records[self.evidence_index[evidence_id]]
        return None

    def get_by_uri(self, uri: str) -> list[ProvenanceRecord]:
        """Get all records for a URI."""
        if uri in self.uri_index:
            return [self.records[idx] for idx in self.uri_index[uri]]
        return []

    def get_by_kind(self, kind: EvidenceKind) -> list[ProvenanceRecord]:
        """Get all records of a specific kind."""
        kind_str = kind.value
        if kind_str in self.kind_index:
            return [self.records[idx] for idx in self.kind_index[kind_str]]
        return []
