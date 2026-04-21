#!/usr/bin/env python3
"""COGANT demo REST server.

This is the second deliverable of the COGANT demo system (the first being
``examples/demo_notebook.ipynb``). It exposes a tiny HTTP surface over the
in-process COGANT engine so the forward pipeline and ``explain`` CLI can be
driven from curl, Postman, or a browser.

Endpoints
---------

``GET /health``
    Liveness probe. Returns ``{"status": "ok", "version": "<cogant.__version__>"}``.

``POST /analyze``
    Body: ``{"repo_path": "<path>"}``. Runs the static forward pipeline on the
    repository and returns a GNN package summary (graph node/edge counts, role
    distribution, Markov blanket partition counts, and pipeline errors).

``GET /explain/{node}?repo_path=<path>``
    Re-runs the static pipeline on ``repo_path`` and asks every translation
    rule to justify its decision on ``{node}``. Returns the
    :class:`cogant.cli.explain.ExplainResult` as JSON.

``GET /docs``
    Redirects to the COGANT documentation site (or the FastAPI-generated
    OpenAPI docs when FastAPI is installed).

Running
-------
The server prefers FastAPI + uvicorn when available because it gives you
automatic OpenAPI docs at ``/docs``. When FastAPI is not installed we fall
back to the pure-stdlib :mod:`http.server`, so the demo is runnable on any
Python 3.10+ install without extra dependencies::

    cd /path/to/cogant
    python examples/demo_server.py            # default port 8080

You can override the bind host and port::

    python examples/demo_server.py --host 0.0.0.0 --port 9000

Smoke test::

    curl -s localhost:8080/health
    curl -s -X POST localhost:8080/analyze \\
        -H 'content-type: application/json' \\
        -d '{"repo_path": "examples/control_positive/calculator"}'
    curl -s 'localhost:8080/explain/input_digit?repo_path=examples/control_positive/calculator'

The server is intentionally single-threaded and not hardened for production
use. It exists so reviewers can poke at COGANT interactively without
spinning up a notebook kernel.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import traceback
from collections import Counter
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import cogant
from cogant.api.bundle import ArtifactKey, Bundle
from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.cli.explain import NodeNotFoundError, explain_node
from cogant.markov import MarkovBlanketExtractor

# Public documentation URL. ``GET /docs`` redirects here when FastAPI's
# built-in OpenAPI UI is not available.
COGANT_DOCS_URL = "https://github.com/ActiveInferenceInstitute/GeneralizedNotationNotation"

logger = logging.getLogger("cogant.demo_server")


# ---------------------------------------------------------------------------
# Shared core: the actual COGANT work, independent of the HTTP framework.
# ---------------------------------------------------------------------------


def _run_forward(repo_path: str) -> Bundle:
    """Run the static forward pipeline on ``repo_path``.

    Used by ``/analyze``. Skips ``dynamic``, ``process``, ``export``, and
    ``validate`` to keep the request turnaround short and hermetic — we do
    not need coverage data, on-disk artifacts, or validation reports to
    answer the demo queries.

    Args:
        repo_path: Absolute or relative path to the repository to analyse.

    Returns:
        A populated :class:`Bundle`.

    Raises:
        FileNotFoundError: If ``repo_path`` does not exist on disk.
    """
    path = Path(repo_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"repo path does not exist: {repo_path}")

    runner = PipelineRunner()
    config = PipelineConfig(
        stages=[
            "ingest",
            "static",
            "normalize",
            "graph",
            "translate",
            "statespace",
        ],
        skip_dynamic=True,
    )
    return runner.run(str(path), config)


def analyze_repo(repo_path: str) -> dict[str, Any]:
    """Return a JSON-ready summary of the forward pipeline on ``repo_path``.

    This is the core of the ``/analyze`` endpoint. We compute:

    * graph node / edge counts,
    * role distribution from the semantic mappings,
    * Markov blanket partition counts (``auto`` strategy), and
    * any pipeline errors (non-fatal — the forward pipeline keeps going
      after stage failures).

    Args:
        repo_path: Repository to analyse.

    Returns:
        A JSON-serialisable dict with the summary.
    """
    bundle = _run_forward(repo_path)
    program_graph = bundle.get_artifact(ArtifactKey.PROGRAM_GRAPH)
    semantic_mappings = bundle.get_artifact(ArtifactKey.SEMANTIC_MAPPINGS) or {}

    # Role histogram from the semantic mappings.
    role_counts: Counter[str] = Counter()
    for mapping in semantic_mappings.values():
        kind = getattr(mapping.kind, "value", None) or str(mapping.kind)
        role_counts[kind] += 1

    # Markov blanket partition. The extractor can raise on very small or
    # degenerate graphs, so we catch and surface the error rather than
    # failing the whole request.
    blanket_summary: dict[str, Any]
    try:
        if program_graph is None:
            raise ValueError("program graph was not produced")
        extractor = MarkovBlanketExtractor(program_graph)
        blanket = extractor.extract(strategy="auto")
        blanket_summary = {
            "internal": len(blanket.internal_ids),
            "sensory": len(blanket.sensory_ids),
            "active": len(blanket.active_ids),
            "external": len(blanket.external_ids),
            "boundary": len(blanket.boundary_ids),
            "strategy": blanket.metadata.get("strategy", "auto"),
            "reason": blanket.metadata.get("auto_reason"),
        }
    except (ValueError, KeyError) as exc:
        blanket_summary = {"error": f"{type(exc).__name__}: {exc}"}

    return {
        "cogant_version": cogant.__version__,
        "target": bundle.target,
        "pipeline_errors": list(bundle.errors),
        "graph": {
            "nodes": len(program_graph.nodes) if program_graph else 0,
            "edges": len(program_graph.edges) if program_graph else 0,
        },
        "semantic_mappings": {
            "total": len(semantic_mappings),
            "by_role": dict(role_counts),
        },
        "markov_blanket": blanket_summary,
    }


def explain_for_api(repo_path: str, node_query: str) -> dict[str, Any]:
    """Wrap :func:`cogant.cli.explain.explain_node` and return its dict form.

    Args:
        repo_path: Repository to analyse.
        node_query: Node name or substring to explain.

    Returns:
        The ``ExplainResult`` as a plain dict.
    """
    result = explain_node(repo_path, node_query)
    return result.to_dict()


# ---------------------------------------------------------------------------
# FastAPI path (preferred).
# ---------------------------------------------------------------------------


def _build_fastapi_app():  # pragma: no cover - exercised only when fastapi present
    """Build and return a FastAPI app, or ``None`` if FastAPI is not installed.

    We defer the import into this function so the stdlib fallback works on
    installs that do not have FastAPI or pydantic available.
    """
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import RedirectResponse
        from pydantic import BaseModel, Field
    except ImportError:
        return None

    class AnalyzeBody(BaseModel):
        """Request body for ``POST /analyze``."""

        repo_path: str = Field(
            ..., description="Absolute or relative path to a repository to analyse."
        )

    app = FastAPI(
        title="COGANT Demo Server",
        version=cogant.__version__,
        description=(
            "Minimal REST surface over the COGANT forward pipeline and "
            "`cogant explain`. Part of the COGANT demo system."
        ),
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": cogant.__version__}

    @app.post("/analyze")
    def analyze(body: AnalyzeBody) -> dict[str, Any]:
        try:
            return analyze_repo(body.repo_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/explain/{node}")
    def explain(node: str, repo_path: str) -> dict[str, Any]:
        try:
            return explain_for_api(repo_path, node)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except NodeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # The ``/docs`` path is already owned by FastAPI's auto-generated Swagger
    # UI, so we do not override it here — the user gets interactive OpenAPI
    # docs for free. We still expose an explicit redirect target at
    # ``/external-docs`` for parity with the stdlib fallback.
    @app.get("/external-docs")
    def external_docs() -> RedirectResponse:
        return RedirectResponse(COGANT_DOCS_URL, status_code=302)

    return app


def _run_fastapi(host: str, port: int) -> int:  # pragma: no cover - runtime path
    """Run the FastAPI app with uvicorn. Returns process exit code."""
    try:
        import uvicorn
    except ImportError:
        return -1

    app = _build_fastapi_app()
    if app is None:
        return -1

    logger.info("Serving COGANT demo via FastAPI on http://%s:%s", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


# ---------------------------------------------------------------------------
# Stdlib http.server fallback.
# ---------------------------------------------------------------------------


def _send_json(handler, status: int, payload: dict[str, Any]) -> None:
    """Serialise ``payload`` as JSON and write it to the response stream."""
    body = json.dumps(payload, indent=2, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("content-type", "application/json; charset=utf-8")
    handler.send_header("content-length", str(len(body)))
    handler.send_header("access-control-allow-origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _send_redirect(handler, location: str) -> None:
    """Send a 302 redirect to ``location``."""
    handler.send_response(HTTPStatus.FOUND)
    handler.send_header("location", location)
    handler.send_header("content-length", "0")
    handler.end_headers()


def _build_stdlib_handler():
    """Return a :class:`http.server.BaseHTTPRequestHandler` subclass.

    The handler dispatches the four demo endpoints manually. We build it
    inside a function so ``http.server`` is only imported on the fallback
    path.
    """
    from http.server import BaseHTTPRequestHandler

    class CogantDemoHandler(BaseHTTPRequestHandler):
        """Dispatches COGANT demo endpoints over the stdlib HTTP server."""

        server_version = f"CogantDemo/{cogant.__version__}"

        def log_message(self, fmt: str, *args: Any) -> None:
            """Route access logs through the module logger instead of stderr."""
            logger.info("%s - %s", self.address_string(), fmt % args)

        # ``GET`` handlers ------------------------------------------------

        def do_GET(self) -> None:  # noqa: N802 (stdlib naming convention)
            parsed = urlparse(self.path)
            path = parsed.path

            try:
                if path == "/health":
                    _send_json(
                        self,
                        HTTPStatus.OK,
                        {"status": "ok", "version": cogant.__version__},
                    )
                    return

                if path == "/docs":
                    _send_redirect(self, COGANT_DOCS_URL)
                    return

                if path.startswith("/explain/"):
                    node = path[len("/explain/") :]
                    if not node:
                        _send_json(
                            self,
                            HTTPStatus.BAD_REQUEST,
                            {"error": "empty node name in /explain/{node}"},
                        )
                        return
                    query = parse_qs(parsed.query or "")
                    repo_paths = query.get("repo_path")
                    if not repo_paths:
                        _send_json(
                            self,
                            HTTPStatus.BAD_REQUEST,
                            {"error": "missing ?repo_path= query parameter"},
                        )
                        return
                    result = explain_for_api(repo_paths[0], node)
                    _send_json(self, HTTPStatus.OK, result)
                    return

                _send_json(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {"error": f"no GET handler for {path!r}"},
                )
            except FileNotFoundError as exc:
                _send_json(self, HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except NodeNotFoundError as exc:
                _send_json(self, HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except (ValueError, RuntimeError) as exc:
                _send_json(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001 - last-chance handler
                logger.exception("unhandled error in GET %s", path)
                _send_json(
                    self,
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": f"{type(exc).__name__}: {exc}",
                        "traceback": traceback.format_exc(),
                    },
                )

        # ``POST`` handlers -----------------------------------------------

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            try:
                if path != "/analyze":
                    _send_json(
                        self,
                        HTTPStatus.NOT_FOUND,
                        {"error": f"no POST handler for {path!r}"},
                    )
                    return

                length = int(self.headers.get("content-length", "0") or "0")
                if length <= 0:
                    _send_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"error": "empty request body; expected JSON"},
                    )
                    return
                raw = self.rfile.read(length)
                try:
                    body = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    _send_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"error": f"invalid JSON body: {exc}"},
                    )
                    return
                if not isinstance(body, dict) or "repo_path" not in body:
                    _send_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"error": 'body must be an object with a "repo_path" field'},
                    )
                    return

                result = analyze_repo(str(body["repo_path"]))
                _send_json(self, HTTPStatus.OK, result)
            except FileNotFoundError as exc:
                _send_json(self, HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except (ValueError, RuntimeError) as exc:
                _send_json(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001 - last-chance handler
                logger.exception("unhandled error in POST %s", path)
                _send_json(
                    self,
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": f"{type(exc).__name__}: {exc}",
                        "traceback": traceback.format_exc(),
                    },
                )

    return CogantDemoHandler


def _run_stdlib(host: str, port: int) -> int:
    """Run the stdlib ``http.server`` fallback. Returns process exit code."""
    from http.server import HTTPServer

    handler_cls = _build_stdlib_handler()
    httpd = HTTPServer((host, port), handler_cls)
    logger.info(
        "Serving COGANT demo via http.server on http://%s:%s (FastAPI not installed)",
        host,
        port,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutdown requested via KeyboardInterrupt")
    finally:
        httpd.server_close()
    return 0


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------


def _parse_args(argv: list | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cogant-demo-server",
        description="Run the COGANT demo REST server (FastAPI if available).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host (default: 127.0.0.1). Use 0.0.0.0 to listen on all interfaces.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Bind port (default: 8080).",
    )
    parser.add_argument(
        "--force-stdlib",
        action="store_true",
        help="Skip the FastAPI path even when it is installed. Useful for testing the fallback.",
    )
    return parser.parse_args(argv)


def main(argv: list | None = None) -> int:
    """Start the demo server. Returns process exit code."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = _parse_args(argv)

    if not args.force_stdlib:
        rc = _run_fastapi(args.host, args.port)
        if rc >= 0:
            return rc
        logger.info("FastAPI not available; falling back to http.server")

    return _run_stdlib(args.host, args.port)


if __name__ == "__main__":
    sys.exit(main())
