# `cogant.server`

REST + WebSocket interface to the COGANT engine. Prefers
FastAPI + uvicorn (auto-generated OpenAPI at `/docs`, Pydantic request
validation); falls back to a pure-stdlib `http.server` dispatcher that
serves the same endpoint contract when FastAPI is not installed, so
`cogant serve` works on any Python 3.11+ install.

## Public API

Re-exported from `cogant/server/__init__.py`:

| Symbol | Role |
| --- | --- |
| `create_app()` | Build the FastAPI application object. Raises `RuntimeError` if FastAPI is missing — callers wanting the stdlib fallback should use `run_server`. |
| `run_server(host, port)` | Bind and serve. Selects FastAPI+uvicorn when available; otherwise drops into the stdlib backend. |

## Endpoint contract

Both backends honour the same paths:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`  | `/health` | Liveness probe (`{"status": "ok"}`). |
| `POST` | `/api/v1/translate` | Run the forward pipeline on inline source code. |
| `POST` | `/api/v1/visualize` | Render the program graph as `mermaid` / `json` / `graphml`. |
| `POST` | `/api/v1/translate/stream` | Async streaming variant that emits stage events. |
| `POST` | `/api/v1/translate/batch` | Sequential batch translation with per-item summaries. |

## Conventions

* Endpoints are intentionally decoupled from
  `examples/demo_server.py` so the demo can stay minimal while the
  production surface evolves (auth, rate limiting, …).
* All handlers return JSON-safe payloads via
  `cogant.api.bundle._json_default` so `datetime`, `Path`, and dataclass
  values serialise cleanly.
* Errors normalise to `{"detail": str}` with appropriate 4xx/5xx codes.

See [`AGENTS.md`](AGENTS.md) for the per-handler contract and
[`../api/AGENTS.md`](../api/AGENTS.md) for the orchestration helpers
the handlers delegate to.
