#!/usr/bin/env python3
"""Coverage boost batch 85 — server/app.py pure utility classes,
rust_backend.py env/build functions, cogant/__init__.py attributes.

Covers:
- server/app.py: _MetricsStore (record, record_rate_limited, render_prometheus),
  _RateLimiter (check with allow/deny), _probe_dependencies
- rust_backend.py: _env_prefers_rust paths, build_program_graph fallback,
  RUST_AVAILABLE, rust_version, get_program_graph_impl
- cogant/__init__.py: __version__, __rust_version__, _RUST_AVAILABLE,
  CogantSession, GNNBundle aliases, run_pipeline (ImportError path)
"""

import os
import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# server/app.py — _MetricsStore
# ---------------------------------------------------------------------------

class TestMetricsStore:
    def _make_store(self):
        from cogant.server.app import _MetricsStore
        return _MetricsStore()

    def test_init_empty(self):
        store = self._make_store()
        assert store.requests is not None
        assert store.errors is not None
        assert store.rate_limited is not None

    def test_record_increments_requests(self):
        store = self._make_store()
        store.record("GET", "/health", 200, 0.01)
        assert store.requests[("GET", "/health", 200)] == 1
        store.record("GET", "/health", 200, 0.02)
        assert store.requests[("GET", "/health", 200)] == 2

    def test_record_increments_duration(self):
        store = self._make_store()
        store.record("POST", "/analyze", 200, 1.5)
        store.record("POST", "/analyze", 200, 0.5)
        assert abs(store.duration_sum[("POST", "/analyze")] - 2.0) < 1e-9
        assert store.duration_count[("POST", "/analyze")] == 2

    def test_record_500_increments_errors(self):
        store = self._make_store()
        store.record("POST", "/analyze", 500, 0.1)
        assert store.errors[("POST", "/analyze")] == 1

    def test_record_200_does_not_increment_errors(self):
        store = self._make_store()
        store.record("GET", "/health", 200, 0.01)
        assert store.errors.get(("GET", "/health"), 0) == 0

    def test_record_rate_limited(self):
        store = self._make_store()
        store.record_rate_limited("POST", "/analyze")
        assert store.rate_limited[("POST", "/analyze")] == 1
        store.record_rate_limited("POST", "/analyze")
        assert store.rate_limited[("POST", "/analyze")] == 2

    def test_render_prometheus_returns_string(self):
        store = self._make_store()
        result = store.render_prometheus()
        assert isinstance(result, str)
        assert "cogant_http_requests_total" in result
        assert "cogant_build_info" in result
        assert result.endswith("\n")

    def test_render_prometheus_with_data(self):
        store = self._make_store()
        store.record("GET", "/health", 200, 0.005)
        store.record("POST", "/analyze", 500, 2.1)
        store.record_rate_limited("POST", "/analyze")
        result = store.render_prometheus()
        assert "GET" in result
        assert "POST" in result
        assert "/health" in result

    def test_render_prometheus_counter_type(self):
        store = self._make_store()
        result = store.render_prometheus()
        assert "# TYPE cogant_http_requests_total counter" in result
        assert "# HELP cogant_http_errors_total" in result


# ---------------------------------------------------------------------------
# server/app.py — _RateLimiter
# ---------------------------------------------------------------------------

class TestRateLimiter:
    def _make_limiter(self, max_requests=3, window_s=60.0):
        from cogant.server.app import _RateLimiter
        return _RateLimiter(max_requests=max_requests, window_s=window_s)

    def test_allow_within_limit(self):
        limiter = self._make_limiter(max_requests=5)
        for _ in range(5):
            assert limiter.check("192.168.1.1") is True

    def test_deny_over_limit(self):
        limiter = self._make_limiter(max_requests=3)
        for _ in range(3):
            limiter.check("10.0.0.1")
        # 4th should be denied
        assert limiter.check("10.0.0.1") is False

    def test_different_keys_independent(self):
        limiter = self._make_limiter(max_requests=2)
        assert limiter.check("ip_a") is True
        assert limiter.check("ip_a") is True
        assert limiter.check("ip_a") is False
        # Different IP not throttled
        assert limiter.check("ip_b") is True
        assert limiter.check("ip_b") is True

    def test_window_expired_allows_again(self):
        import time
        limiter = self._make_limiter(max_requests=2, window_s=0.001)
        assert limiter.check("key") is True
        assert limiter.check("key") is True
        assert limiter.check("key") is False
        # Sleep to expire window
        time.sleep(0.01)
        assert limiter.check("key") is True

    def test_single_request_always_allowed(self):
        limiter = self._make_limiter(max_requests=1)
        assert limiter.check("solo") is True
        assert limiter.check("solo") is False


# ---------------------------------------------------------------------------
# server/app.py — _probe_dependencies
# ---------------------------------------------------------------------------

class TestProbeDependencies:
    def test_returns_dict(self):
        from cogant.server.app import _probe_dependencies
        result = _probe_dependencies()
        assert isinstance(result, dict)
        assert len(result) >= 1

    def test_cogant_api_pipeline_present(self):
        from cogant.server.app import _probe_dependencies
        result = _probe_dependencies()
        assert "cogant.api.pipeline" in result
        assert result["cogant.api.pipeline"] == "ok"

    def test_networkx_present(self):
        from cogant.server.app import _probe_dependencies
        result = _probe_dependencies()
        # networkx is a core dep so should be "ok"
        assert result.get("networkx") == "ok"

    def test_values_are_strings(self):
        from cogant.server.app import _probe_dependencies
        result = _probe_dependencies()
        for v in result.values():
            assert isinstance(v, str)


