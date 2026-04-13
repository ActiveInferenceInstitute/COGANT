"""Content-addressed result cache for COGANT.

Avoids redundant re-analysis of unchanged repositories by caching stage
results keyed on ``sha256(file_contents)``.
"""

from cogant.cache.store import CacheEntry, CacheKey, CacheStore, get_cache_dir

__all__ = ["CacheEntry", "CacheKey", "CacheStore", "get_cache_dir"]
