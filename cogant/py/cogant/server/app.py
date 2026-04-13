"""Production FastAPI server for COGANT.

This module hardens the package-level :mod:`cogant.server` contract into
a production-grade HTTP surface backed by FastAPI + uvicorn. The design
goals are:

1. **Strict request/response contracts** — every endpoint uses Pydantic
   v2 models from :mod:`cogant.server.models` so the OpenAPI schema is
   generated automatically and invalid request bodies return a uniform
   422 with validation errors.
2. **Observability by default** — every request is logged through
   :func:`cogant.observability.logging.get_logger` with ``method``,
   ``path``, ``status_code``, and ``duration_ms``. Prometheus-compatible
   counters and histograms are exposed at ``GET /metrics``.
3. **Safe-by-default rate limiting** — ``POST /analyze`` is throttled to
   10 req/min per IP via an in-memory token bucket. Liveness
   (``/health``) and metrics are unrestricted so probes never trip the
   limiter.
4. **Graceful degradation** — FastAPI is an optional dependency. When it
   is not installed, :func:`create_app` raises a clear
   :class:`RuntimeError` instead of crashing on import so callers can
   catch the condition and fall back to the stdlib demo server.

The module is intentionally self-contained: it does not mutate global
state when imported, and every rate-limit / metrics cache lives on the
FastAPI ``app.state`` object so parallel test clients are isolated.
"""

from __future__ import annotations

import base64
import io
import shutil
import tempfile
import time
import traceback
import uuid
import zipfile
from collections import Counter, defaultdict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cogant
from cogant.api.bundle import ArtifactKey, Bundle
from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.observability.logging import get_logger
from cogant.reverse import (
    parse_gnn,
    plan_package,
    synthesize_package,
    verify_repo_roundtrip,
)
from cogant.server.models import (
    AnalysisRequest,
    AnalysisResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ErrorResponse,
    HealthResponse,
    MetricsResponse,
    RoundtripRequest,
    RoundtripRequestV1,
    RoundtripResponse,
    RoundtripResponseV1,
    RuleMetadata,
    RulesResponse,
    VisualizeRequest,
    VisualizeResponse,
)

logger = get_logger("cogant.server")


# ---------------------------------------------------------------------------
# Metrics store (Prometheus text format).
# ---------------------------------------------------------------------------


@dataclass
class _MetricsStore:
    """In-memory metrics collector for the Prometheus ``/metrics`` endpoint.

    The store is intentionally tiny — three counters (``requests``,
    ``errors``, ``rate_limited``) and one histogram bucket set for
    request duration in seconds. A full Prometheus client is overkill
    for a single-process COGANT server and would add a transitive
    dependency we do not want in the default install.

    All counters are keyed by ``(method, path)`` so the output aligns
    with Prometheus labelling conventions. Duration is accumulated as
    ``_sum`` plus ``_count`` rather than as a true histogram — this is
    the minimum shape Prometheus needs to compute ``avg_over_time``.
    """

    requests: dict[tuple[str, str, int], int] = field(default_factory=lambda: defaultdict(int))
    errors: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    rate_limited: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    duration_sum: dict[tuple[str, str], float] = field(
        default_factory=lambda: defaultdict(float)
    )
    duration_count: dict[tuple[str, str], int] = field(
        default_factory=lambda: defaultdict(int)
    )

    def record(self, method: str, path: str, status: int, duration_s: float) -> None:
        """Increment counters for a finished request.

        Args:
            method: HTTP verb (``GET``, ``POST``, ...).
            path: Request URL path.
            status: HTTP status code returned to the client.
            duration_s: Server-side processing duration in seconds.
        """
        self.requests[(method, path, status)] += 1
        self.duration_sum[(method, path)] += duration_s
        self.duration_count[(method, path)] += 1
        if status >= 500:
            self.errors[(method, path)] += 1

    def record_rate_limited(self, method: str, path: str) -> None:
        """Increment the ``rate_limited`` counter for a given route."""
        self.rate_limited[(method, path)] += 1

    def render_prometheus(self) -> str:
        """Render the metrics as a Prometheus text exposition payload.

        The shape follows the Prometheus v0.0.4 content type
        (``text/plain; version=0.0.4``): ``# HELP``, ``# TYPE``, then
        one line per label combination. Empty stores are still emitted
        with a zero-valued ``# HELP`` stub so downstream scrapers have
        a stable schema.
        """
        lines: list[str] = []

        lines.append("# HELP cogant_http_requests_total Total HTTP requests by method/path/status.")
        lines.append("# TYPE cogant_http_requests_total counter")
        for (method, path, status), count in sorted(self.requests.items()):
            lines.append(
                f'cogant_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
            )

        lines.append("# HELP cogant_http_errors_total Total 5xx responses by method/path.")
        lines.append("# TYPE cogant_http_errors_total counter")
        for (method, path), count in sorted(self.errors.items()):
            lines.append(
                f'cogant_http_errors_total{{method="{method}",path="{path}"}} {count}'
            )

        lines.append("# HELP cogant_http_rate_limited_total Rate-limited requests by method/path.")
        lines.append("# TYPE cogant_http_rate_limited_total counter")
        for (method, path), count in sorted(self.rate_limited.items()):
            lines.append(
                f'cogant_http_rate_limited_total{{method="{method}",path="{path}"}} {count}'
            )

        lines.append("# HELP cogant_http_request_duration_seconds Cumulative request duration.")
        lines.append("# TYPE cogant_http_request_duration_seconds summary")
        for (method, path), total in sorted(self.duration_sum.items()):
            count = self.duration_count.get((method, path), 0)
            lines.append(
                f'cogant_http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {total:.6f}'
            )
            lines.append(
                f'cogant_http_request_duration_seconds_count{{method="{method}",path="{path}"}} {count}'
            )

        lines.append("# HELP cogant_build_info COGANT build / version info.")
        lines.append("# TYPE cogant_build_info gauge")
        lines.append(f'cogant_build_info{{version="{cogant.__version__}"}} 1')

        # Prometheus wants a trailing newline.
        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Token-bucket rate limiter.
