"""Behavioral tests for cogant.server.models pydantic schemas.

Tests cover successful construction, default values, validation errors,
extra-field policy, and round-trip through model_dump().
"""

from __future__ import annotations

import sys
import types

import pytest
from pydantic import ValidationError

# cogant.server.__init__ eagerly imports `cogant.server.app` which does
# not exist in this worktree. Stub it out *before* importing the models
# module so that `from cogant.server.models import ...` succeeds and
# coverage is correctly attributed to the real dotted module name.
if "cogant.server.app" not in sys.modules:
    _stub = types.ModuleType("cogant.server.app")
    _stub.create_app = lambda *_a, **_kw: None  # noqa: E731
    _stub.run_server = lambda *_a, **_kw: None  # noqa: E731
    sys.modules["cogant.server.app"] = _stub

from cogant.server.models import (  # noqa: E402
    AnalyzeRequest,
    AnalyzeResponse,
    ErrorResponse,
    ExplainResponse,
    GraphEdge,
    GraphNode,
    GraphResponse,
    HealthResponse,
    RoundtripRequest,
    RoundtripResponse,
)


# --------------------------- AnalyzeRequest ----------------------------- #


def test_analyze_request_minimal_uses_defaults():
    """repo_path is required; stages/skip_dynamic have defaults."""
    req = AnalyzeRequest(repo_path="/tmp/repo")
    assert req.repo_path == "/tmp/repo"
    assert req.stages is None
    assert req.skip_dynamic is True


def test_analyze_request_full_construction():
    """All fields can be set explicitly."""
    req = AnalyzeRequest(
        repo_path="/tmp/r",
        stages=["ingest", "static"],
        skip_dynamic=False,
    )
    assert req.stages == ["ingest", "static"]
    assert req.skip_dynamic is False


def test_analyze_request_rejects_empty_repo_path():
    """Empty repo_path fails min_length validation."""
    with pytest.raises(ValidationError):
        AnalyzeRequest(repo_path="")


def test_analyze_request_forbids_extra_fields():
    """extra='forbid' rejects unknown keys."""
    with pytest.raises(ValidationError):
        AnalyzeRequest(repo_path="/tmp", extra_field="oops")


# --------------------------- AnalyzeResponse ---------------------------- #


def test_analyze_response_defaults_and_dump():
    """Default roles/errors lists are empty, and model_dump returns a dict."""
    resp = AnalyzeResponse(nodes=10, edges=20, mappings=5)
    assert resp.nodes == 10
    assert resp.roles == {}
    assert resp.errors == []
    dumped = resp.model_dump()
    assert dumped["nodes"] == 10
    assert dumped["mappings"] == 5


def test_analyze_response_rejects_negative_counts():
    """ge=0 constraint prevents negative counts."""
    with pytest.raises(ValidationError):
        AnalyzeResponse(nodes=-1, edges=0, mappings=0)


def test_analyze_response_populated_roles_and_errors():
    """Custom role map and errors list round-trip through model_dump."""
    resp = AnalyzeResponse(
        nodes=1,
        edges=1,
        mappings=1,
        roles={"observation": 3, "action": 1},
        errors=["minor"],
    )
    assert resp.roles["observation"] == 3
    assert resp.errors == ["minor"]


# --------------------------- HealthResponse ----------------------------- #


def test_health_response_defaults():
    """HealthResponse only requires version; status and docs default."""
    resp = HealthResponse(version="1.2.3")
    assert resp.status == "ok"
    assert resp.version == "1.2.3"
    assert resp.docs == "/docs"


def test_health_response_override_docs():
    """docs can be overridden."""
    resp = HealthResponse(version="0.0", docs="/stdlib-docs")
    assert resp.docs == "/stdlib-docs"


# --------------------------- ExplainResponse ---------------------------- #


def test_explain_response_extra_allowed_and_defaults():
    """extra='allow' means arbitrary additional keys are preserved."""
    resp = ExplainResponse(
        node_name="do_thing",
        node_id="n1",
        node_kind="function",
        blanket_role="markov_blanket",
        extra_key="custom",
    )
    assert resp.node_name == "do_thing"
    assert resp.rules_fired == []
    assert resp.rules_considered == []
    # Extra fields are preserved (extra=allow)
    dumped = resp.model_dump()
    assert dumped.get("extra_key") == "custom"


# --------------------------- RoundtripRequest --------------------------- #


def test_roundtrip_request_defaults_threshold_to_point_seven():
    """Default threshold matches the server spec."""
    req = RoundtripRequest(repo_path="/tmp/r")
    assert req.threshold == 0.7


def test_roundtrip_request_clamps_via_validation():
    """threshold must live in [0, 1]."""
    with pytest.raises(ValidationError):
        RoundtripRequest(repo_path="/tmp/r", threshold=1.5)
    with pytest.raises(ValidationError):
        RoundtripRequest(repo_path="/tmp/r", threshold=-0.1)


def test_roundtrip_request_forbids_extra_fields():
    """extra='forbid' on the request model."""
    with pytest.raises(ValidationError):
        RoundtripRequest(repo_path="/tmp/r", unknown="x")


# --------------------------- RoundtripResponse -------------------------- #


def test_roundtrip_response_construction_and_dump():
    """All required fields can be supplied and the dump is stable."""
    resp = RoundtripResponse(
        role_match_score=0.85,
        is_isomorphic=True,
        original_roles={"observation": 2},
        synthesized_roles={"observation": 2},
        threshold=0.8,
    )
    assert resp.is_isomorphic is True
    dumped = resp.model_dump()
    assert dumped["role_match_score"] == 0.85
    assert dumped["errors"] == []


def test_roundtrip_response_rejects_out_of_range_scores():
    """role_match_score must be in [0, 1]."""
    with pytest.raises(ValidationError):
        RoundtripResponse(
            role_match_score=2.0,
            is_isomorphic=False,
            threshold=0.5,
        )


# --------------------------- Graph models ------------------------------- #


def test_graph_node_and_edge_minimal_construction():
    """GraphNode and GraphEdge accept their required fields."""
    node = GraphNode(id="n1", name="main", kind="function")
    edge = GraphEdge(id="e1", source="n1", target="n2", kind="calls")
    assert node.role is None
    assert edge.source == "n1"


def test_graph_response_defaults_and_round_trip():
    """Empty GraphResponse produces empty lists; populated dumps cleanly."""
    empty = GraphResponse()
    assert empty.nodes == []
    assert empty.edges == []

    populated = GraphResponse(
        nodes=[GraphNode(id="n1", name="f", kind="function", role="action")],
        edges=[GraphEdge(id="e1", source="n1", target="n2", kind="calls")],
    )
    dumped = populated.model_dump()
    assert dumped["nodes"][0]["role"] == "action"
    assert dumped["edges"][0]["kind"] == "calls"


# --------------------------- ErrorResponse ------------------------------ #


def test_error_response_requires_both_fields():
    """detail and error_type are both required."""
    resp = ErrorResponse(detail="not found", error_type="FileNotFoundError")
    assert resp.detail == "not found"
    with pytest.raises(ValidationError):
        ErrorResponse(detail="oops")  # missing error_type
