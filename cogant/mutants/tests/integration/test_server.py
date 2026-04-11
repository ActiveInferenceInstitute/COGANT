"""Integration tests for :mod:`cogant.server.app`.

These tests exercise the FastAPI app through ``httpx.AsyncClient`` +
``httpx.ASGITransport`` so no socket, process, or real HTTP server is
involved — the ASGI app is driven in-process by asyncio. Every test is
a plain synchronous function that delegates to ``anyio.run`` with an
inner async closure, which sidesteps the flaky ``pytest-anyio`` PyPI
placeholder without losing any async semantics.

The tests follow the COGANT no-mocks policy: real Pydantic validation,
real pipeline calls, real fixture repositories under
``examples/control_positive/calculator``. The ``/reverse`` path uses a
real GNN markdown snippet assembled inline so the test does not depend
on pipeline output paths.
"""

from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

import anyio
import pytest

fastapi = pytest.importorskip("fastapi")  # noqa: F841
httpx = pytest.importorskip("httpx")

from httpx import ASGITransport, AsyncClient  # noqa: E402

import cogant  # noqa: E402
from cogant.server.app import create_app  # noqa: E402

# ---------------------------------------------------------------------------
# Shared helpers.
# ---------------------------------------------------------------------------


def _run(coro_factory):  # type: ignore[no-untyped-def]
    """Drive an async test body with ``anyio.run``.

    ``coro_factory`` is a zero-arg callable returning a coroutine so
    each test can be wrapped as ``_run(lambda: body(...))`` without
    building a coroutine at collection time (which would warn about
    never awaiting the returned object).
    """
    return anyio.run(coro_factory)


def _client(app):  # type: ignore[no-untyped-def]
    """Build an in-process async client against the given FastAPI app."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# Minimal GNN markdown snippet the ``/reverse`` synthesiser can parse.
# We mirror the structure of ``cogant.reverse.parser.parse_gnn``'s
# required sections: ModelName, StateSpaceBlock, Connections, and a
# Time declaration. Matrices are optional for a round-trip smoke test.
_MINIMAL_GNN = """## ModelName
ServerTestModel

## StateSpaceBlock
s_f0[2,1,type=categorical]
o_m0[2,1,type=categorical]
u_c0[2,1,type=categorical]

## Connections
(s_f0) > (o_m0)
(u_c0) > (s_f0)

## ActInfOntologyAnnotation
s_f0=HiddenState
o_m0=Observation
u_c0=Action

