"""Configuration classes for a Flask-style web application.

Exercises: configuration-as-state, environment overrides, class hierarchy,
dictionary-backed value stores, and a dependency-injection entry point.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any


class ConfigError(Exception):
    """Raised when a required configuration key is missing or malformed."""


class BaseConfig:
    """Base configuration with environment overrides.

    Subclasses should set class-level defaults. At construction time, any
    environment variable with the ``COGANT_`` prefix overrides the class
    attribute of the same name (case-insensitive).
    """

    DEBUG: bool = False
    TESTING: bool = False
    SECRET_KEY: str = "dev-secret-change-me"
    DATABASE_URI: str = "sqlite:///:memory:"
    JSON_SORT_KEYS: bool = True
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16 MB
    SESSION_COOKIE_NAME: str = "session"
    SESSION_COOKIE_SECURE: bool = False
    PERMANENT_SESSION_LIFETIME: int = 3600  # seconds

    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        self._values: dict[str, Any] = {}
        for key in self._own_keys():
            self._values[key] = getattr(type(self), key)
        if overrides:
            for key, value in overrides.items():
                self._values[key.upper()] = value
        self._apply_environment()

    def _own_keys(self) -> Iterable[str]:
        for klass in type(self).__mro__:
            for key, value in vars(klass).items():
                if key.isupper() and not callable(value):
                    yield key

    def _apply_environment(self) -> None:
        for key in list(self._values.keys()):
            env_key = f"COGANT_{key}"
            if env_key in os.environ:
                raw = os.environ[env_key]
                self._values[key] = self._coerce(key, raw)

    def _coerce(self, key: str, raw: str) -> Any:
        current = self._values.get(key)
        if isinstance(current, bool):
            return raw.lower() in {"1", "true", "yes", "on"}
        if isinstance(current, int):
            try:
                return int(raw)
            except ValueError as exc:
                raise ConfigError(f"{key} must be int, got {raw!r}") from exc
        return raw

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key.upper(), default)

    def require(self, key: str) -> Any:
        if key.upper() not in self._values:
            raise ConfigError(f"Missing required config key: {key}")
        return self._values[key.upper()]

    def as_dict(self) -> dict[str, Any]:
        return dict(self._values)

    def __getitem__(self, key: str) -> Any:
        return self.require(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self._values[key.upper()] = value


class DevelopmentConfig(BaseConfig):
    """Configuration for local development."""

    DEBUG = True
    TESTING = False
    DATABASE_URI = "sqlite:///dev.db"
    JSON_SORT_KEYS = False


class TestingConfig(BaseConfig):
    """Configuration for the test suite."""

    DEBUG = False
    TESTING = True
    DATABASE_URI = "sqlite:///:memory:"
    MAX_CONTENT_LENGTH = 1024 * 1024  # 1 MB limit during tests
    SESSION_COOKIE_NAME = "test_session"


class ProductionConfig(BaseConfig):
    """Configuration for deployed production instances."""

    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        super().__init__(overrides)
        if self._values["SECRET_KEY"] == BaseConfig.SECRET_KEY:
            raise ConfigError("SECRET_KEY must be overridden in production")


_CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def load_config(name: str, overrides: dict[str, Any] | None = None) -> BaseConfig:
    """Resolve a config name into an instantiated configuration object."""
    try:
        klass = _CONFIG_MAP[name.lower()]
    except KeyError as exc:
        raise ConfigError(f"Unknown config profile: {name}") from exc
    return klass(overrides)
