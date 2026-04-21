"""Pydantic request/response models for the COGANT server.

These models define the public contract of the production REST server
(:mod:`cogant.server.app`). They are written in Pydantic v2 so FastAPI
can consume them directly for request validation and OpenAPI schema
generation. The stdlib fallback server uses the same classes to
validate request bodies and to coerce responses into JSON, so the
contract is identical across both backends.

Every response model includes a :func:`model_dump` friendly shape so
callers that want the raw dict can use ``response.model_dump()`` or
``response.model_dump_json()``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# /analyze
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    """Request body for ``POST /analyze``.

    Attributes:
        repo_path: Absolute or relative path to the repository to
            analyze. The path must exist on the server filesystem.
        stages: Optional explicit list of pipeline stages to run. When
            ``None``, the default pipeline is used (ingest → static →
            normalize → graph → translate → statespace → process →
            export → validate; ``dynamic`` is governed by
            ``skip_dynamic``).
        skip_dynamic: When ``True``, the dynamic-analysis enrichment
            stage is skipped. Most analyses should keep this ``True``
            because dynamic enrichment requires coverage / trace files
            that are rarely available in a server context.
    """

    model_config = ConfigDict(extra="forbid")

    repo_path: str = Field(..., min_length=1, description="Path to repository to analyze")
    stages: list[str] | None = Field(
        default=None,
        description="Explicit pipeline stages (None = default stage list)",
    )
    skip_dynamic: bool = Field(
        default=True,
        description="Skip the dynamic-analysis enrichment stage",
    )


class AnalyzeResponse(BaseModel):
    """Response body for ``POST /analyze``.

    Attributes:
        nodes: Total number of nodes in the program graph.
        edges: Total number of edges in the program graph.
        mappings: Total number of semantic mappings emitted by the
            translate stage.
        roles: Role distribution ``{role_name: count}`` derived from
            the semantic mappings (``observation``, ``action``,
            ``hidden_state``, …).
        errors: Non-fatal pipeline errors collected during the run.
            An empty list indicates a clean pipeline execution.
    """

    nodes: int = Field(..., ge=0)
    edges: int = Field(..., ge=0)
    mappings: int = Field(..., ge=0)
    roles: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Liveness probe response for ``GET /health``.

    Attributes:
        status: Always ``"ok"`` when the server is running.
        version: The installed COGANT package version.
        docs: Path to the interactive API documentation. Populated with
            ``"/docs"`` when the FastAPI backend is running, or with a
            short string describing the stdlib fallback when it is not.
    """

    status: str = "ok"
    version: str
    docs: str = "/docs"


# ---------------------------------------------------------------------------
# /explain
# ---------------------------------------------------------------------------


class ExplainResponse(BaseModel):
    """Response body for ``GET /explain/{node_name}``.

    The server wraps :class:`cogant.cli.explain.ExplainResult` by
    serialising it through :func:`ExplainResult.to_dict`. Because the
    dict contains rule-explanation records with variable shape, the
    response model permits extra keys.
    """

    model_config = ConfigDict(extra="allow")

    node_name: str
    node_id: str
    node_kind: str
    assigned_role: str | None = None
    rules_fired: list[dict[str, Any]] = Field(default_factory=list)
    rules_considered: list[dict[str, Any]] = Field(default_factory=list)
    blanket_role: str
    target: str = ""
    mapping_label: str | None = None
    mapping_description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# /roundtrip
# ---------------------------------------------------------------------------


class RoundtripRequest(BaseModel):
    """Request body for ``POST /roundtrip``.

    Attributes:
        repo_path: Repository to round-trip (forward → reverse → forward).
        threshold: Minimum ``role_match_score`` for the result to be
            flagged as isomorphic. The COGANT default is ``0.5``; the
            server spec pins the default to ``0.7`` so the endpoint
            returns a stricter signal by default.
    """

    model_config = ConfigDict(extra="forbid")

    repo_path: str = Field(..., min_length=1)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class RoundtripResponse(BaseModel):
    """Response body for ``POST /roundtrip``.

    Mirrors the headline fields of
    :class:`cogant.reverse.idempotency.RoundtripResult` that the spec
    calls out. Additional fields from the underlying result are not
    exposed here to keep the contract stable.
    """

    role_match_score: float = Field(..., ge=0.0, le=1.0)
    is_isomorphic: bool
    original_roles: dict[str, int] = Field(default_factory=dict)
    synthesized_roles: dict[str, int] = Field(default_factory=dict)
    threshold: float = Field(..., ge=0.0, le=1.0)
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# /graph
# ---------------------------------------------------------------------------