## Time
Dynamic
DiscreteTime=s_f0
ModelTimeHorizon=5
"""


# Path to a real example repo that exists in the repo tree and is small
# enough to run the forward pipeline on in well under the pytest 10s
# default timeout.
_CALCULATOR_REPO = (
    Path(__file__).resolve().parents[2] / "examples" / "control_positive" / "calculator"
)


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


def test_health_returns_200_with_version() -> None:
    """``GET /health`` must return the installed COGANT version."""
    app = create_app()

    async def body() -> None:
        async with _client(app) as c:
            resp = await c.get("/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "ok"
        assert payload["version"] == cogant.__version__
        assert payload["docs"] == "/docs"

    _run(body)


def test_ready_returns_200_or_503() -> None:
    """``GET /ready`` must return 200 when deps import, 503 otherwise.

    Either outcome is a valid production signal — we only assert that
    the response is one of the two documented codes and carries the
    ``checks`` dict so callers can debug a 503.
    """
    app = create_app()

    async def body() -> None:
        async with _client(app) as c:
            resp = await c.get("/ready")
        assert resp.status_code in (200, 503)
        payload = resp.json()
        assert payload["status"] in ("ready", "not_ready")
        assert "checks" in payload
        assert isinstance(payload["checks"], dict)
        assert len(payload["checks"]) >= 1

    _run(body)


def test_analyze_invalid_body_returns_422() -> None:
    """Missing ``repo_path`` must yield 422 with the uniform error shape."""
    app = create_app()

    async def body() -> None:
        async with _client(app) as c:
            resp = await c.post("/analyze", json={})
        assert resp.status_code == 422
        payload = resp.json()
        assert "detail" in payload
        assert "error_type" in payload
        assert payload["error_type"] == "RequestValidationError"

    _run(body)


def test_analyze_nonexistent_path_returns_404() -> None:
    """A repo path that does not exist must yield 404, not 500."""
    app = create_app()

    async def body() -> None:
        async with _client(app) as c:
            resp = await c.post(
                "/analyze",
                json={"repo_path": "/definitely/not/a/real/path/xyz", "skip_dynamic": True},
            )
        assert resp.status_code == 404
        payload = resp.json()
        assert "does not exist" in payload["detail"]
        assert payload["error_type"] == "HTTPException"

    _run(body)


def test_reverse_with_valid_gnn_returns_zip_b64() -> None:
    """``POST /reverse`` must synthesise a package and return it as zip b64."""
    app = create_app()

    async def body() -> None:
        async with _client(app) as c:
            resp = await c.post("/reverse", json={"gnn_text": _MINIMAL_GNN})
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert "package_zip_b64" in payload
        assert payload["file_count"] > 0
        assert payload["cogant_version"] == cogant.__version__

        # Decode the zip and assert the synthesised package has at least
        # the state module — this proves the synthesiser actually ran,
        # not just that we got a well-formed response envelope.
        raw = base64.b64decode(payload["package_zip_b64"])
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            names = zf.namelist()
        assert any(name.endswith("state.py") for name in names), names
        assert any(name.endswith("__init__.py") for name in names), names

    _run(body)


def test_reverse_with_missing_body_returns_422() -> None:
    """Empty or missing ``gnn_text`` must be rejected with 422."""
    app = create_app()

    async def body() -> None:
        async with _client(app) as c:
            resp = await c.post("/reverse", json={"gnn_text": ""})
        assert resp.status_code == 422
        payload = resp.json()
        assert "gnn_text" in payload["detail"]

    _run(body)


def test_metrics_returns_prometheus_text() -> None:
    """``GET /metrics`` must expose Prometheus v0.0.4 text output."""
    app = create_app()

    async def body() -> None:
        async with _client(app) as c:
            # Drive at least one request so the metrics store is non-empty
            # and the counters for ``/health`` appear in the output.
            await c.get("/health")
            resp = await c.get("/metrics")
        assert resp.status_code == 200
        ctype = resp.headers["content-type"]
        assert ctype.startswith("text/plain")
        text = resp.text
        assert "cogant_http_requests_total" in text
        assert "cogant_http_request_duration_seconds" in text
        assert f'cogant_build_info{{version="{cogant.__version__}"}} 1' in text
        # We previously hit /health, so it should show up in the counter.
        assert 'path="/health"' in text

    _run(body)


def test_openapi_json_is_served() -> None:
    """FastAPI must auto-generate the OpenAPI schema at ``/openapi.json``."""
    app = create_app()

    async def body() -> None:
        async with _client(app) as c:
            resp = await c.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "COGANT Production Server"
        assert schema["info"]["version"] == cogant.__version__
        paths = schema["paths"]
        for endpoint in ("/health", "/ready", "/analyze", "/reverse", "/roundtrip", "/metrics"):
            assert endpoint in paths, f"{endpoint} missing from OpenAPI schema"

    _run(body)


def test_rate_limiter_trips_on_analyze_burst() -> None:
    """A burst of ``/analyze`` calls past the limit must return 429.

    We configure the limiter down to 3 requests per window so the test
    runs quickly, drive 5 hits against an obviously invalid path, and
    assert that at least one of the tail requests is rate-limited with
    the uniform error shape.
    """
    app = create_app(rate_limit_requests=3, rate_limit_window_s=60.0)

    async def body() -> None:
        async with _client(app) as c:
            statuses: list[int] = []
            for _ in range(5):
                resp = await c.post(
                    "/analyze",
                    json={"repo_path": "/nope/still/not/real", "skip_dynamic": True},
                )
                statuses.append(resp.status_code)
        # First 3 attempts should be allowed through (hitting 404 because
        # the path does not exist); the 4th and 5th must be rate-limited.
        assert statuses[:3] == [404, 404, 404], statuses
        assert 429 in statuses[3:], statuses

    _run(body)


def test_analyze_happy_path_with_real_repo() -> None:
    """A real repo under ``examples/`` must analyse cleanly via ``/analyze``.

    This test is marked ``integration`` so it shares the slow-test
    pytest lane with the rest of the pipeline suite. It skips if the
    fixture directory has been moved out of the tree so the suite
    stays green under partial checkouts.
    """
    if not _CALCULATOR_REPO.exists():
        pytest.skip(f"calculator fixture not present at {_CALCULATOR_REPO}")

    app = create_app()

    async def body() -> None:
        async with _client(app) as c:
            resp = await c.post(
                "/analyze",
                json={"repo_path": str(_CALCULATOR_REPO), "skip_dynamic": True},
            )
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        # The calculator fixture is small but non-trivial; we only
        # assert the shape is correct and the pipeline produced at
        # least one node. Concrete counts drift as rules evolve.
        assert payload["nodes"] >= 1
        assert payload["edges"] >= 0
        assert isinstance(payload["roles"], dict)
        assert isinstance(payload["errors"], list)

    _run(body)
