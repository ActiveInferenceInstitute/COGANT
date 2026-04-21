"""
Minimal Flask-like HTTP framework.

Exercises: class hierarchy, decorators as policies, request/response as observations,
middleware as hidden state transforms.
"""

from collections.abc import Callable


class Request:
    """HTTP request observation."""

    def __init__(self, method: str, path: str, body: str | None = None):
        self.method = method
        self.path = path
        self.body = body
        self.headers = {}

    def get_header(self, name: str) -> str | None:
        return self.headers.get(name)


class Response:
    """HTTP response action."""

    def __init__(self, status: int, body: str = ""):
        self.status = status
        self.body = body
        self.headers = {}

    def set_header(self, name: str, value: str) -> None:
        self.headers[name] = value


class Middleware:
    """Hidden state transform - processes request/response."""

    def process_request(self, req: Request) -> Request:
        """Transform request before routing."""
        return req

    def process_response(self, req: Request, resp: Response) -> Response:
        """Transform response after handling."""
        return resp


class LoggingMiddleware(Middleware):
    """Logs all requests (hidden state: request log)."""

    def __init__(self):
        self.request_log = []

    def process_request(self, req: Request) -> Request:
        self.request_log.append({"method": req.method, "path": req.path})
        return req


class AuthMiddleware(Middleware):
    """Enforces authentication (hidden state: authenticated flag)."""

    def __init__(self, secret_token: str):
        self.secret_token = secret_token
        self.authenticated = False

    def process_request(self, req: Request) -> Request:
        auth_header = req.get_header("Authorization")
        self.authenticated = auth_header == f"Bearer {self.secret_token}"
        return req

    def process_response(self, req: Request, resp: Response) -> Response:
        if not self.authenticated:
            resp.status = 401
            resp.body = "Unauthorized"
        return resp


class Route:
    """A registered route."""

    def __init__(self, path: str, method: str, handler: Callable):
        self.path = path
        self.method = method
        self.handler = handler


class Application:
    """Mini HTTP application with state, routes, and middleware."""

    def __init__(self):
        self.routes: list[Route] = []
        self.middlewares: list[Middleware] = []
        self.error_handlers: dict[int, Callable] = {}

    def route(self, path: str, method: str = "GET") -> Callable:
        """Decorator to register a route."""

        def decorator(func: Callable) -> Callable:
            self.routes.append(Route(path, method, func))
            return func

        return decorator

    def error_handler(self, status_code: int) -> Callable:
        """Decorator to register error handler."""

        def decorator(func: Callable) -> Callable:
            self.error_handlers[status_code] = func
            return func

        return decorator

    def use_middleware(self, middleware: Middleware) -> None:
        """Register a middleware."""
        self.middlewares.append(middleware)

    def match_route(self, req: Request) -> Route | None:
        """Find matching route for request."""
        for route in self.routes:
            if route.path == req.path and route.method == req.method:
                return route
        return None

    def handle_request(self, req: Request) -> Response:
        """Process request through middleware and routing."""
        # Pre-process with middlewares
        for mw in self.middlewares:
            req = mw.process_request(req)

        # Find and execute route handler
        route = self.match_route(req)
        if route:
            try:
                resp = route.handler(req)
            except Exception as e:
                resp = Response(500, f"Internal error: {str(e)}")
        else:
            resp = Response(404, "Not Found")

        # Post-process with middlewares
        for mw in self.middlewares:
            resp = mw.process_response(req, resp)

        return resp


# Example usage
if __name__ == "__main__":
    app = Application()

    # Add middleware
    app.use_middleware(LoggingMiddleware())
    app.use_middleware(AuthMiddleware("secret123"))

    # Register routes
    @app.route("/", method="GET")
    def home(req: Request) -> Response:
        return Response(200, "Hello World")

    @app.route("/api/data", method="GET")
    def get_data(req: Request) -> Response:
        return Response(200, '{"data": [1, 2, 3]}')

    @app.route("/api/data", method="POST")
    def post_data(req: Request) -> Response:
        return Response(201, "Data created")

    # Test request
    test_req = Request("GET", "/")
    test_req.headers["Authorization"] = "Bearer secret123"
    resp = app.handle_request(test_req)
    print(f"Status: {resp.status}, Body: {resp.body}")
