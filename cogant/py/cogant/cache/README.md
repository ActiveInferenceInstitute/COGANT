# `cogant.cache`

Content-addressed on-disk cache used by incremental pipeline runs
(`PipelineConfig.incremental_since`). Stage outputs are keyed on
`sha256` of the inputs so re-running an unchanged repository skips
ingest / static / graph and reuses the previous bundle.

## Public API

Re-exported from `cogant/cache/__init__.py`:

| Symbol | Role |
| --- | --- |
| `CacheStore` | Filesystem-backed cache with `get` / `put` / `clear` / `prune`. |
| `CacheKey` | Content hash + namespace + version, suitable as a dict key. |
| `CacheEntry` | Wrapped value + metadata (`created_at`, `bytes`, `hits`). |
| `get_cache_dir()` | Resolves the active cache root, honoring `cache_dir` overrides and the `~/.cache/cogant` default. |

## Storage layout

```
~/.cache/cogant/
├── bundles/   <sha>.json      previous PipelineRunner outputs
└── meta/      <sha>.json      sidecar metadata for prune / hit counts
```

## Conventions

* Cache hits are decided per-file: only Python files that changed
  between `incremental_since` and `HEAD` are re-parsed.
* `incremental_stats` on `bundle.metadata` records `cache_hit`,
  `files_total`, `files_reparsed`, and a free-form `reason` so audits
  can confirm the cache fired.
* `cache_dir=` in `PipelineConfig` redirects the root for tests and
  benchmarks without touching the user's home dir.

See [`AGENTS.md`](AGENTS.md) for invariants and
[`../api/AGENTS.md`](../api/AGENTS.md) for how the runner consults the
cache.
