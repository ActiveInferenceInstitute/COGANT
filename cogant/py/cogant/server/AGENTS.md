# Agents — py/cogant/server

## Owner
Runtime Lead

## What Is the Server Module

The `server/` module provides **HTTP/REST API access** to COGANT. It wraps the entire pipeline (stages 1-10) behind REST endpoints with strict request/response contracts, rate limiting, observability (logging, metrics), and graceful fallback when dependencies unavailable.

Primary backend: FastAPI + uvicorn (production-grade, OpenAPI docs auto-generated)
Fallback: stdlib `http.server` (for testing in minimal environments; same contract)

## Pipeline Integration

```
REST client
    ↓
GET /health          → HealthResponse
POST /analyze        → PipelineRunner → ProgramGraph → AnalyzeResponse
GET /api/v1/rules    → RulesMetadata → RulesResponse
POST /api/v1/roundtrip → reverse synthesis → RoundtripResponse
POST /api/v1/visualize → PNG/PDF/Mermaid → VisualizeResponse
GET /metrics         → Prometheus text format
```

The server **stateless**: each request is independent. No request context persists across calls.

## Endpoints

### Liveness & Observability

**GET /health**
- Liveness probe for load balancers/Kubernetes
- Response: `HealthResponse` with version and docs URL
- No rate limiting; always instant

**GET /metrics**
- Prometheus-compatible metrics (text format)
- Counters: requests (by method/path/status), errors, rate_limited
- Histogram: request duration (sum + count for avg calculation)
- No rate limiting; always instant

### Analysis Endpoints

**POST /analyze** (primary)
- Run full pipeline: ingest → static → normalize → graph → translate → statespace → export → validate
- Request: `AnalyzeRequest` (repo_path, optional stages, skip_dynamic)
- Response: `AnalyzeResponse` (nodes, edges, mappings, roles, errors)
- Rate limited: 10 req/min per IP (token bucket)

**GET /api/v1/rules**
- List all 22 translation rules with metadata
- Response: `RulesResponse` (rules: list[RuleMetadata])
- No rate limiting

**POST /api/v1/analyze** (alternative, same as /analyze)
- Same as `POST /analyze` but versioned endpoint
- For API versioning / client compatibility

### Semantic & Synthesis Endpoints

**POST /api/v1/roundtrip** (reverse synthesis)
- Roundtrip test: forward-reverse-forward
- Request: `RoundtripRequest` (repo_path, forward_only: bool)
- Response: `RoundtripResponse` (isomorphic: bool, forward_nodes, reverse_nodes, re_forward_nodes, metrics)
- Validates that synthesis can reconstruct original graph
- Rate limited: 5 req/min per IP

**POST /api/v1/roundtrip/v1** (deprecated)
- Legacy roundtrip endpoint (v0.4.x compatibility)
- Request: `RoundtripRequestV1`
- Response: `RoundtripResponseV1`
- Maintained for backward compatibility

### Visualization Endpoints

**POST /api/v1/visualize** (experimental)
- Generate visualization from graph/mappings
- Request: `VisualizeRequest` (graph_json, format: 'png'|'pdf'|'mermaid'|'svg', options)
- Response: `VisualizeResponse` (data: base64-encoded PNG/PDF, or mermaid/svg text)
- Requires matplotlib (PNG/PDF) or graphviz (SVG)
- Rate limited: 10 req/min per IP

## Request/Response Models

All models are **Pydantic v2** (dataclass-like with validation). Generated OpenAPI docs at `/docs` (FastAPI only).

