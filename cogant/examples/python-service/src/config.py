"""Configuration management for the example service."""

from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Example Python Service"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite:///./test.db"
    echo_sql: bool = False

    # API
    api_prefix: str = "/api/v1"
    api_timeout: int = 30

    # Features
    enable_caching: bool = True
    cache_ttl: int = 300

    # Security
    secret_key: str = "secret-key-change-in-production"
    cors_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    return Settings()
