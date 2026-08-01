"""Content-addressed hashing for repositories and files.

Uses SHA-256 over sorted (relative_path, content) pairs so the digest is
deterministic regardless of filesystem traversal order.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

_DEFAULT_EXTENSIONS: list[str] = [
    ".py",
    ".pyx",
    ".pyi",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".rs",
    ".go",
]
_IGNORED_DIRS: set[str] = {"__pycache__", ".git", ".venv", "node_modules"}


def hash_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a single file's contents."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _iter_repo_files(repo_path: Path, exts: set[str]):
    """Yield ``(relative_path, real_path)`` for matching files in the repo.

    Uses ``os.walk(followlinks=False)`` so directory symlinks that leave the
    repository are not traversed, keeping the content hash (and thus the cache
    key) from silently including or looping through out-of-tree content.
    """
    root = repo_path.resolve()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Prune ignored directories in-place so os.walk does not descend.
        dirnames[:] = [d for d in dirnames if d not in _IGNORED_DIRS]
        for filename in sorted(filenames):
            full = Path(dirpath) / filename
            if full.is_file() and full.suffix in exts:
                try:
                    rel = full.resolve().relative_to(root)
                except ValueError:
                    # Real path escapes the repo root; skip it.
                    continue
                yield rel, full


def hash_repo(
    repo_path: Path,
    extensions: list[str] | None = None,
) -> str:
    """Return a SHA-256 hex digest representing the repo's relevant content.

    The hash is computed over ``sorted(relative_path + file_content)`` for
    every file whose suffix is in *extensions* (default: .py, .js, .ts).
    Files are streamed one at a time so memory stays bounded regardless of
    total repository size. Directories in ``_IGNORED_DIRS`` are skipped.
    """
    exts = set(extensions) if extensions is not None else set(_DEFAULT_EXTENSIONS)
    h = hashlib.sha256()

    for rel, full in sorted(_iter_repo_files(repo_path, exts), key=lambda pair: pair[0]):
        # Length-prefix both fields so path/content boundaries cannot collide
        # (for example, ``ab`` + ``c`` vs ``a`` + ``bc``).
        rel_bytes = str(rel).encode()
        h.update(len(rel_bytes).to_bytes(8, "big"))
        h.update(rel_bytes)
        content_length = full.stat().st_size
        h.update(content_length.to_bytes(8, "big"))
        with full.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)

    return h.hexdigest()