```python
# ---- /analyze ----
@dataclass
class AnalyzeRequest:
    repo_path: str  # Required
    stages: list[str] | None  # Optional; defaults to full pipeline
    skip_dynamic: bool  # Default: True (dynamic analysis skipped)

@dataclass
class AnalyzeResponse:
    nodes: int  # >= 0
    edges: int  # >= 0
    mappings: int  # >= 0
    roles: dict[str, int]  # e.g., {"HIDDEN_STATE": 15, "OBSERVATION": 8, ...}
    errors: list[str]  # Non-fatal warnings

# ---- /health ----
@dataclass
class HealthResponse:
    status: str  # Always "ok"
    version: str  # COGANT version
    docs: str  # "/docs" (FastAPI) or "FastAPI not available" (stdlib)

# ---- /metrics ----
@dataclass
class MetricsResponse:
    """Prometheus text format string."""
    data: str  # Multiline Prometheus format

# ---- /api/v1/rules ----
@dataclass
class RuleMetadata:
    name: str
    family: str  # 'structural' | 'semantic' | 'control' | 'behavioral' | 'resilience'
    description: str
    conditions: list[str]
    actions: list[str]
    confidence: float  # [0.0, 1.0]

@dataclass
class RulesResponse:
    rules: list[RuleMetadata]
    count: int

# ---- /api/v1/roundtrip ----
@dataclass
class RoundtripRequest:
    repo_path: str
    forward_only: bool  # If True, skip synthesis step

@dataclass
class RoundtripResponse:
    isomorphic: bool  # True if forward/reverse/forward are equal
    forward_node_count: int
    reverse_node_count: int
    re_forward_node_count: int
    metrics: dict[str, Any]  # e.g., {"synthesis_time_ms": 150, ...}
    errors: list[str]

# ---- /api/v1/visualize ----
@dataclass
class VisualizeRequest:
    graph_json: str  # Serialized ProgramGraph (JSON)
    format: str  # 'png' | 'pdf' | 'mermaid' | 'svg'
    options: dict[str, Any]  # e.g., {"dpi": 150, "width": 1200}

@dataclass
class VisualizeResponse:
    format: str
    data: str  # Base64-encoded (PNG/PDF) or plain text (Mermaid/SVG)
    size_bytes: int
    metadata: dict[str, Any]  # e.g., {"generated_at": "...", "render_time_ms": 250}
```

## Core Components

### Files

**app.py** — `create_app`, `run_server`
- Builds FastAPI application with all routes
- Registers middleware: logging, rate limiting, error handling, metrics
- Methods:
  - `create_app(enable_rate_limit: bool = True) -> FastAPI` — builds app
  - `run_server(host: str = "127.0.0.1", port: int = 8080, use_uvicorn: bool = True) -> None` — starts server
  - All route handlers (POST /analyze, GET /health, etc.)

**models.py** — Pydantic models
- All request/response dataclasses
- Validation rules via Pydantic Field constraints
- Serialization/deserialization via `model_dump()`, `model_dump_json()`

**__init__.py** — public exports
- `create_app`, `run_server` only

### Middleware & Features

**Logging**
- All requests logged: method, path, status, duration_ms
- All errors logged with traceback
- Uses `cogant.observability.logging.get_logger()`

**Rate Limiting**
- Token bucket algorithm, in-memory
- POST /analyze: 10 req/min per IP
- POST /api/v1/roundtrip: 5 req/min per IP
- POST /api/v1/visualize: 10 req/min per IP
- GET /health, GET /metrics, GET /api/v1/rules: unrestricted
- Returns HTTP 429 when limit exceeded

**Error Handling**
- Request validation errors (422 Unprocessable Entity)
- Caught exceptions → 500 Internal Server Error
- All errors returned as JSON with error message + request_id

**Metrics**
- In-memory Prometheus-compatible metrics
- Counters: requests_total, errors_total, rate_limited_total
- Histogram: request_duration_seconds (sum + count)
- Exposed at GET /metrics in Prometheus text format

**OpenAPI Documentation**
- FastAPI auto-generates at GET /docs (Swagger UI)
- Auto-generated from Pydantic models
- Including request/response schemas, examples, validation rules

## Common Usage Patterns

### Run the Server (Development)

```bash
# Using FastAPI + uvicorn (preferred)
python -m cogant.server

# Or programmatically
from cogant.server import run_server
run_server(host="0.0.0.0", port=8080)
```

### Analyze via REST

```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/path/to/repo",
    "skip_dynamic": true
  }'

# Response:
# {"nodes": 156, "edges": 289, "mappings": 45, "roles": {"HIDDEN_STATE": 20, ...}, "errors": []}
```

### Get API Documentation

```bash
# Open in browser
http://localhost:8080/docs

# Or get OpenAPI schema as JSON
curl http://localhost:8080/openapi.json
```

### List All Translation Rules

```bash
curl http://localhost:8080/api/v1/rules

# Response:
# {
#   "count": 22,
#   "rules": [
#     {
#       "name": "StateVariableToHiddenState",
#       "family": "semantic",
#       "description": "...",
#       "confidence": 0.95,
#       ...
#     },
#     ...
#   ]
# }
```

### Roundtrip Verification

```bash
curl -X POST http://localhost:8080/api/v1/roundtrip \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/path/to/repo",
    "forward_only": false
  }'

# Response:
# {
#   "isomorphic": true,
#   "forward_node_count": 156,
#   "reverse_node_count": 156,
#   "re_forward_node_count": 156,
#   "metrics": {"synthesis_time_ms": 250, ...},
#   "errors": []
# }
```

