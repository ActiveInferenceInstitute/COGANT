# cogant.server

REST interface to the COGANT engine. The FastAPI backend is the production path;
request and response models live in `models.py`, and `run_server()` provides the
public entry point exported from `cogant.server`.

## Public API

| Symbol | Role |
| --- | --- |
| `create_app()` | Build the FastAPI application object. |
| `run_server(host, port)` | Serve with FastAPI/uvicorn when available, falling back to the stdlib backend where supported. |

## Endpoint Contract

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe with COGANT version. |
| `GET` | `/ready` | Dependency readiness checks. |
| `POST` | `/analyze` | Forward pipeline summary. |
| `POST` | `/reverse` | Synthesize Python package zip from GNN markdown. |
| `POST` | `/roundtrip` | v0.6 roundtrip invariant summary. |
| `GET` | `/metrics` | Prometheus text metrics. |
| `GET` | `/api/v1/rules` | Translation-rule metadata. |
| `POST` | `/api/v1/analyze` | Versioned analysis response with request id and timing. |
| `POST` | `/api/v1/roundtrip` | Versioned roundtrip response with request id and timing. |
| `POST` | `/api/v1/visualize` | Source-code visualization as `mermaid`, `json`, or `graphml`. |
| `GET` | `/api/v1/metrics` | JSON metrics summary. |

## Roundtrip Fields

Roundtrip responses use the v0.6 taxonomy: `roundtrip_status`,
`role_preservation_score`, `role_preserved`, `structurally_isomorphic`,
`matrix_preserved`, `gnn_sections_preserved`, `generated_code_ok`, and an
`invariants` ledger. Strict structural isomorphism is separate from role
preservation.

## Conventions

- Handlers return JSON-safe payloads and normalize errors through `ErrorResponse`.
- Request metrics are exposed both as Prometheus text and a compact JSON summary.
- `create_app()` bounds actual request bytes (including chunked bodies),
  expensive-request concurrency, and dispatch time. The default bind is
  loopback; non-loopback binds require an auth token.
- The default workspace is local and path-bounded: relative paths resolve
  beneath `workspace_root`, outside/traversal paths return 403, and missing
  in-bound directories return 404. Absolute paths require the explicit
  `allow_absolute_paths=True` opt-in.
- Invalid request bodies use 422; internal failures return a redacted 500
  envelope with a request id. This service is not a sandbox or arbitrary-code
  execution boundary.
- Analysis responses expose `pipeline_status` so partial, failed, skipped, and
  unavailable results cannot be mistaken for successful evidence.
- Route docs should be updated in [`AGENTS.md`](AGENTS.md) whenever `app.py` decorators or `models.py` fields change.
