"""
ProvenanceRecord: Evidence and traceability for analysis results.

Stores provenance information linking analysis artifacts back to their
source code, configurations, tests, and execution traces.
"""

from typing import Optional, Dict, Any, List, Literal
from enum import Enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict

from .base import CogantBaseModel, StableID, Span, EvidenceRef


class EvidenceKind(str, Enum):
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
    kind: EvidenceKind = Field(
        ..., description="Type of evidence"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When evidence was collected",
    )

    # Location information
    uri: str = Field(
        ...,
        description="URI of evidence source (file path, URL, database location, etc.)",
    )
    locator: Optional[str] = Field(
        default=None,
        description="Precise locator within source (line:col, query, offset, etc.)",
    )
    span: Optional[Span] = Field(
        default=None,
        description="Source code span if applicable",
    )

    # Evidence content
    excerpt: Optional[str] = Field(
        default=None,
        description="Short excerpt of evidence source (e.g., source line, test assertion)",
    )
    excerpt_hash: Optional[str] = Field(
        default=None,
        description="SHA256 hash of excerpt for integrity",
    )

    # Metadata
    context: Dict[str, Any] = Field(
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
    generated_by: Optional[str] = Field(
        default=None,
        description="Tool/analyzer that generated evidence (e.g., 'ast_visitor', 'type_checker')",
    )
    generator_version: Optional[str] = Field(
        default=None,
        description="Version of generator tool",
    )

    # Relationships
    related_evidence_ids: List[str] = Field(
        default_factory=list,
        description="IDs of related evidence items",
    )

    # Type-specific fields
    # For SOURCE_SPAN:
    element_id: Optional[str] = Field(
        default=None,
        description="ID of program graph element (for SOURCE_SPAN)",
    )

    # For AST_FACT:
    ast_node_type: Optional[str] = Field(
        default=None,
        description="Type of AST node (for AST_FACT)",
    )
    ast_properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Properties extracted from AST node",
    )

    # For TRACE_EVENT:
    event_name: Optional[str] = Field(
        default=None,
        description="Name of trace event",
    )
    event_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload/data",
    )
    event_timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp of trace event execution",
    )

    # For TEST_ASSERTION:
    test_name: Optional[str] = Field(
        default=None,
        description="Name of test containing assertion",
    )
    assertion_type: Optional[str] = Field(
        default=None,
        description="Type of assertion (e.g., 'equals', 'contains', 'raises')",
    )
    assertion_passed: Optional[bool] = Field(
        default=None,
        description="Whether test assertion passed",
    )

    # For CONFIG_ENTRY:
    config_key: Optional[str] = Field(
        default=None,
        description="Configuration key",
    )
    config_value: Optional[str] = Field(
        default=None,
        description="Configuration value",
    )

    # For COMMIT_EVENT:
    commit_hash: Optional[str] = Field(
        default=None,
        description="Git commit hash",
    )
    commit_author: Optional[str] = Field(
        default=None,
        description="Commit author",
    )
    commit_message: Optional[str] = Field(
        default=None,
        description="Commit message",
    )

    # Metadata
    tags: List[str] = Field(
        default_factory=list,
        description="User-defined tags",
    )
    notes: Optional[str] = Field(
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
    records: List[ProvenanceRecord] = Field(
        default_factory=list,
        description="All provenance records",
    )

    # Indices
    evidence_index: Dict[str, int] = Field(
        default_factory=dict,
        description="Map evidence_id to record index",
    )
    uri_index: Dict[str, List[int]] = Field(
        default_factory=dict,
        description="Map URI to record indices",
    )
    kind_index: Dict[str, List[int]] = Field(
        default_factory=dict,
        description="Map kind to record indices",
    )

    # Statistics
    statistics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Store statistics (record counts, coverage, etc.)",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
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

    def get_record(self, evidence_id: str) -> Optional[ProvenanceRecord]:
        """Retrieve record by evidence ID."""
        if evidence_id in self.evidence_index:
            return self.records[self.evidence_index[evidence_id]]
        return None

    def get_by_uri(self, uri: str) -> List[ProvenanceRecord]:
        """Get all records for a URI."""
        if uri in self.uri_index:
            return [self.records[idx] for idx in self.uri_index[uri]]
        return []

    def get_by_kind(self, kind: EvidenceKind) -> List[ProvenanceRecord]:
        """Get all records of a specific kind."""
        kind_str = kind.value
        if kind_str in self.kind_index:
            return [self.records[idx] for idx in self.kind_index[kind_str]]
        return []
