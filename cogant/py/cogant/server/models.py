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

from typing import Any

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

    detail: str
    error_type: str
