from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from _typeshed import Incomplete

from cogant.config.schema import ProjectConfig

__all__ = ["app", "create_app", "create_app_from_config", "run_server"]

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

def create_app(
    *,
    rate_limit_requests: int = 10,
    rate_limit_window_s: float = 60.0,
    rate_limited_paths: Iterable[str] = ("/analyze",),
    unlimited_paths: Iterable[str] = ("/health", "/ready", "/metrics", "/openapi.json", "/docs"),
    workspace_root: str = ".",
    allow_absolute_paths: bool = False,
    auth_token: str | None = None,
    max_request_bytes: int = 2_000_000,
    max_gnn_text_bytes: int = 1_000_000,
    max_archive_bytes: int = 25_000_000,
    max_archive_files: int = 1_000,
    max_concurrent_requests: int = 4,
    request_timeout_s: float = 300.0,
    bind_host: str = "127.0.0.1",
) -> Any: ...

def create_app_from_config(config: ProjectConfig) -> Any: ...

app: Any

def run_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    *,
    workspace_root: str = ".",
    auth_token: str | None = None,
    config: ProjectConfig | None = None,
) -> int: ...
