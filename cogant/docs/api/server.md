# FastAPI Server Reference

> **What this page is:** Complete reference for COGANT's FastAPI application (`cogant.server.app`) and all 12 exposed HTTP routes.
>
> **Prerequisites:** [Installation](installation.md) and familiarity with the [analysis pipeline](overview.md).
>
> **Reading time:** ~10 minutes
>
> **Next steps:** [Complete Example](complete_example.md) · [API Stability](api_stability.md) · [Performance Tips](performance_tips.md)

## Overview

`cogant.server.app` exposes a FastAPI application for analyzing codebases and operating the reverse pipeline via HTTP. The server provides JSON endpoints for translation, reverse synthesis, roundtrip validation, and metrics retrieval. It is packaged as a Docker container (`cogant/Dockerfile`) and can be started via `docker-compose.yml` or directly from Python.

## Routes

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| GET | `/health` | Service health check | none | `{"status": "ok", "version": "..."}` |
| GET | `/ready` | Readiness probe with dependency checks | none | `{"ready": bool, "checks": {...}}` |
| GET | `/metrics` | Prometheus-format text metrics | none | Plain text (Prometheus format) |
| POST | `/analyze` | Full translation pipeline | `{"repo_path": str, "config"?: {...}}` | GNN bundle JSON |
| POST | `/reverse` | GNN-to-code synthesis | `{"gnn_markdown": str}` | `{"package_plan": {...}, "synthesized_files": [...]}` |
| POST | `/roundtrip` | Forward-then-reverse validation | `{"repo_path": str}` | `{"isomorphism_score": float, "result": str}` |
| GET | `/api/v1/rules` | List all active translation rules | none | `[{"name": str, "family": str, "priority": int}, ...]` |
| POST | `/api/v1/analyze` | Alias for `/analyze` | `{"repo_path": str, "config"?: {...}}` | GNN bundle JSON |
| POST | `/api/v1/roundtrip` | Alias for `/roundtrip` | `{"repo_path": str}` | `{"isomorphism_score": float, "result": str}` |
| POST | `/api/v1/visualize` | Generate graph visualizations | `{"gnn_bundle": {...}}` | `{"svg": str, "mermaid": str}` |
| GET | `/api/v1/metrics` | Structured JSON metrics | none | `{"rule_counts": {...}, "graph_size": {...}, ...}` |
| GET | `/gnn_text` | (Internal) streaming GNN text export | Query params: `bundle_id`, `format` | Streaming NdJSON lines |

## Request/Response Details

### POST /analyze

**Request:**
```json
{
  "repo_path": "/path/to/repo",
  "config": {
    "output_dir": "output/",
    "no_dynamic": false,
    "min_confidence": 0.4,
    "markov_seed": "auto"
  }
}
```

**Response:** Full GNN bundle as JSON (same format as `cogant translate --output`).

### POST /reverse

**Request:**
```json
{
  "gnn_markdown": "# GNN\n[HIDDEN_STATE x]\n..."
}
```

**Response:**
```json
{
  "package_plan": {
    "modules": [...],
    "hidden_states": [...],
    "observations": [...],
    "actions": [...]
  },
  "synthesized_files": [
    {"path": "src/agent.py", "content": "..."},
    {"path": "src/state.py", "content": "..."}
  ]
}
```

### GET /api/v1/rules

**Response:**
```json
[
  {"name": "MutatingSubsystemRule", "family": "semantic", "priority": 10},
  {"name": "ActionRule", "family": "semantic", "priority": 15},
  ...
]
```

### POST /api/v1/visualize

**Request:**
```json
{
  "gnn_bundle": { ... },
  "options": {
    "show_confidence": true,
    "highlight_low_confidence": false
  }
}
```

**Response:**
```json
{
  "svg": "<svg>...</svg>",
  "mermaid": "graph TD; ...",
  "json_format": "..."
}
```

## Starting the Server

### Python (Direct)

```python
from cogant.server.app import create_app
import uvicorn

app = create_app()
uvicorn.run(app, host="0.0.0.0", port=8080, workers=1)
```

### Docker