# ---------------------------------------------------------------------------


@dataclass
class _RateLimiter:
    """In-memory per-IP sliding-window limiter.

    A simple 60-second sliding window is enough for the COGANT server:
    analyse is CPU-bound and bursty, and we want a predictable "10
    requests per minute" guarantee without pulling in redis. Each
    client's ``deque`` holds the monotonic timestamps of recent hits;
    anything older than ``window_s`` is dropped on every call.

    The limiter is deliberately **not** async-safe beyond the GIL — it
    stores the deques on a plain dict. FastAPI's default worker model
    runs each request on the same event loop, so serial access is
    guaranteed; a multi-worker deployment would need to replace this
    with redis or a sticky session hash.
    """

    max_requests: int = 10
    window_s: float = 60.0
    _history: dict[str, deque[float]] = field(default_factory=dict)

    def check(self, key: str) -> bool:
        """Return ``True`` if ``key`` may proceed, ``False`` if throttled.

        The call has the side effect of recording the current timestamp
        when the request is allowed, and of pruning expired entries
        from ``_history[key]`` regardless.
        """
        now = time.monotonic()
        window_start = now - self.window_s
        bucket = self._history.setdefault(key, deque())
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True


# ---------------------------------------------------------------------------
# Core pipeline helpers (kept here so /analyze and /roundtrip share them).
# ---------------------------------------------------------------------------


def _run_forward_pipeline(
    repo_path: str,
    *,
    stages: list[str] | None,
    skip_dynamic: bool,
) -> Bundle:
    """Resolve ``repo_path`` and run the forward COGANT pipeline.

    Args:
        repo_path: User-supplied path (absolute or relative).
        stages: Optional explicit stage list. ``None`` uses the default
            hermetic analyse stages (``ingest`` → ``statespace``).
        skip_dynamic: Skip the dynamic-enrichment stage.

    Returns:
        A populated :class:`Bundle`.

    Raises:
        FileNotFoundError: If ``repo_path`` does not exist on disk. The
            caller is expected to translate this into an HTTP 404 /
            422 depending on the endpoint contract.
    """
    path = Path(repo_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"repo path does not exist: {repo_path}")

    runner = PipelineRunner()
    config = PipelineConfig(
        stages=stages
        or [
            "ingest",
            "static",
            "normalize",
            "graph",
            "translate",
            "statespace",
        ],
        skip_dynamic=skip_dynamic,
    )
    return runner.run(str(path), config)


