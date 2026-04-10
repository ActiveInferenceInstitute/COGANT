# Agents — py/cogant/server

## Owner

Runtime Lead

## Responsibilities

HTTP surface for COGANT: `create_app` builds a FastAPI application (OpenAPI at `/docs`); `run_server` binds and serves, preferring FastAPI+uvicorn and falling back to a stdlib `http.server` implementation when FastAPI is absent so the contract stays testable everywhere.

## Coordination

Independent of `examples/demo_server.py`; extend here for production endpoints, auth, or rate limits.

## Files

- `app.py` — `create_app`, `run_server`, route wiring.
- `models.py` — Pydantic request/response models (see module).
- `__init__.py` — exports `create_app`, `run_server`.
