# Agents — py/cogant/cache

## Owner

Runtime Lead

## Responsibilities

Content-addressed JSON cache for pipeline stage results. Keys combine repository path, `sha256` of analyzed content, and COGANT version so unchanged trees reuse prior work.

## Coordination

Used by incremental ingest/analysis paths; default directory `~/.cache/cogant`. Atomic writes support concurrent readers.

## Files

- `store.py` — `CacheKey`, `CacheEntry`, `CacheStore`, `get_cache_dir`.
- `__init__.py` — re-exports public cache API.
