"""Prometheus metric labels must be bounded and correctly escaped.

The observability middleware records every request, including requests
rejected before authentication. Keying series by the raw URL path let
any unauthenticated client mint an unbounded number of label series
(memory growth on a long-running server) and inject ``"`` / ``\\`` into
label values, which corrupts the whole ``/metrics`` exposition.
"""

from __future__ import annotations

import re

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from cogant.server.app import _MetricsStore, create_app  # noqa: E402

# One Prometheus text-format sample line: name{label="value",...} number
_LABEL_VALUE = r'"(?:[^"\\\n]|\\["\\n])*"'
_SAMPLE_LINE = re.compile(
    r"^[a-zA-Z_:][a-zA-Z0-9_:]*"
    r"(?:\{[a-zA-Z_][a-zA-Z0-9_]*=" + _LABEL_VALUE + r"(?:,[a-zA-Z_][a-zA-Z0-9_]*="
    r"" + _LABEL_VALUE + r")*\})?"
    r" [-+0-9.eEinfNa]+$"
)


def _series_count(store: _MetricsStore) -> int:
    return len(store.requests) + len(store.duration_sum) + len(store.duration_count)


def test_unauthenticated_unknown_paths_do_not_mint_new_metric_series() -> None:
    app = create_app(auth_token="secret-token")
    client = TestClient(app)

    client.get("/probe-0")
    baseline = _series_count(app.state.metrics)
    for i in range(1, 50):
        assert client.get(f"/probe-{i}").status_code == 401

    assert _series_count(app.state.metrics) == baseline


def test_unknown_paths_and_methods_collapse_into_bounded_labels() -> None:
    app = create_app()
    client = TestClient(app)

    for i in range(20):
        client.get(f"/does-not-exist/{i}")
        client.request(f"PROBE{i}", "/health")

    methods = {method for method, _path, _status in app.state.metrics.requests}
    paths = {path for _method, path, _status in app.state.metrics.requests}
    assert len(methods) <= 8
    assert "/health" in paths
    assert not any(p.startswith("/does-not-exist") for p in paths)


def test_metrics_exposition_stays_parseable_for_hostile_paths() -> None:
    app = create_app()
    client = TestClient(app)

    client.get("/x%22y%5C")
    client.get("/health")
    text = client.get("/metrics").text

    for line in text.splitlines():
        if line.startswith("#") or not line:
            continue
        assert _SAMPLE_LINE.match(line), line


def test_render_prometheus_escapes_label_values() -> None:
    store = _MetricsStore()
    store.record("GET", 'a"b\\c\nd', 200, 0.001)

    text = store.render_prometheus()

    assert 'path="a\\"b\\\\c\\nd"' in text
    for line in text.splitlines():
        if line.startswith("#") or not line:
            continue
        assert _SAMPLE_LINE.match(line), line


def test_registered_routes_keep_their_own_path_label() -> None:
    app = create_app()
    client = TestClient(app)

    client.get("/health")
    client.get("/api/v1/rules")

    assert app.state.metrics.requests[("GET", "/health", 200)] == 1
    assert app.state.metrics.requests[("GET", "/api/v1/rules", 200)] == 1
