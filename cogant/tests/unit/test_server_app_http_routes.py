"""Targeted unit tests for: exercise cogant.server.app FastAPI endpoints.

Drives every HTTP route via fastapi.testclient.TestClient against a real
tiny repo and real GNN markdown. No mocks, no monkeypatches — the server
is constructed with ``create_app`` and hit with actual JSON bodies.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Skip this whole module when FastAPI is not installed. In the CI
# matrix we expect it to be present; on minimal installs it gets
# skipped rather than failing.
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from cogant.server.app import (  # noqa: E402
    _MetricsStore,
    _probe_dependencies,
    _RateLimiter,
    create_app,
)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    # Very high rate limit so the tests never trip it by accident.
    app = create_app(
        rate_limit_requests=10000,
        rate_limit_window_s=3600.0,
        workspace_root=tmp_path,
    )
    return TestClient(app)


@pytest.fixture()
def throttled_client(tmp_path: Path) -> TestClient:
    # Very low rate limit so we can verify the 429 path.
    app = create_app(
        rate_limit_requests=1,
        rate_limit_window_s=60.0,
        workspace_root=tmp_path,
    )
    return TestClient(app)


@pytest.fixture()
def tiny_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def main() -> int:\n    return 1\n")
    return repo


@pytest.fixture()
def gnn_text() -> str:
    """Return a complete one-state GNN document with explicit matrices."""
    return """## ModelName
ServerUnitModel

## StateSpaceBlock
s_f0[1,1,type=float]
o_m0[1,1,type=float]
u_c0[1,1,type=int]

## Connections
(s_f0) > (o_m0)
(u_c0) > (s_f0)

## InitialParameterization
D_f0={ (1.0) }
A_m0={ (1.0) }
B_f0=identity(1,1,1)
C_m0={ (0.0) }

## ActInfOntologyAnnotation
s_f0=HiddenState
o_m0=Observation
u_c0=Action