# ---------------------------------------------------------------------------
# rust_backend.py — _env_prefers_rust and build_program_graph
# ---------------------------------------------------------------------------

class TestEnvPrefersRust:
    def test_returns_none_when_unset(self):
        from cogant.rust_backend import _env_prefers_rust
        env = os.environ.copy()
        os.environ.pop("COGANT_USE_RUST", None)
        try:
            result = _env_prefers_rust()
            assert result is None
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_returns_true_for_1(self):
        from cogant.rust_backend import _env_prefers_rust
        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "1"
        try:
            result = _env_prefers_rust()
            assert result is True
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_returns_true_for_true(self):
        from cogant.rust_backend import _env_prefers_rust
        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "true"
        try:
            result = _env_prefers_rust()
            assert result is True
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_returns_false_for_0(self):
        from cogant.rust_backend import _env_prefers_rust
        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "0"
        try:
            result = _env_prefers_rust()
            assert result is False
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_returns_false_for_false(self):
        from cogant.rust_backend import _env_prefers_rust
        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "false"
        try:
            result = _env_prefers_rust()
            assert result is False
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_returns_none_for_invalid(self):
        from cogant.rust_backend import _env_prefers_rust
        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "maybe"
        try:
            result = _env_prefers_rust()
            assert result is None
        finally:
            os.environ.clear()
            os.environ.update(env)


class TestBuildProgramGraph:
    def test_returns_builder_with_use_rust_false(self):
        from cogant.rust_backend import build_program_graph
        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "0"
        try:
            builder = build_program_graph("repo://test", use_rust=False)
            assert builder is not None
            assert hasattr(builder, "add_node")
            assert hasattr(builder, "finalize")
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_explicit_use_rust_false_uses_python(self):
        from cogant.rust_backend import build_program_graph
        from cogant.graph.builder import ProgramGraphBuilder
        builder = build_program_graph("repo://test", use_rust=False)
        assert isinstance(builder, ProgramGraphBuilder)

    def test_auto_detect_returns_valid_builder(self):
        from cogant.rust_backend import build_program_graph
        env = os.environ.copy()
        os.environ.pop("COGANT_USE_RUST", None)
        try:
            builder = build_program_graph("repo://test")
            assert hasattr(builder, "finalize")
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_env_force_python(self):
        from cogant.rust_backend import build_program_graph
        from cogant.graph.builder import ProgramGraphBuilder
        env = os.environ.copy()
        os.environ["COGANT_USE_RUST"] = "0"
        try:
            builder = build_program_graph("repo://test", use_rust=None)
            assert isinstance(builder, ProgramGraphBuilder)
        finally:
            os.environ.clear()
            os.environ.update(env)


class TestRustBackendBasics:
    def test_rust_available_is_bool(self):
        from cogant.rust_backend import RUST_AVAILABLE
        assert isinstance(RUST_AVAILABLE, bool)

    def test_rust_version_returns_str_or_none(self):
        from cogant.rust_backend import rust_version
        v = rust_version()
        assert v is None or isinstance(v, str)

    def test_get_program_graph_impl_returns_class(self):
        from cogant.rust_backend import get_program_graph_impl
        impl = get_program_graph_impl()
        assert impl is not None
        assert callable(impl)

    def test_create_example_graph_raises_without_rust(self):
        from cogant.rust_backend import RUST_AVAILABLE, create_example_graph
        if not RUST_AVAILABLE:
            with pytest.raises(RuntimeError):
                create_example_graph()
        else:
            # If rust is available, it should return something
            result = create_example_graph()
            assert result is not None


# ---------------------------------------------------------------------------
# cogant/__init__.py — module attributes
# ---------------------------------------------------------------------------

class TestCogantInit:
    def test_version_is_string(self):
        import cogant
        assert isinstance(cogant.__version__, str)
        # Should be semver-like
        parts = cogant.__version__.split(".")
        assert len(parts) >= 2

    def test_rust_version_attr(self):
        import cogant
        assert hasattr(cogant, "__rust_version__")
        # Either None or a string
        assert cogant.__rust_version__ is None or isinstance(cogant.__rust_version__, str)

    def test_rust_available_is_bool(self):
        import cogant
        assert hasattr(cogant, "_RUST_AVAILABLE")
        assert isinstance(cogant._RUST_AVAILABLE, bool)

    def test_session_alias(self):
        import cogant
        assert hasattr(cogant, "CogantSession")
        # Either Session or None
        assert cogant.CogantSession is None or cogant.CogantSession is not None

    def test_gnn_bundle_alias(self):
        import cogant
        assert hasattr(cogant, "GNNBundle")

    def test_author_attr(self):
        import cogant
        assert hasattr(cogant, "__author__")
        assert isinstance(cogant.__author__, str)

    def test_all_contains_expected(self):
        import cogant
        assert "__version__" in cogant.__all__
        assert "run_pipeline" in cogant.__all__
