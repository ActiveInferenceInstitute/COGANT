"""Content-addressed hashing for repositories and files.

Uses SHA-256 over sorted (relative_path, content) pairs so the digest is
deterministic regardless of filesystem traversal order.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_DEFAULT_EXTENSIONS: list[str] = [".py", ".js", ".ts"]
_IGNORED_DIRS: set[str] = {"__pycache__", ".git", ".venv", "node_modules"}


def hash_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a single file's contents."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def hash_repo(
    repo_path: Path,
    extensions: list[str] | None = None,
) -> str:
    """Return a SHA-256 hex digest representing the repo's relevant content.

    The hash is computed over ``sorted(relative_path + file_content)`` for
    every file whose suffix is in *extensions* (default: .py, .js, .ts).
    Directories in ``_IGNORED_DIRS`` are skipped entirely.
    """
    exts = set(extensions) if extensions is not None else set(_DEFAULT_EXTENSIONS)
    h = hashlib.sha256()

    entries: list[tuple[str, bytes]] = []
    for child in sorted(repo_path.rglob("*")):
        # Skip ignored directories and their contents.
        if any(part in _IGNORED_DIRS for part in child.parts):
            continue
        if child.is_file() and child.suffix in exts:
            rel = str(child.relative_to(repo_path))
            entries.append((rel, child.read_bytes()))

    for rel, content in entries:
        h.update(rel.encode())
        h.update(content)

    return h.hexdigest()