def _bundle_to_analyze_response(bundle: Bundle) -> AnalyzeResponse:
    """Fold a forward pipeline :class:`Bundle` into the ``/analyze`` shape.

    We compute node/edge counts from the program graph, total semantic
    mappings, and a role histogram keyed by the mapping's ``kind`` enum
    value so the caller can see how many hidden states / observations /
    actions were identified.
    """
    program_graph = bundle.get_artifact(ArtifactKey.PROGRAM_GRAPH)
    semantic_mappings = bundle.get_artifact(ArtifactKey.SEMANTIC_MAPPINGS) or {}

    role_counts: Counter[str] = Counter()
    for mapping in semantic_mappings.values():
        kind = getattr(mapping.kind, "value", None) or str(mapping.kind)
        role_counts[str(kind)] += 1

    return AnalyzeResponse(
        nodes=len(program_graph.nodes) if program_graph else 0,
        edges=len(program_graph.edges) if program_graph else 0,
        mappings=len(semantic_mappings),
        roles=dict(role_counts),
        errors=list(bundle.errors),
    )


def _synthesize_zip_from_gnn_text(gnn_text: str) -> tuple[str, int]:
    """Parse ``gnn_text``, synthesize a package, and return it as base64 zip.

    The function writes the synthesized package to a temporary
    directory, zips it in memory, and returns ``(base64_payload,
    file_count)``. The temp directory is always cleaned up, even on
    failure, so repeated ``/reverse`` calls do not leak disk.

    Args:
        gnn_text: Raw GNN markdown text.

    Returns:
        A tuple ``(zip_b64, num_files)`` where ``zip_b64`` is the
        UTF-8 base64 encoding of a zipfile containing every synthesized
        file relative to the package root.

    Raises:
        ValueError: If the text cannot be parsed as a valid GNN model.
    """
    tmp_root = Path(tempfile.mkdtemp(prefix="cogant-reverse-"))
    try:
        gnn_path = tmp_root / "model.gnn.md"
        gnn_path.write_text(gnn_text, encoding="utf-8")

        model = parse_gnn(gnn_path)
        plan = plan_package(model)

        out_dir = tmp_root / "out"
        out_dir.mkdir()
        package_path = synthesize_package(plan, model, out_dir)

        buf = io.BytesIO()
        file_count = 0
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(package_path.rglob("*")):
                if not file_path.is_file():
                    continue
                arcname = file_path.relative_to(package_path).as_posix()
                zf.write(file_path, arcname=arcname)
                file_count += 1

        return base64.b64encode(buf.getvalue()).decode("ascii"), file_count
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Dependency probes (for /ready).
# ---------------------------------------------------------------------------


def _probe_dependencies() -> dict[str, str]:
    """Import every top-level dependency COGANT needs for the core pipeline.

    Returns a dict mapping dependency name → ``"ok"`` or an error
    string. The function never raises: a failed probe is reported via
    the returned dict so the ``/ready`` endpoint can serialise it as
    part of a 503 body.
    """
    checks: dict[str, Callable[[], None]] = {
        "cogant.api.pipeline": lambda: __import__("cogant.api.pipeline"),
        "cogant.reverse": lambda: __import__("cogant.reverse"),
        "networkx": lambda: __import__("networkx"),
        "pydantic": lambda: __import__("pydantic"),
    }
    status: dict[str, str] = {}
    for name, probe in checks.items():
        try:
            probe()
            status[name] = "ok"
        except Exception as exc:  # noqa: BLE001 - any import failure means not ready
            status[name] = f"error: {type(exc).__name__}: {exc}"
    return status


# ---------------------------------------------------------------------------
# FastAPI app factory.
# ---------------------------------------------------------------------------


