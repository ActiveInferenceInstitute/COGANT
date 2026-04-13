"""requests-style HTTP library fixture for COGANT integration tests."""

from .adapters import BaseAdapter, HTTPAdapter, MockAdapter, MountTable
from .auth import AuthBase, BasicAuth, BearerAuth, HMACAuth, NoAuth, RotatingTokenAuth, build_auth
from .models import (
    CaseInsensitiveDict,
    ConnectionError,
    HTTPError,
    PreparedRequest,
    Request,
    RequestException,
    Response,
    Timeout,
)
from .sessions import CookieJar, Session
from .utils import (
    STATUS_CODES,
    default_headers,
    is_client_error,
    is_redirect,
    is_server_error,
    is_success,
    parse_url,
    rebuild_url,
    resolve_redirect,
    status_text,
)

__all__ = [
    "AuthBase",
    "BaseAdapter",
    "BasicAuth",
    "BearerAuth",
    "CaseInsensitiveDict",
    "ConnectionError",
    "CookieJar",
    "HMACAuth",
    "HTTPAdapter",
    "HTTPError",
    "MockAdapter",
    "MountTable",
    "NoAuth",
    "PreparedRequest",
    "Request",
    "RequestException",
    "Response",
    "RotatingTokenAuth",
    "STATUS_CODES",
    "Session",
    "Timeout",
    "build_auth",
    "default_headers",
    "is_client_error",
    "is_redirect",
    "is_server_error",
    "is_success",
    "parse_url",
    "rebuild_url",
    "resolve_redirect",
    "status_text",
]