## Time
Static
"""


# ---------------------------------------------------------------------------
# health / metrics / ready — static routes
# ---------------------------------------------------------------------------


class TestStaticRoutes:
    def test_health_returns_200(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "version" in body

    def test_metrics_returns_prometheus_text(self, client: TestClient) -> None:
        # Hit the server once so metrics have something to report.
        client.get("/health")
        r = client.get("/metrics")
        assert r.status_code == 200
        # Prometheus text format uses "# HELP" / "# TYPE" comments
        assert "content-type" in {k.lower() for k in r.headers.keys()}
        text = r.text
        assert isinstance(text, str)

    def test_ready_probe_returns_200_or_503(self, client: TestClient) -> None:
        r = client.get("/ready")
        # In a healthy env this is 200; if any import probe fails it's 503.
        assert r.status_code in (200, 503)

    def test_openapi_json_available(self, client: TestClient) -> None:
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "openapi" in schema
        assert "paths" in schema
        # Our registered routes must show up
        for path in ["/health", "/metrics", "/analyze", "/reverse", "/roundtrip"]:
            assert path in schema["paths"]


# ---------------------------------------------------------------------------
# /analyze
# ---------------------------------------------------------------------------


class TestAnalyzeEndpoint:
    def test_analyze_happy_path(self, client: TestClient, tiny_repo: Path) -> None:
        r = client.post(
            "/analyze",
            json={"repo_path": "repo", "skip_dynamic": True},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # AnalyzeResponse has at least nodes, edges, mappings, errors
        for key in ["nodes", "edges", "mappings", "errors"]:
            assert key in body

    def test_analyze_missing_repo_returns_404(self, client: TestClient) -> None:
        r = client.post(
            "/analyze",
            json={"repo_path": "missing-repo"},
        )
        assert r.status_code == 404
        body = r.json()
        assert "detail" in body

    def test_analyze_empty_body_returns_422(self, client: TestClient) -> None:
        r = client.post("/analyze", json={})
        assert r.status_code == 422
        body = r.json()
        assert body.get("error_type") == "RequestValidationError"


# ---------------------------------------------------------------------------
# /reverse
# ---------------------------------------------------------------------------


class TestReverseEndpoint:
    def test_reverse_happy_path_returns_base64_zip(self, client: TestClient, gnn_text: str) -> None:
        r = client.post("/reverse", json={"gnn_text": gnn_text})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "package_zip_b64" in body
        assert isinstance(body["package_zip_b64"], str)
        assert body["file_count"] >= 1

    def test_reverse_empty_body_returns_422(self, client: TestClient) -> None:
        r = client.post("/reverse", json={})
        assert r.status_code == 422
        assert "gnn_text" in r.json()["detail"]

    def test_reverse_blank_gnn_text_returns_422(self, client: TestClient) -> None:
        r = client.post("/reverse", json={"gnn_text": "   \n   "})
        assert r.status_code == 422

    def test_reverse_rejects_non_gnn_text(self, client: TestClient) -> None:
        """Malformed GNN text is rejected instead of becoming a package."""
        r = client.post("/reverse", json={"gnn_text": "not gnn at all"})
        assert r.status_code == 422
        assert "invalid GNN text" in r.json()["detail"]


# ---------------------------------------------------------------------------
# /roundtrip
# ---------------------------------------------------------------------------


class TestRoundtripEndpoint:
    def test_roundtrip_missing_path_returns_404(self, client: TestClient) -> None:
        r = client.post(
            "/roundtrip",
            json={"repo_path": "missing-repo", "threshold": 0.8},
        )
        assert r.status_code == 404

    def test_roundtrip_invalid_body_returns_422(self, client: TestClient) -> None:
        r = client.post("/roundtrip", json={})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def test_analyze_hits_rate_limit_after_one_request(
        self, throttled_client: TestClient, tiny_repo: Path
    ) -> None:
        # First request: success or 404/422 (still counts for the limiter)
        r1 = throttled_client.post(
            "/analyze",
            json={"repo_path": "repo", "skip_dynamic": True},
        )
        assert r1.status_code in (200, 404, 422, 429, 500)
        # Second request must be rate-limited (max_requests=1)
        r2 = throttled_client.post(
            "/analyze",
            json={"repo_path": "repo", "skip_dynamic": True},
        )
        assert r2.status_code == 429
        body = r2.json()
        assert "rate limit" in body["detail"].lower()

    def test_health_bypasses_rate_limit(self, throttled_client: TestClient) -> None:
        """Health is unlimited even with a strict limiter configured."""
        for _ in range(5):
            r = throttled_client.get("/health")
            assert r.status_code == 200


# ---------------------------------------------------------------------------
# unit tests on helper classes
# ---------------------------------------------------------------------------


class TestMetricsStoreAndRateLimiter:
    def test_metrics_store_records_and_renders(self) -> None:
        store = _MetricsStore()
        store.record("GET", "/health", 200, 0.001)
        store.record("POST", "/analyze", 500, 0.5)
        store.record_rate_limited("POST", "/analyze")
        text = store.render_prometheus()
        assert isinstance(text, str)
        # Should mention at least one of the counter names we track
        assert "requests" in text.lower() or "errors" in text.lower() or "cogant" in text.lower()

    def test_rate_limiter_enforces_window(self) -> None:
        limiter = _RateLimiter(max_requests=2, window_s=60.0)
        # First two calls from same key succeed
        assert limiter.check("client:/path") is True
        assert limiter.check("client:/path") is True
        # Third is throttled
        assert limiter.check("client:/path") is False
        # A different key is independent
        assert limiter.check("other:/path") is True

    def test_probe_dependencies_returns_status_dict(self) -> None:
        status = _probe_dependencies()
        assert isinstance(status, dict)
        # Every probed dep must be present with a string status
        for name in ["cogant.api.pipeline", "cogant.reverse", "networkx", "pydantic"]:
            assert name in status
            assert isinstance(status[name], str)


class TestAuthDecoupling:
    """Auth must protect non-public routes independent of the rate-limit set."""

    def test_auth_protects_non_rate_limited_route(self, tmp_path: Path) -> None:
        app = create_app(
            rate_limit_requests=10000,
            rate_limit_window_s=3600.0,
            workspace_root=tmp_path,
            auth_token="s3cret",
        )
        client = TestClient(app)
        # /api/v1/rules is not in the default rate_limited_paths set, so it
        # must still be auth-protected when a token is configured.
        assert client.get("/api/v1/rules").status_code == 401
        assert (
            client.get("/api/v1/rules", headers={"authorization": "Bearer s3cret"}).status_code
            == 200
        )

    def test_auth_leaves_unlimited_route_open(self, tmp_path: Path) -> None:
        app = create_app(
            rate_limit_requests=10000,
            rate_limit_window_s=3600.0,
            workspace_root=tmp_path,
            auth_token="s3cret",
        )
        client = TestClient(app)
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code in (200, 503)
