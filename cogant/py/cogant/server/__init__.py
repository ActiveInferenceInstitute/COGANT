"""COGANT production REST server package.

This package exposes the COGANT engine over HTTP. The preferred backend
is FastAPI + uvicorn (automatic OpenAPI docs at ``/docs``, request
validation via Pydantic). When FastAPI is not installed, the package
falls back to a pure-stdlib :mod:`http.server` dispatcher that serves
the same endpoint contract so the server remains runnable on any
Python 3.11+ install without extra dependencies.

Two public entry points are exported:

* :func:`create_app` — build a FastAPI ``app`` object. Raises
  :class:`RuntimeError` when FastAPI is not installed (callers who want
  the stdlib fallback should use :func:`run_server` instead).
* :func:`run_server` — bind and serve the HTTP interface. Automatically
  selects FastAPI+uvicorn when available; otherwise drops into the
  stdlib fallback. Both backends honour the same ``host`` and ``port``
  arguments.

The package is intentionally independent from ``examples/demo_server.py``
so the demo can stay minimal and the production server can evolve its
own surface (new endpoints, auth, rate-limiting, …) without breaking
the notebook walk-through.
"""

from __future__ import annotations

from cogant.server.app import create_app, run_server

__all__ = ["create_app", "run_server"]