class GraphNode(BaseModel):
    """Flat node description returned by ``GET /graph``."""

    id: str
    name: str
    kind: str
    role: str | None = None


class GraphEdge(BaseModel):
    """Flat edge description returned by ``GET /graph``."""

    id: str
    source: str
    target: str
    kind: str


class GraphResponse(BaseModel):
    """Response body for ``GET /graph``.

    Attributes:
        nodes: Flat list of graph nodes with their assigned AI role
            (if any).
        edges: Flat list of graph edges.
    """

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Uniform error payload.

    Attributes:
        detail: Human-readable error description.
        error_type: Concrete exception class name (e.g.
            ``FileNotFoundError``).
    """

    model_config = ConfigDict(extra="forbid")

    detail: str = Field(..., description="Human-readable error message")
    error_type: str = Field(..., description="Exception class name")


# ---------------------------------------------------------------------------
# /api/v1/translate
# ---------------------------------------------------------------------------


class TranslateOptions(BaseModel):
    """Options for code translation.

    Attributes:
        include_viz: Include visualization in response.
        viz_format: Output format for visualization
            (``"mermaid"``, ``"json"``, or ``"graphml"``).
        markov_seed: Strategy for Markov blanket partition
            (``"auto"``, ``"module"``, ``"class"``, ``"subgraph"``,
            or ``"manual"``).
        incremental: Enable incremental mode (use cached results when
            possible).
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    include_viz: bool = Field(default=False, description="Include visualization in response")
    viz_format: Literal["mermaid", "json", "graphml"] = Field(
        default="json", description="Visualization format"
    )
    markov_seed: Literal["auto", "module", "class", "subgraph", "manual"] = Field(
        default="auto", description="Markov blanket partition strategy"
    )
    incremental: bool = Field(default=False, description="Enable incremental mode (use cache)")


class TranslateRequest(BaseModel):
    """Request body for ``POST /api/v1/translate``.

    Attributes:
        source_code: Source code as a raw string.
        language: Programming language
            (``"python"``, ``"javascript"``, or ``"typescript"``).
        options: Translation options.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    source_code: str = Field(..., min_length=1, description="Source code to translate")
    language: Literal["python", "javascript", "typescript"] = Field(
        ..., description="Programming language"
    )
    options: TranslateOptions = Field(
        default_factory=TranslateOptions, description="Translation options"
    )


class TranslateResponse(BaseModel):
    """Response body for ``POST /api/v1/translate``.

    Attributes:
        request_id: Unique identifier for this request (UUID4).
        gnn_bundle: GNN markdown as a string.
        semantic_mappings: Semantic role assignments by node ID.
        validator_score: AII validator score (0-100).
        viz: Optional visualization (format depends on request).
        timing: Breakdown of per-stage timing in milliseconds.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    request_id: str = Field(..., description="Unique request identifier (UUID4)")
    gnn_bundle: str = Field(..., description="GNN markdown representation")
    semantic_mappings: dict[str, Any] = Field(
        default_factory=dict, description="Semantic role assignments by node"
    )
    validator_score: int = Field(..., ge=0, le=100, description="AII validator score (0-100)")
    viz: str | None = Field(default=None, description="Optional visualization")
    timing: dict[str, float] = Field(
        default_factory=dict, description="Per-stage timing in milliseconds"
    )


# ---------------------------------------------------------------------------
# /api/v1/analyze
# ---------------------------------------------------------------------------


class AnalysisRequest(BaseModel):
    """Request body for ``POST /api/v1/analyze``.

    Attributes:
        repo_path: Path to repository.
        stages: Optional explicit pipeline stages.
        skip_dynamic: Skip dynamic analysis.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    repo_path: str = Field(..., min_length=1, description="Path to repository")
    stages: list[str] | None = Field(
        default=None, description="Explicit pipeline stages (None = default)"
    )
    skip_dynamic: bool = Field(default=True, description="Skip dynamic analysis enrichment")


class AnalysisResponse(BaseModel):
    """Response body for ``POST /api/v1/analyze``.

    Attributes:
        request_id: Unique identifier for this request.
        nodes: Total nodes in program graph.
        edges: Total edges in program graph.
        mappings: Total semantic mappings.
        roles: Role distribution histogram.
        errors: Non-fatal pipeline errors.
        timing: Per-stage timing breakdown.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    request_id: str = Field(..., description="Unique request identifier (UUID4)")
    nodes: int = Field(..., ge=0, description="Node count")
    edges: int = Field(..., ge=0, description="Edge count")
    mappings: int = Field(..., ge=0, description="Semantic mapping count")
    roles: dict[str, int] = Field(default_factory=dict, description="Role distribution")
    errors: list[str] = Field(default_factory=list, description="Pipeline errors")
    timing: dict[str, float] = Field(
        default_factory=dict, description="Per-stage timing in milliseconds"
    )