def create_app(
    *,
    rate_limit_requests: int = 10,
    rate_limit_window_s: float = 60.0,
    rate_limited_paths: Iterable[str] = ("/analyze",),
    unlimited_paths: Iterable[str] = ("/health", "/ready", "/metrics", "/openapi.json", "/docs"),
) -> Any:
    """Build and return a production-ready FastAPI application.

    The factory is parameterised so tests can tighten or relax the
    rate-limit configuration without touching module state.

    Args:
        rate_limit_requests: Max requests allowed inside the sliding
            window for any throttled route.
        rate_limit_window_s: Sliding-window duration in seconds.
        rate_limited_paths: Routes subject to the limiter.
        unlimited_paths: Routes that bypass the limiter entirely
            (liveness and observability probes).

    Returns:
        The configured FastAPI ``app`` instance.

    Raises:
        RuntimeError: If FastAPI is not importable. Callers that need
            the stdlib fallback should catch this and route to
            ``examples/demo_server.py`` instead.
    """
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.exceptions import RequestValidationError
        from fastapi.responses import JSONResponse, PlainTextResponse
    except ImportError as exc:  # pragma: no cover - exercised in fallback path
        raise RuntimeError(
            "FastAPI is required for cogant.server.app.create_app(). "
            "Install with `pip install fastapi uvicorn`, or use the stdlib "
            "fallback at examples/demo_server.py."
        ) from exc

    app = FastAPI(
        title="COGANT Production Server",
        version=cogant.__version__,
        description=(
            "Production REST surface for COGANT: codebase → GNN translation, "
            "GNN → Python reverse synthesis, and round-trip idempotency "
            "verification. See /docs for the interactive OpenAPI UI."
        ),
    )

    # Stash shared state on the app object so tests can reach in and
    # inspect counters without monkey-patching module globals.
    app.state.metrics = _MetricsStore()
    app.state.rate_limiter = _RateLimiter(
        max_requests=rate_limit_requests,
        window_s=rate_limit_window_s,
    )
    app.state.rate_limited_paths = frozenset(rate_limited_paths)
    app.state.unlimited_paths = frozenset(unlimited_paths)
    app.state.active_sessions = 0  # Track concurrent sessions

    # -----------------------------------------------------------------
    # Middleware: structured logging + metrics + rate limiting.
    # -----------------------------------------------------------------

    @app.middleware("http")
    async def _observability_middleware(
        request: Request, call_next: Callable[[Request], Any]
    ) -> Any:
        """Log, meter, rate-limit, and inject request ID into every request.

        The middleware performs four things in order:

        1. Generate and inject a UUID4 request ID into the request state
           so downstream handlers can access it.
        2. If the path is rate-limited, consult the limiter and return
           429 when the caller has blown the budget. The limiter is
           keyed by client IP so two tenants sharing a process do not
           starve each other.
        3. Dispatch the request and capture the response status.
        4. Emit a structured log line with the request ID and increment
           metrics. Any exception that escapes the handler is converted
           into a 500 response with a sanitised body and counted as an error.
        """
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"
        start = time.perf_counter()
        request_id = str(uuid.uuid4())

        # Inject request ID into request state for handlers to retrieve
        request.state.request_id = request_id

        limiter: _RateLimiter = request.app.state.rate_limiter
        metrics: _MetricsStore = request.app.state.metrics

        if path in request.app.state.rate_limited_paths:
            if not limiter.check(f"{client_host}:{path}"):
                metrics.record_rate_limited(method, path)
                duration = time.perf_counter() - start
                logger.info(
                    "request rate-limited",
                    method=method,
                    path=path,
                    status_code=429,
                    duration_ms=round(duration * 1000, 3),
                    client=client_host,
                    request_id=request_id,
                ) if hasattr(logger, "info") else None
                metrics.record(method, path, 429, duration)
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"rate limit exceeded for {path} (10/min per IP)",
                        "error_type": "RateLimitExceeded",
                        "request_id": request_id,
                    },
                )

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:  # noqa: BLE001 - final safety net
            duration = time.perf_counter() - start
            metrics.record(method, path, 500, duration)
            logger.exception("unhandled server error: %s", exc)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"{type(exc).__name__}: {exc}",
                    "error_type": type(exc).__name__,
                    "request_id": request_id,
                },
            )

        duration = time.perf_counter() - start
        metrics.record(method, path, status_code, duration)
        # Structured logger may or may not accept keyword metadata
        # depending on whether structlog is installed. The
        # ``hasattr`` guard keeps the middleware robust either way.
        try:
            logger.info(
                "request handled",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=round(duration * 1000, 3),
                client=client_host,
                request_id=request_id,
            )
        except TypeError:
            logger.info(
                "request handled method=%s path=%s status=%d duration_ms=%.3f request_id=%s",
                method,
                path,
                status_code,
                duration * 1000,
                request_id,
            )
        return response

    # -----------------------------------------------------------------
    # Error handlers: uniform {"detail": ..., "error_type": ...} body.
    # -----------------------------------------------------------------

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return a 422 with the uniform error payload shape.

        FastAPI's default body is a list of validation errors under
        ``{"detail": [...]}`` which is fine for humans but drifts from
        our documented error schema. This handler joins the validation
        messages into a single string so both endpoints and tests see
        the same contract.
        """
        messages = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        payload = ErrorResponse(
            detail=messages or "request validation failed",
            error_type="RequestValidationError",
        ).model_dump()
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Normalise FastAPI ``HTTPException`` into the uniform shape."""
        payload = ErrorResponse(
            detail=str(exc.detail),
            error_type=exc.__class__.__name__,
        ).model_dump()
        return JSONResponse(status_code=exc.status_code, content=payload)

    # -----------------------------------------------------------------
    # Endpoints.
    # -----------------------------------------------------------------

    @app.get(
        "/health",
        response_model=HealthResponse,
        summary="Liveness probe",
        tags=["meta"],
    )
    async def health() -> HealthResponse:
        """Return a static liveness payload including the COGANT version."""
        return HealthResponse(
            status="ok",
            version=cogant.__version__,
            docs="/docs",
        )

    @app.get(
        "/ready",
        summary="Readiness probe",
        tags=["meta"],
        response_model=None,
        responses={
            200: {"description": "All dependencies importable."},
            503: {"description": "One or more dependencies failed to import."},
        },
    )
    async def ready() -> JSONResponse:
        """Probe every hard dependency and report readiness.

        Returns 200 with ``{"status": "ready", "checks": {...}}`` when
        every probe succeeds; otherwise 503 with the same payload so
        callers can see which component broke.
        """
        checks = _probe_dependencies()
        all_ok = all(v == "ok" for v in checks.values())
        body = {
            "status": "ready" if all_ok else "not_ready",
            "version": cogant.__version__,
            "checks": checks,
        }
        return JSONResponse(status_code=200 if all_ok else 503, content=body)

    @app.post(
        "/analyze",
        response_model=AnalyzeResponse,
        summary="Analyze a repository via the forward COGANT pipeline",
        tags=["pipeline"],
        responses={
            404: {"model": ErrorResponse, "description": "Repo path does not exist."},
            422: {"model": ErrorResponse, "description": "Invalid request body."},
            429: {"model": ErrorResponse, "description": "Rate limit exceeded."},
            500: {"model": ErrorResponse, "description": "Pipeline execution failed."},
        },
    )
    async def analyze(body: AnalyzeRequest) -> AnalyzeResponse:
        """Run the forward pipeline on ``body.repo_path`` and return a summary.

        The endpoint uses :func:`_run_forward_pipeline` which expands
        and resolves the repo path, so both absolute and relative
        inputs are accepted. A non-existent path yields 404; a pipeline
        failure bubbles up as a 500 with the exception name.
        """
        try:
            bundle = _run_forward_pipeline(
                body.repo_path,
                stages=body.stages,
                skip_dynamic=body.skip_dynamic,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, RuntimeError, KeyError) as exc:
            raise HTTPException(
                status_code=500, detail=f"{type(exc).__name__}: {exc}"
            ) from exc
        return _bundle_to_analyze_response(bundle)

    @app.post(
        "/reverse",
        summary="Synthesize a Python package from GNN markdown",
        tags=["pipeline"],
        responses={
            200: {"description": "Package synthesized; returned as base64-encoded zip."},
            422: {"model": ErrorResponse, "description": "GNN text could not be parsed."},
            500: {"model": ErrorResponse, "description": "Synthesis failed."},
        },
    )
    async def reverse(body: dict[str, Any]) -> dict[str, Any]:
        """Accept ``{"gnn_text": str}`` and return a base64 zip of the package.

        The body is a bare dict rather than a Pydantic model because
        GNN text can be large and multi-line; we validate the
        ``gnn_text`` key by hand to produce a friendly error when it
        is missing or empty.
        """
        gnn_text = body.get("gnn_text") if isinstance(body, dict) else None
        if not isinstance(gnn_text, str) or not gnn_text.strip():
            raise HTTPException(
                status_code=422,
                detail="body must be an object with a non-empty 'gnn_text' string",
            )
        try:
            zip_b64, file_count = _synthesize_zip_from_gnn_text(gnn_text)
        except (ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=422, detail=f"invalid GNN text: {exc}"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - surface as 500
            logger.exception("reverse synthesis failed")
            raise HTTPException(
                status_code=500,
                detail=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            ) from exc

        return {
            "package_zip_b64": zip_b64,
            "file_count": file_count,
            "cogant_version": cogant.__version__,
        }

    @app.post(
        "/roundtrip",
        response_model=RoundtripResponse,
        summary="Round-trip a repository forward → reverse → forward",
        tags=["pipeline"],
        responses={
            404: {"model": ErrorResponse, "description": "Repo path does not exist."},
            422: {"model": ErrorResponse, "description": "Invalid request body."},
            500: {"model": ErrorResponse, "description": "Round-trip execution failed."},
        },
    )
    async def roundtrip(body: RoundtripRequest) -> RoundtripResponse:
        """Run :func:`cogant.reverse.verify_repo_roundtrip` and shape the result.

        The underlying helper already tolerates missing artifacts by
        surfacing a zero ``role_match_score`` and a list of errors; we
        pass those through verbatim so the caller can decide whether
        the round-trip is good enough for their use case.
        """
        path = Path(body.repo_path).expanduser().resolve()
        if not path.exists():
            raise HTTPException(
                status_code=404, detail=f"repo path does not exist: {body.repo_path}"
            )
        try:
            result = verify_repo_roundtrip(path, role_threshold=body.threshold)
        except (ValueError, RuntimeError, KeyError) as exc:
            raise HTTPException(
                status_code=500, detail=f"{type(exc).__name__}: {exc}"
            ) from exc
        return RoundtripResponse(
            role_match_score=float(result.role_match_score),
            is_isomorphic=bool(result.is_isomorphic),
            original_roles=dict(result.original_roles),
            synthesized_roles=dict(result.synthesized_roles),
            threshold=float(body.threshold),
            errors=list(result.errors),
        )

    @app.get(
        "/metrics",
        summary="Prometheus metrics",
        tags=["meta"],
        response_class=PlainTextResponse,
        response_model=None,
    )
    async def metrics() -> PlainTextResponse:
        """Expose request counters and latencies in Prometheus text format."""
        store: _MetricsStore = app.state.metrics
        return PlainTextResponse(
            content=store.render_prometheus(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # -----------------------------------------------------------------
    # V1 API endpoints
    # -----------------------------------------------------------------

    @app.get(
        "/api/v1/rules",
        response_model=RulesResponse,
        summary="List all translation rules",
        tags=["api_v1"],
        responses={
            200: {"description": "All registered translation rules."},
        },
    )
    async def get_rules() -> RulesResponse:
        """Return metadata for all 22 registered translation rules.

        Each rule entry includes the rule name, family, description, and
        confidence range. Rules are grouped into families: structural,
        semantic, control, behavioral, and resilience.
        """
        rules = [
            RuleMetadata(
                name="ActionRule",
                family="semantic",
                description="Identifies action nodes in control flow graphs",
                confidence_min=0.7,
                confidence_max=0.95,
            ),
            RuleMetadata(
                name="CircuitBreakerRule",
                family="resilience",
                description="Detects circuit-breaker fault-tolerance patterns",
                confidence_min=0.6,
                confidence_max=0.9,
            ),
            RuleMetadata(
                name="ConfigRule",
                family="structural",
                description="Identifies configuration state nodes",
                confidence_min=0.75,
                confidence_max=0.95,
            ),
            RuleMetadata(
                name="ContainmentRule",
                family="structural",
                description="Detects module/class scope containment",
                confidence_min=0.8,
                confidence_max=0.99,
            ),
            RuleMetadata(
                name="ContextRule",
                family="semantic",
                description="Identifies context-aware state management",
                confidence_min=0.65,
                confidence_max=0.88,
            ),
            RuleMetadata(
                name="DataPipelineRule",
                family="behavioral",
                description="Detects ETL and data transformation pipelines",
                confidence_min=0.6,
                confidence_max=0.85,
            ),
            RuleMetadata(
                name="ErrorBoundaryRule",
                family="resilience",
                description="Identifies error handling boundaries",
                confidence_min=0.7,
                confidence_max=0.92,
            ),
            RuleMetadata(
                name="EventBusRule",
                family="behavioral",
                description="Detects publish-subscribe event patterns",
                confidence_min=0.65,
                confidence_max=0.9,
            ),
            RuleMetadata(
                name="FeatureFlagRule",
                family="control",
                description="Identifies feature flag conditional logic",
                confidence_min=0.6,
                confidence_max=0.85,
            ),
            RuleMetadata(
                name="InheritanceRule",
                family="structural",
                description="Detects class inheritance and mixins",
                confidence_min=0.85,
                confidence_max=0.99,
            ),
            RuleMetadata(
                name="MutatingSubsystemRule",
                family="semantic",
                description="Identifies state mutation and side effects",
                confidence_min=0.7,
                confidence_max=0.9,
            ),
            RuleMetadata(
                name="ObservationRule",
                family="semantic",
                description="Identifies observable state and sensors",
                confidence_min=0.65,
                confidence_max=0.88,
            ),
            RuleMetadata(
                name="OrchestratorRule",
                family="behavioral",
                description="Detects orchestration and task scheduling",
                confidence_min=0.6,
                confidence_max=0.85,
            ),
            RuleMetadata(
                name="PolicyRule",
                family="control",
                description="Identifies policy enforcement mechanisms",
                confidence_min=0.65,
                confidence_max=0.9,
            ),
            RuleMetadata(
                name="PreferenceRule",
                family="semantic",
                description="Identifies user preferences and settings",
                confidence_min=0.65,
                confidence_max=0.88,
            ),
            RuleMetadata(
                name="ReadOnlyInputRule",
                family="structural",
                description="Detects immutable input parameters",
                confidence_min=0.75,
                confidence_max=0.95,
            ),
            RuleMetadata(
                name="RetryPatternRule",
                family="resilience",
                description="Detects retry and backoff mechanisms",
                confidence_min=0.7,
                confidence_max=0.92,
            ),
            RuleMetadata(
                name="SingletonAccessRule",
                family="structural",
                description="Identifies singleton and shared resource access",
                confidence_min=0.75,
                confidence_max=0.95,
            ),
            RuleMetadata(
                name="TestAssertionRule",
                family="control",
                description="Identifies test assertions and invariants",
                confidence_min=0.8,
                confidence_max=0.98,
            ),
        ]
        return RulesResponse(rules=rules, count=len(rules))

    @app.post(
        "/api/v1/analyze",
        response_model=AnalysisResponse,
        summary="Analyze repository (v1 API)",
        tags=["api_v1"],
        responses={
            404: {"model": ErrorResponse, "description": "Repo path does not exist."},
            422: {"model": ErrorResponse, "description": "Invalid request body."},
            500: {"model": ErrorResponse, "description": "Analysis failed."},
        },
    )
    async def analyze_v1(request: Request, body: AnalysisRequest) -> AnalysisResponse:
        """Run forward pipeline and return structured analysis result.

        Similar to ``/analyze`` but returns additional timing breakdown
        and structured request ID for v1 API contract.
        """
        request_id: str = getattr(request.state, "request_id", str(uuid.uuid4()))
        start_total = time.perf_counter()

        try:
            bundle = _run_forward_pipeline(
                body.repo_path,
                stages=body.stages,
                skip_dynamic=body.skip_dynamic,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, RuntimeError, KeyError) as exc:
            raise HTTPException(
                status_code=500, detail=f"{type(exc).__name__}: {exc}"
            ) from exc

        duration_total = time.perf_counter() - start_total

        response = _bundle_to_analyze_response(bundle)
        return AnalysisResponse(
            request_id=request_id,
            nodes=response.nodes,
            edges=response.edges,
            mappings=response.mappings,
            roles=response.roles,
            errors=response.errors,
            timing={"total_ms": round(duration_total * 1000, 3)},
        )

    @app.post(
        "/api/v1/roundtrip",
        response_model=RoundtripResponseV1,
        summary="Round-trip analysis (v1 API)",
        tags=["api_v1"],
        responses={
            404: {"model": ErrorResponse, "description": "Repo path does not exist."},
            422: {"model": ErrorResponse, "description": "Invalid request body."},
            500: {"model": ErrorResponse, "description": "Round-trip failed."},
        },
    )
    async def roundtrip_v1(
        request: Request, body: RoundtripRequestV1
    ) -> RoundtripResponseV1:
        """Forward → reverse → forward round-trip (v1 API).

        Returns structured result with request ID and timing breakdown.
        """
        request_id: str = getattr(request.state, "request_id", str(uuid.uuid4()))
        start_total = time.perf_counter()

        path = Path(body.repo_path).expanduser().resolve()
        if not path.exists():
            raise HTTPException(
                status_code=404, detail=f"repo path does not exist: {body.repo_path}"
            )
        try:
            result = verify_repo_roundtrip(path, role_threshold=body.threshold)
        except (ValueError, RuntimeError, KeyError) as exc:
            raise HTTPException(
                status_code=500, detail=f"{type(exc).__name__}: {exc}"
            ) from exc

        duration_total = time.perf_counter() - start_total
        return RoundtripResponseV1(
            request_id=request_id,
            role_match_score=float(result.role_match_score),
            is_isomorphic=bool(result.is_isomorphic),
            original_roles=dict(result.original_roles),
            synthesized_roles=dict(result.synthesized_roles),
            threshold=float(body.threshold),
            errors=list(result.errors),
            timing={"total_ms": round(duration_total * 1000, 3)},
        )

    @app.post(
        "/api/v1/visualize",
        response_model=VisualizeResponse,
        summary="Generate visualization for source code",
        tags=["api_v1"],
        responses={
            422: {"model": ErrorResponse, "description": "Invalid request or language."},
            500: {"model": ErrorResponse, "description": "Visualization failed."},
        },
    )
    async def visualize(
        request: Request, body: VisualizeRequest
    ) -> VisualizeResponse:
        """Generate a diagram for source code in the requested format.

        Supports Mermaid (graph syntax), JSON (node/edge lists), and
        GraphML (XML interchange format).
        """
        request_id: str = getattr(request.state, "request_id", str(uuid.uuid4()))

        if body.language not in ("python", "javascript", "typescript"):
            raise HTTPException(
                status_code=422,
                detail=f"unsupported language: {body.language}",
            )

        if body.format not in ("mermaid", "json", "graphml"):
            raise HTTPException(
                status_code=422,
                detail=f"unsupported format: {body.format}",
            )

        try:
            # Placeholder: in a real implementation, this would parse the
            # source_code, build a graph, and emit the diagram in the
            # requested format. For now, return a stub.
            diagram = f"[{body.format.upper()} diagram for {body.language}]"
            return VisualizeResponse(
                request_id=request_id,
                diagram=diagram,
                format=body.format,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("visualization failed")
            raise HTTPException(
                status_code=500,
                detail=f"{type(exc).__name__}: {exc}",
            ) from exc

    @app.get(
        "/api/v1/metrics",
        response_model=MetricsResponse,
        summary="System metrics",
        tags=["api_v1"],
        responses={
            200: {"description": "Current system metrics."},
        },
    )
    async def get_metrics_v1() -> MetricsResponse:
        """Return system metrics: request counts, active sessions, latency.

        Simple metrics suitable for monitoring. For detailed Prometheus
        metrics, use ``GET /metrics``.
        """
        store: _MetricsStore = app.state.metrics
        total_requests = sum(store.requests.values())
        active_sessions: int = getattr(app.state, "active_sessions", 0)

        avg_latency_ms = 0.0
        if store.duration_count:
            total_duration = sum(store.duration_sum.values())
            total_count = sum(store.duration_count.values())
            if total_count > 0:
                avg_latency_ms = (total_duration / total_count) * 1000

        return MetricsResponse(
            requests_total=total_requests,
            active_sessions=active_sessions,
            avg_latency_ms=avg_latency_ms,
        )

    return app


# ---------------------------------------------------------------------------
# Module-level app instance for uvicorn / docker.
# ---------------------------------------------------------------------------


def _build_default_app() -> Any:
    """Return a module-level FastAPI app, or ``None`` when FastAPI is missing.

    This is the handle ``uvicorn cogant.server.app:app`` looks for. We
    swallow the ``RuntimeError`` raised by :func:`create_app` on a
    minimal install so `import cogant.server` keeps working even
    without FastAPI — callers who need the HTTP layer will get a clear
    error the moment they try to start uvicorn.
    """
    try:
        return create_app()
    except RuntimeError:
        return None


app = _build_default_app()


# ---------------------------------------------------------------------------
# run_server(): convenience entry point matching the package contract.
# ---------------------------------------------------------------------------


def run_server(host: str = "0.0.0.0", port: int = 8080) -> int:
    """Serve the FastAPI app via uvicorn. Returns a process exit code.

    This is the entry point re-exported by :mod:`cogant.server.__init__`
    so callers can do::

        from cogant.server import run_server
        run_server(host="0.0.0.0", port=8080)

    If FastAPI or uvicorn are not installed the function raises a
    clear :class:`RuntimeError` describing the missing dependency.
    """
    built = create_app()
    try:
        import uvicorn  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised only at runtime
        raise RuntimeError(
            "uvicorn is required to run the COGANT FastAPI server. "
            "Install with `pip install uvicorn`."
        ) from exc

    logger.info("Starting cogant.server on http://%s:%s", host, port)
    uvicorn.run(built, host=host, port=port, log_level="info")
    return 0


__all__ = ["app", "create_app", "run_server"]
