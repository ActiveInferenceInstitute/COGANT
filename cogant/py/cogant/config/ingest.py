"""Ingest stage configuration.

Controls how the ingest stage discovers, reads, and filters files from
the target codebase. Frozen so that config objects can be safely shared
across concurrent stages without risk of mutation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IngestConfig(BaseModel):
    """Configuration for the ingest stage.

    Attributes:
        max_file_size_kb: Reject files larger than this (in kilobytes).
        include_extensions: Only ingest files with these suffixes.
        exclude_patterns: Skip any path that contains one of these
            substrings (e.g. ``__pycache__``, ``.git``).
        follow_symlinks: Whether to follow symbolic links during
            directory traversal.
        encoding: Text encoding used when reading source files.
    """

    max_file_size_kb: int = Field(
        default=512, ge=1, description="Max file size in kilobytes"
    )
    include_extensions: list[str] = Field(
        default_factory=lambda: [".py", ".js", ".ts"],
        description="File suffixes to include",
    )
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["__pycache__", ".git", "node_modules"],
        description="Path substrings to exclude",
    )
    follow_symlinks: bool = Field(
        default=False, description="Follow symlinks during traversal"
    )
    encoding: str = Field(
        default="utf-8", description="Text encoding for source files"
    )

    model_config = ConfigDict(frozen=True)