# ---------------------------------------------------------------------------
# /api/v1/roundtrip
# ---------------------------------------------------------------------------


class RoundtripRequestV1(BaseModel):
    """Request body for ``POST /api/v1/roundtrip``.

    Attributes:
        repo_path: Repository to round-trip.
        threshold: Minimum role match score for isomorphic flag.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    repo_path: str = Field(..., min_length=1, description="Path to repository")
    threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum role match score for isomorphic",
    )


class RoundtripResponseV1(BaseModel):
    """Response body for ``POST /api/v1/roundtrip``.

    Attributes:
        request_id: Unique identifier for this request.
        role_match_score: Forward-reverse role match score (0-1).
        is_isomorphic: Whether score >= threshold.
        original_roles: Role histogram from forward pass.
        synthesized_roles: Role histogram from reverse pass.
        threshold: Threshold used for isomorphic judgment.
        errors: Any errors during round-trip.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    request_id: str = Field(..., description="Unique request identifier (UUID4)")
    role_match_score: float = Field(
        ..., ge=0.0, le=1.0, description="Forward-reverse role match score"
    )
    is_isomorphic: bool = Field(..., description="Whether role_match_score >= threshold")
    original_roles: dict[str, int] = Field(
        default_factory=dict, description="Forward pass role histogram"
    )
    synthesized_roles: dict[str, int] = Field(
        default_factory=dict, description="Reverse pass role histogram"
    )
    threshold: float = Field(..., ge=0.0, le=1.0, description="Isomorphic threshold")
    errors: list[str] = Field(default_factory=list, description="Round-trip errors")
    timing: dict[str, float] = Field(
        default_factory=dict, description="Per-stage timing in milliseconds"
    )


# ---------------------------------------------------------------------------
# /api/v1/rules
# ---------------------------------------------------------------------------


class RuleMetadata(BaseModel):
    """Metadata for a single translation rule.

    Attributes:
        name: Rule name.
        family: Rule family (e.g., ``"structural"``, ``"semantic"``).
        description: Human-readable rule description.
        confidence_min: Minimum confidence score (0-1).
        confidence_max: Maximum confidence score (0-1).
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(..., description="Rule name")
    family: str = Field(..., description="Rule family")
    description: str = Field(..., description="Rule description")
    confidence_min: float = Field(..., ge=0.0, le=1.0, description="Minimum confidence")
    confidence_max: float = Field(..., ge=0.0, le=1.0, description="Maximum confidence")


class RulesResponse(BaseModel):
    """Response body for ``GET /api/v1/rules``.

    Attributes:
        rules: List of all registered translation rules.
        count: Total number of rules.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    rules: list[RuleMetadata] = Field(..., description="Translation rules")
    count: int = Field(..., ge=0, description="Total rule count")


# ---------------------------------------------------------------------------
# /api/v1/visualize
# ---------------------------------------------------------------------------


class VisualizeRequest(BaseModel):
    """Request body for ``POST /api/v1/visualize``.

    Attributes:
        source_code: Source code as a string.
        language: Programming language.
        format: Output format
            (``"mermaid"``, ``"json"``, or ``"graphml"``).
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    source_code: str = Field(..., min_length=1, description="Source code to visualize")
    language: Literal["python", "javascript", "typescript"] = Field(
        ..., description="Programming language"
    )
    format: Literal["mermaid", "json", "graphml"] = Field(
        default="json", description="Output format"
    )


class VisualizeResponse(BaseModel):
    """Response body for ``POST /api/v1/visualize``.

    Attributes:
        request_id: Unique identifier for this request.
        diagram: Diagram in the requested format.
        format: Actual format used.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    request_id: str = Field(..., description="Unique request identifier (UUID4)")
    diagram: str = Field(..., description="Diagram in requested format")
    format: str = Field(..., description="Actual format used")


# ---------------------------------------------------------------------------
# /api/v1/metrics
# ---------------------------------------------------------------------------


class MetricsResponse(BaseModel):
    """Response body for ``GET /api/v1/metrics``.

    Attributes:
        requests_total: Total number of requests processed.
        active_sessions: Number of active sessions.
        avg_latency_ms: Average request latency in milliseconds.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    requests_total: int = Field(..., ge=0, description="Total requests")
    active_sessions: int = Field(..., ge=0, description="Active sessions")
    avg_latency_ms: float = Field(..., ge=0.0, description="Average latency")