```bash
# Build image
docker build -f cogant/Dockerfile -t cogant:latest .

# Run container
docker run -p 8080:8080 \
  -e COGANT_RATE_LIMIT=100 \
  -e LOG_LEVEL=info \
  cogant:latest
```

### Docker Compose

```bash
# From repository root
docker-compose up

# Logs
docker-compose logs -f cogant_server
```

The `docker-compose.yml` exposes port 8080 and sets standard logging.

## Configuration

Server behavior is controlled via environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `COGANT_RATE_LIMIT` | `100` | Requests per minute per IP (middleware rate limiter) |
| `COGANT_TIMEOUT` | `300` | Request timeout in seconds |
| `COGANT_MAX_WORKERS` | `4` | Number of uvicorn worker processes |
| `COGANT_LOG_LEVEL` | `"info"` | Log level (debug, info, warning, error) |
| `COGANT_CORS_ORIGINS` | `["*"]` | CORS allowed origins (comma-separated or JSON list) |

## Authentication & Security

v0.5.0 **does not** ship token-based authentication. The server implements:

- **Rate limiting** (configurable via `COGANT_RATE_LIMIT` env var): 100 requests/minute per IP by default.
- **CORS middleware** (default: all origins allowed; tighten via `COGANT_CORS_ORIGINS`).
- **Request timeouts** (configurable via `COGANT_TIMEOUT`).

For production deployments, place the server behind a reverse proxy (nginx, Envoy) with API key enforcement, TLS termination, and stricter CORS policies.

## Error Responses

All endpoints return JSON errors in this format:

```json
{
  "detail": "Human-readable error message",
  "status": 400,
  "error_code": "INVALID_REPO_PATH"
}
```

Common error codes:

- `INVALID_REPO_PATH` — `repo_path` does not exist or is not readable
- `PARSE_ERROR` — Python/JS/TS parsing failed (syntax error or unsupported grammar)
- `TRANSLATION_FAILED` — GNN translation did not produce valid mappings
- `VALIDATION_FAILED` — Output bundle failed validation checks
- `TIMEOUT` — Request exceeded `COGANT_TIMEOUT` threshold

## Health Checks

### /health

Lightweight check; always returns 200 if the server is running.

```bash
curl http://localhost:8080/health
# {"status": "ok", "version": "0.5.0"}
```

### /ready

Detailed readiness; returns 503 if dependencies are missing or misconfigured.

```bash
curl http://localhost:8080/ready
# {
#   "ready": true,
#   "checks": {
#     "python_parser": "ok",
#     "tree_sitter": "ok",
#     "rust_backend": "unavailable"
#   }
# }
```

## Metrics

### GET /metrics (Prometheus format)

```
# TYPE cogant_analysis_total counter
cogant_analysis_total{status="success"} 42
# TYPE cogant_analysis_duration_seconds histogram
cogant_analysis_duration_seconds_bucket{le="1.0"} 10
```

### GET /api/v1/metrics (JSON)

```json
{
  "total_analyses": 42,
  "successful_analyses": 40,
  "failed_analyses": 2,
  "mean_duration_seconds": 2.3,
  "rule_counts": {
    "MutatingSubsystemRule": 156,
    "ActionRule": 89,
    ...
  }
}
```

## Examples

### Analyze a repository

```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "/path/to/repo", "config": {"no_dynamic": true}}'
```

### Reverse a GNN

```bash
curl -X POST http://localhost:8080/reverse \
  -H "Content-Type: application/json" \
  -d '{"gnn_markdown": "# GNN\n[HIDDEN_STATE x]\n..."}'
```

### Get active rules

```bash
curl http://localhost:8080/api/v1/rules | jq '.[] | .name'
```

### Generate visualizations

```bash
curl -X POST http://localhost:8080/api/v1/visualize \
  -H "Content-Type: application/json" \
  -d '{"gnn_bundle": {...}}'
```

## See Also

- [Complete Example](complete_example.md) — full worked example with error handling
- [Performance Tips](performance_tips.md) — scaling considerations
- [FAQ #38: How do I run the FastAPI server?](../faq.md#38-how-do-i-run-the-fastapi-server)
- [`examples/demo_server.py`](https://github.com/cogant-contributors/cogant/tree/main/cogant/examples/demo_server.py) — standalone server startup example
