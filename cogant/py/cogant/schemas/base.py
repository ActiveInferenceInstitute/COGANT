"""
Base types and configuration for all COGANT Pydantic models.

Defines shared types, validation utilities, and BaseModel configuration
used across all schema modules.
"""

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CogantBaseModel(BaseModel):
    """
    Base model for all COGANT schemas with Pydantic v2 configuration.
    Enforces strict schema validation and JSON serialization.
    """

    model_config = ConfigDict(
        use_enum_values=False,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        json_schema_extra={"version": "1.0"},
    )


class StableID(str):
    """
    A deterministic, stable identifier for reproducible hashing across runs.
    Derived from semantic content rather than ephemeral UUIDs.
    """

    pass


class SemanticVersion(str):
    """Semantic version string (e.g., '1.2.3').

    Validates format on construction: must be exactly ``major.minor.patch``
    where each component is a non-negative integer.
    """

    def __new__(cls, value: str) -> "SemanticVersion":
        """Create a validated SemanticVersion string."""
        if isinstance(value, str):
            parts = value.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                raise ValueError(
                    f"Invalid semantic version: {value}. Expected format: major.minor.patch"
                )
        return super().__new__(cls, value)


class Span(CogantBaseModel):
    """
    Source code span with line and column information.
    Inclusive of start, exclusive of end (following LSP conventions).
    """

    start_line: int = Field(..., description="1-indexed start line")
    start_col: int = Field(..., description="0-indexed start column")
    end_line: int = Field(..., description="1-indexed end line (inclusive)")
    end_col: int = Field(..., description="0-indexed end column (exclusive)")

    @field_validator("start_line", "end_line", "start_col", "end_col")
    @classmethod
    def validate_span_bounds(cls, v: int) -> int:
        """Ensure span values are non-negative."""
        if v < 0:
            raise ValueError("Span values must be non-negative")
        return v

    @field_validator("end_line", mode="after")
    @classmethod
    def validate_end_after_start(cls, v: int, info) -> int:
        """Ensure end_line >= start_line."""
        if "start_line" in info.data and v < info.data["start_line"]:
            raise ValueError("end_line must be >= start_line")
        return v


class EvidenceRef(CogantBaseModel):
    """
    Reference to provenance evidence connecting a schema element
    back to its source (code, config, test, trace).
    """

    evidence_id: str = Field(
        ..., description="Unique identifier of evidence in provenance store"
    )
    kind: Literal[
        "source_span",
        "ast_fact",
        "trace_event",
        "test_assertion",
        "config_entry",
        "commit_event",
    ] = Field(..., description="Type of evidence")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this evidence [0, 1]",
    )
    locator: str | None = Field(
        default=None, description="Additional locator within evidence (e.g., line number)"
    )


class TypeInfo(CogantBaseModel):
    """
    Structured type information for symbols, fields, and expressions.
    Supports scalar, composite, and generic types.
    """

    base_type: str = Field(..., description="Base type name (e.g., 'str', 'int', 'List')")
    is_optional: bool = Field(
        default=False, description="Whether type is Optional/Nullable"
    )
    is_generic: bool = Field(default=False, description="Whether type is parameterized")
    type_parameters: list[str] = Field(
        default_factory=list,
        description="Type parameters for generics (e.g., ['int', 'str'] for Dict[int, str])",
    )
    is_collection: bool = Field(
        default=False, description="Whether type is a collection (List, Set, Dict)"
    )
    collection_element_type: str | None = Field(
        default=None, description="Type of collection elements if is_collection=True"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Language-specific type metadata (e.g., array dimensions)",
    )


class ConfidenceMetric(CogantBaseModel):
    """
    Structured confidence score with rationale and evidence types.
    Enables transparent uncertainty tracking throughout the schema.
    """

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score in range [0, 1]",
    )
    rationale: str | None = Field(
        default=None, description="Human-readable explanation of score"
    )
    evidence_types: list[str] = Field(
        default_factory=list,
        description="Types of evidence contributing to this score (e.g., 'static_analysis', 'test_coverage')",
    )


class LocationInfo(CogantBaseModel):
    """
    Location information for files and code elements.
    Supports absolute and relative paths, plus source control references.
    """

    path: str = Field(..., description="Absolute or relative file path")
    span: Span | None = Field(
        default=None, description="Source span if element is a code region"
    )
    language: str | None = Field(
        default=None, description="Programming language (e.g., 'python', 'javascript')"
    )
    repo_root: str | None = Field(
        default=None, description="Repository root path for context"
    )


def generate_stable_id(content: str, prefix: str = "") -> StableID:
    """
    Generate a deterministic stable ID from content using SHA256.

    Args:
        content: The semantic content to hash (e.g., "module:src/main.py")
        prefix: Optional prefix for the ID (e.g., "node_")

    Returns:
        StableID derived from hash of content
    """
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
    if prefix:
        return StableID(f"{prefix}{h}")
    return StableID(h)
