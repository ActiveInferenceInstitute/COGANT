# Agents - py/cogant/server

## Owner

Runtime Lead

## Scope

HTTP access to COGANT pipeline behavior. `app.py` builds the FastAPI
application, middleware, rate limiter, metrics store, and route handlers.
`models.py` owns the Pydantic v2 request/response contract used by FastAPI and
stdlib fallback paths.

## Live Route Surface

- `GET /health` - liveness with package version and docs path.
- `GET /ready` - dependency readiness probe.
- `POST /analyze` - forward pipeline summary using `AnalyzeRequest` / `AnalyzeResponse`.
- `POST /reverse` - synthesize a package zip from inline GNN markdown.
- `POST /roundtrip` - forward-reverse-forward verification using v0.6 roundtrip status fields.
- `GET /metrics` - Prometheus text metrics.
- `GET /api/v1/rules` - metadata for the 22 registered translation rules.
- `POST /api/v1/analyze` - v1 analysis response with request id and timing.
- `POST /api/v1/roundtrip` - v1 roundtrip response with request id and timing.
- `POST /api/v1/visualize` - source-code visualization as `mermaid`, `json`, or `graphml`.
- `GET /api/v1/metrics` - JSON system metrics summary.

## Roundtrip Contract

Do not describe role-only preservation as isomorphism. Current responses expose:
`roundtrip_status`, `role_preservation_score`, `role_preserved`,
`structurally_isomorphic`, `matrix_preserved`, `gnn_sections_preserved`,
`generated_code_ok`, `invariants`, original/synthesized role counts, threshold,
and errors. Deprecated compatibility aliases may exist in models, but docs and
new clients should use the v0.6 names.

## Rules

- Keep route documentation synchronized with `app.py` decorators and `models.py` fields.
- Preserve Pydantic `extra="forbid"` contracts unless an API-versioned migration is added.
- Keep `/health`, `/ready`, `/metrics`, `/openapi.json`, and `/docs` unrestricted by rate limits.
- Surface failures through `ErrorResponse` rather than raw tracebacks in normal response bodies.

## Verification

From the inner package root:

```bash
uv run pytest tests/unit/test_server_app_http_routes.py tests/unit/test_server_models_contract.py -q --no-cov
uv run pytest tests/unit/test_server_statespace_compiler.py -q --no-cov
```
