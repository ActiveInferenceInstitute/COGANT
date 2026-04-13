"""Flask-pattern application entry point.

Exercises: route decorators, middleware chaining, request/response
observables, error handlers, and an app-factory function that wires a
config, a service container, and a blueprint-like set of handlers
together without requiring Flask to be installed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .config import BaseConfig, load_config
from .models import User, ValidationError
from .services import (
    AuthorizationError,
    NotFoundError,
    ServiceContainer,
    ServiceError,
)
from .utils import jsonify, paginate

logger = logging.getLogger(__name__)

Handler = Callable[["Request"], "Response"]


@dataclass
class Request:
    """HTTP request observation."""

    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    query: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    principal: Optional[User] = None

    def get_header(self, name: str) -> Optional[str]:
        return self.headers.get(name.lower())


@dataclass
class Response:
    """HTTP response action."""

    status: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None

    def json(self) -> str:
        return jsonify(self.body)


class Route:
    """A registered URL pattern + method + handler."""

    def __init__(self, pattern: str, methods: Tuple[str, ...], handler: Handler) -> None:
        self.pattern = pattern
        self.methods = tuple(m.upper() for m in methods)
        self.handler = handler

    def matches(self, request: Request) -> bool:
        return request.path == self.pattern and request.method.upper() in self.methods


class Middleware:
    """Base class for request/response transforms."""

    def before_request(self, request: Request) -> Optional[Response]:
        return None

    def after_request(self, request: Request, response: Response) -> Response:
        return response


class AuthMiddleware(Middleware):
    """Resolves a bearer token into ``request.principal``."""

    def __init__(self, container: ServiceContainer) -> None:
        self.container = container

    def before_request(self, request: Request) -> Optional[Response]:
        auth = request.get_header("authorization")
        if not auth or not auth.lower().startswith("bearer "):
            return None
        token = auth.split(None, 1)[1]
        for user in self.container.session.all(User):
            if user.id == token and user.is_active:
                request.principal = user
                return None
        return Response(status=401, body={"error": "invalid_token"})


class LoggingMiddleware(Middleware):
    """Logs every request/response pair; also tracks per-path counters."""

    def __init__(self) -> None:
        self.counters: Dict[str, int] = {}

    def before_request(self, request: Request) -> Optional[Response]:
        self.counters[request.path] = self.counters.get(request.path, 0) + 1
        logger.info("%s %s", request.method, request.path)
        return None

    def after_request(self, request: Request, response: Response) -> Response:
        logger.info("-> %d %s", response.status, request.path)
        return response


class Application:
    """A Flask-style HTTP application."""

    def __init__(self, config: BaseConfig) -> None:
        self.config = config
        self.container = ServiceContainer(config)
        self.routes: List[Route] = []
        self.middlewares: List[Middleware] = [
            LoggingMiddleware(),
            AuthMiddleware(self.container),
        ]
        self.error_handlers: Dict[type, Handler] = {}

    def route(self, pattern: str, methods: Tuple[str, ...] = ("GET",)) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            self.routes.append(Route(pattern, methods, handler))
            return handler
        return decorator

    def errorhandler(self, exc_type: type) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            self.error_handlers[exc_type] = handler
            return handler
        return decorator

    def dispatch(self, request: Request) -> Response:
        for mw in self.middlewares:
            early = mw.before_request(request)
            if early is not None:
                return self._finalise(request, early)
        for route in self.routes:
            if route.matches(request):
                try:
                    response = route.handler(request)
                except Exception as exc:  # noqa: BLE001
                    response = self._handle_error(exc)
                return self._finalise(request, response)
        return self._finalise(request, Response(status=404, body={"error": "not_found"}))

    def _finalise(self, request: Request, response: Response) -> Response:
        for mw in reversed(self.middlewares):
            response = mw.after_request(request, response)
        return response

    def _handle_error(self, exc: Exception) -> Response:
        for exc_type, handler in self.error_handlers.items():
            if isinstance(exc, exc_type):
                try:
                    return handler(Request(method="ERROR", path=str(exc)))
                except Exception:  # noqa: BLE001
                    logger.exception("error handler itself failed")
                    break
        if isinstance(exc, ValidationError):
            return Response(status=400, body={"error": str(exc)})
        if isinstance(exc, AuthorizationError):
            return Response(status=403, body={"error": str(exc)})
        if isinstance(exc, NotFoundError):
            return Response(status=404, body={"error": str(exc)})
        if isinstance(exc, ServiceError):
            return Response(status=409, body={"error": str(exc)})
        logger.exception("unhandled error: %s", exc)
        return Response(status=500, body={"error": "internal_server_error"})


def create_app(profile: str = "development", overrides: Optional[Dict[str, Any]] = None) -> Application:
    """Application factory, Flask-style."""
    config = load_config(profile, overrides)
    app = Application(config)

    @app.route("/", methods=("GET",))
    def index(request: Request) -> Response:
        return Response(body={"name": "flask_app", "profile": profile})

    @app.route("/health", methods=("GET",))
    def health(request: Request) -> Response:
        return Response(body={"status": "ok"})

    @app.route("/api/users/register", methods=("POST",))
    def register(request: Request) -> Response:
        data = request.body or {}
        user = app.container.users.register(
            data.get("username", ""),
            data.get("email", ""),
            data.get("password", ""),
        )
        return Response(status=201, body=user.to_dict())

    @app.route("/api/users/login", methods=("POST",))
    def login(request: Request) -> Response:
        data = request.body or {}
        user = app.container.users.authenticate(
            data.get("username", ""),
            data.get("password", ""),
        )
        if user is None:
            return Response(status=401, body={"error": "invalid_credentials"})
        return Response(body={"token": user.id, "role": user.role})

    @app.route("/api/posts", methods=("GET",))
    def list_posts(request: Request) -> Response:
        page = int(request.query.get("page", "1"))
        per_page = int(request.query.get("per_page", "20"))
        items = [p.to_dict() for p in app.container.posts.list_published()]
        return Response(body=paginate(items, page=page, per_page=per_page))

    @app.route("/api/posts", methods=("POST",))
    def create_post(request: Request) -> Response:
        if request.principal is None:
            return Response(status=401, body={"error": "auth_required"})
        data = request.body or {}
        post = app.container.posts.create(
            request.principal,
            data.get("title", ""),
            data.get("body", ""),
            data.get("tags"),
        )
        return Response(status=201, body=post.to_dict())

    @app.errorhandler(ValueError)
    def on_value_error(request: Request) -> Response:
        return Response(status=400, body={"error": "bad_value", "detail": request.path})

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app("development")
    response = app.dispatch(Request(method="GET", path="/health"))
    print(response.status, response.body)
