from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from _typeshed import Incomplete

__all__ = ['app', 'create_app', 'run_server']

@dataclass
class _MetricsStore:
    requests: dict[tuple[str, str, int], int] = field(default_factory=Incomplete)
    errors: dict[tuple[str, str], int] = field(default_factory=Incomplete)
    rate_limited: dict[tuple[str, str], int] = field(default_factory=Incomplete)
    duration_sum: dict[tuple[str, str], float] = field(default_factory=Incomplete)
    duration_count: dict[tuple[str, str], int] = field(default_factory=Incomplete)
    def record(self, method: str, path: str, status: int, duration_s: float) -> None: ...
    def record_rate_limited(self, method: str, path: str) -> None: ...
    def render_prometheus(self) -> str: ...

@dataclass
class _RateLimiter:
    max_requests: int = ...
    window_s: float = ...
    def check(self, key: str) -> bool: ...

def create_app(*, rate_limit_requests: int = 10, rate_limit_window_s: float = 60.0, rate_limited_paths: Iterable[str] = ('/analyze',), unlimited_paths: Iterable[str] = ('/health', '/ready', '/metrics', '/openapi.json', '/docs')) -> Any: ...

app: Any

def run_server(host: str = '0.0.0.0', port: int = 8080) -> int: ...