### Generate Visualization

```bash
# First serialize the graph
graph_json=$(curl -s http://localhost:8080/analyze -X POST ... | jq -r '.graph_json')

# Then visualize
curl -X POST http://localhost:8080/api/v1/visualize \
  -H "Content-Type: application/json" \
  -d "{
    \"graph_json\": \"$graph_json\",
    \"format\": \"png\",
    \"options\": {\"dpi\": 150}
  }" \
  | jq -r '.data' | base64 -d > graph.png
```

### Monitor Metrics (Prometheus)

```bash
curl http://localhost:8080/metrics

# Output (text format):
# # HELP cogant_requests_total Total requests
# # TYPE cogant_requests_total counter
# cogant_requests_total{method="POST",path="/analyze",status="200"} 42
# cogant_requests_total{method="GET",path="/health",status="200"} 1000
# cogant_errors_total{method="POST",path="/analyze"} 2
# cogant_rate_limited_total{method="POST",path="/analyze"} 0
# cogant_request_duration_seconds_sum{method="POST",path="/analyze"} 125.5
# cogant_request_duration_seconds_count{method="POST",path="/analyze"} 42
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
RUN pip install cogant

EXPOSE 8080

CMD ["python", "-m", "cogant.server"]
```

```bash
docker build -t cogant-server .
docker run -p 8080:8080 -v /path/to/repo:/repo cogant-server
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cogant-server
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: cogant
        image: cogant-server:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 2
          periodSeconds: 5
```

### Reverse Proxy (Nginx)

```nginx
upstream cogant {
  server localhost:8080;
  server localhost:8081;
  server localhost:8082;
}

server {
  listen 80;
  server_name api.example.com;

  location / {
    proxy_pass http://cogant;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 60s;
  }
}
```

## Responsibilities & Coordination

### Core Responsibilities
- Expose COGANT pipeline via REST API with strict contracts
- Validate requests (Pydantic models)
- Run pipeline stages on demand
- Rate limit to prevent resource exhaustion
- Log all requests and errors for observability
- Generate Prometheus-compatible metrics
- Auto-document API via OpenAPI/Swagger
- Graceful fallback when FastAPI unavailable

### Input Sources
- HTTP clients: users, CI/CD systems, dashboards
- Local filesystem: repositories to analyze

### Output Sinks
- HTTP responses: JSON (AnalyzeResponse, etc.), Prometheus metrics, OpenAPI schema
- Logs: request lifecycle, errors, durations
- Metrics endpoint: Prometheus scraping

### Guarantees
- **Stateless**: each request is independent
- **Deterministic**: same request → same response (same pipeline run)
- **Rate limited**: protects against DoS
- **Observable**: all requests logged + metricated
- **Validated**: Pydantic models ensure valid requests only
- **Documented**: OpenAPI + human-readable /docs

## How to Extend

### Add a New Endpoint

1. Define request/response models in `models.py`
```python
@dataclass
class MyRequest(BaseModel):
    param1: str
    param2: int | None = None

@dataclass
class MyResponse(BaseModel):
    result: str
    status: str
```

2. Add route handler in `app.py`
```python
@app.post("/api/v1/my-endpoint")
async def my_endpoint(request: MyRequest) -> MyResponse:
    # Implementation
    return MyResponse(result="...", status="ok")
```

3. Wire into `create_app()` (automatic if using @app decorator)

### Add Custom Rate Limiting Per Endpoint

1. Extend `_MetricsStore` with per-endpoint limit config
2. Add rate limit check in middleware
3. Test with concurrent requests

### Add Authentication

1. Add Bearer token validation in middleware
2. Extract user/org from token
3. Add to request context
4. Use in handlers for authorization

### Add Caching

1. Cache expensive operations (graph building, visualization)
2. Key: request hash (repo_path + stages + skip_dynamic)
3. TTL: configurable (e.g., 5 minutes)
4. Invalidate on filesystem changes (optional)

## Performance Notes

- **/analyze on small repo** (~50 nodes): 100-500ms
- **/analyze on medium repo** (~1000 nodes): 1-5s
- **/analyze on large repo** (~10k+ nodes): 10-60s
- **/metrics**: < 1ms (already computed)
- **/health**: < 1ms
- Rate limit checks: < 1ms per request

## See Also

- `py/cogant/server/README.md` — module overview
- `py/cogant/api/pipeline.py` — PipelineRunner (core execution)
- `py/cogant/reverse/` — roundtrip synthesis
- `examples/demo_server.py` — standalone demo server (simpler, for learning)
