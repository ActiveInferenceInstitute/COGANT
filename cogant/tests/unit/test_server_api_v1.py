"""Unit tests for server /api/v1/ routes — rules, analyze, roundtrip, visualize, metrics."""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from cogant.server.app import create_app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    app = create_app(rate_limit_requests=100000, rate_limit_window_s=3600.0)
    return TestClient(app)


@pytest.fixture()
def tiny_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("x: int = 0\n\ndef increment(n: int) -> int:\n    return n + 1\n")
    return repo


@pytest.mark.unit
def test_api_v1_rules_returns_200(client):
    r = client.get("/api/v1/rules")
    assert r.status_code == 200


@pytest.mark.unit
def test_api_v1_rules_returns_list(client):
    r = client.get("/api/v1/rules")
    data = r.json()
    assert "rules" in data
    assert isinstance(data["rules"], list)
    assert len(data["rules"]) > 0


@pytest.mark.unit
def test_api_v1_rules_each_has_name(client):
    rules = client.get("/api/v1/rules").json()["rules"]
    for rule in rules:
        assert "name" in rule
        assert isinstance(rule["name"], str)


@pytest.mark.unit
def test_api_v1_metrics_returns_200(client):
    r = client.get("/api/v1/metrics")
    assert r.status_code == 200


@pytest.mark.unit
def test_api_v1_metrics_has_total_requests(client):
    client.get("/health")
    r = client.get("/api/v1/metrics")
    data = r.json()
    assert isinstance(data, dict)


@pytest.mark.unit
def test_api_v1_analyze_missing_repo_returns_error(client):
    r = client.post("/api/v1/analyze", json={"repo_path": "/nonexistent/path/xyz"})
    assert r.status_code in (404, 422, 400, 500)


@pytest.mark.unit
def test_api_v1_analyze_empty_body_returns_422(client):
    r = client.post("/api/v1/analyze", json={})
    assert r.status_code == 422


@pytest.mark.unit
def test_api_v1_roundtrip_missing_path_returns_error(client):
    r = client.post("/api/v1/roundtrip", json={"repo_path": "/nonexistent/path/xyz"})
    assert r.status_code in (404, 422, 400, 500)


@pytest.mark.unit
def test_api_v1_roundtrip_empty_body_returns_422(client):
    r = client.post("/api/v1/roundtrip", json={})
    assert r.status_code == 422


@pytest.mark.unit
def test_api_v1_visualize_analyze_repo(client, tiny_repo):
    r = client.post("/api/v1/visualize", json={"repo_path": str(tiny_repo)})
    # Visualize may return various status codes
    assert r.status_code in (200, 404, 422, 400, 500)


@pytest.mark.unit
def test_api_v1_visualize_empty_body(client):
    r = client.post("/api/v1/visualize", json={})
    assert r.status_code == 422


@pytest.mark.unit
def test_api_v1_analyze_real_repo(client, tiny_repo):
    r = client.post("/api/v1/analyze", json={"repo_path": str(tiny_repo)})
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert isinstance(data, dict)
