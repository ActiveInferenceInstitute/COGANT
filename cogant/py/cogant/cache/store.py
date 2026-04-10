"""Content-addressed result cache backed by JSON files.

Storage layout::

    <cache_dir>/<content_hash[:2]>/<content_hash>.json

Thread safety for concurrent reads is achieved via atomic writes
(write-to-temp then rename) and tolerant reads.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT_TTL_SECONDS: int = 7 * 24 * 60 * 60  # 7 days


def get_cache_dir() -> Path:
    """Return the default cache directory: ``~/.cache/cogant``."""
    return Path.home() / ".cache" / "cogant"


@dataclass(frozen=True)
class CacheKey:
    """Uniquely identifies a cached analysis result."""

    repo_path: str
    content_hash: str  # SHA-256 of repo contents
    cogant_version: str


@dataclass
class CacheEntry:
    """A single cached result."""

    key: CacheKey
    created_at: str  # ISO 8601
    stage_results: dict[str, Any]
    hit: bool = False


class CacheStore:
    """Filesystem-backed content-addressed cache.

    Parameters
    ----------
    cache_dir:
        Root directory for cache files. Defaults to ``~/.cache/cogant``.
    ttl_seconds:
        Time-to-live for cache entries in seconds. Defaults to 7 days.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        self._dir = cache_dir or get_cache_dir()
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    # -- public API ----------------------------------------------------------

    def get(self, key: CacheKey) -> CacheEntry | None:
        """Retrieve a cached entry, or ``None`` on miss / expiry."""
        path = self._path_for(key)
        if not path.is_file():
            self._misses += 1
            return None

        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            self._misses += 1
            return None

        entry = self._deserialize(data)
        if self._is_expired(entry):
            self._misses += 1
            return None

        entry.hit = True
        self._hits += 1
        return entry

    def put(self, key: CacheKey, stage_results: dict[str, Any]) -> CacheEntry:
        """Store *stage_results* under *key* and return the new entry."""
        entry = CacheEntry(
            key=key,
            created_at=datetime.now(timezone.utc).isoformat(),
            stage_results=stage_results,
        )
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: temp file in same dir, then rename.
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(self._serialize(entry), f)
            os.replace(tmp, str(path))
        except BaseException:
            # Clean up temp on failure.
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

        return entry

    def invalidate(self, key: CacheKey) -> bool:
        """Remove the entry for *key*. Returns ``True`` if it existed."""
        path = self._path_for(key)
        if path.is_file():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        """Remove **all** cached entries. Returns count removed."""
        count = 0
        if not self._dir.is_dir():
            return 0
        for json_file in self._dir.rglob("*.json"):
            json_file.unlink()
            count += 1
        # Remove empty shard directories.
        for child in sorted(self._dir.iterdir(), reverse=True):
            if child.is_dir() and not any(child.iterdir()):
                child.rmdir()
        return count

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        entries = 0
        total_bytes = 0
        if self._dir.is_dir():
            for json_file in self._dir.rglob("*.json"):
                entries += 1
                total_bytes += json_file.stat().st_size

        total_requests = self._hits + self._misses
        return {
            "entries": entries,
            "total_size_bytes": total_bytes,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total_requests if total_requests else 0.0,
        }

    # -- internal helpers ----------------------------------------------------

    def _path_for(self, key: CacheKey) -> Path:
        h = key.content_hash
        return self._dir / h[:2] / f"{h}.json"

    def _is_expired(self, entry: CacheEntry) -> bool:
        created = datetime.fromisoformat(entry.created_at)
        age = (datetime.now(timezone.utc) - created).total_seconds()
        return age > self._ttl

    @staticmethod
    def _serialize(entry: CacheEntry) -> dict[str, Any]:
        return {
            "key": asdict(entry.key),
            "created_at": entry.created_at,
            "stage_results": entry.stage_results,
        }

    @staticmethod
    def _deserialize(data: dict[str, Any]) -> CacheEntry:
        return CacheEntry(
            key=CacheKey(**data["key"]),
            created_at=data["created_at"],
            stage_results=data["stage_results"],
        )
