# Incremental Mode Benchmark

Measures the wall-time speedup of `cogant analyze --incremental <commit>`
against the full pipeline on a real-world Python repository.

## Setup

| Field | Value |
| --- | --- |
| Target repo | `../../evaluation/eval_repos/flask` (Flask, 83 Python files) |
| Stages run | `ingest`, `static`, `normalize`, `graph`, `translate`, `statespace`, `process` |
| Stages skipped | `dynamic`, `export`, `validate` (isolate compute path) |
| Host | macOS (darwin 25.4.0), Python 3.12 via `uv run` |
| Date | 2026-04-09 |
| Measurement | `time.perf_counter()` around `PipelineRunner.run` (excludes CLI startup) |

Each scenario is repeated 3–5 times and reported as the median.

## Scenario 1 — Full cache hit (no changes)

The user runs the pipeline once, then immediately runs it again with
`--incremental HEAD` and no source-file changes. Everything is served
from cache without re-parsing.

```
=== Baseline (no incremental, 3 runs) ===
  run 1: 0.529s
  run 2: 0.536s
  run 3: 0.556s

=== Incremental first run (cache miss, cold cache) ===
  time: 0.583s
  cache_hit: False

=== Incremental repeated runs (cache hit, no changes, 5 runs) ===
  run 1: 0.029s (cache_hit=True, reparsed=0/83)
  run 2: 0.027s
  run 3: 0.025s
  run 4: 0.026s
  run 5: 0.028s
```

| Metric | Value |
| --- | --- |
| Median baseline (full re-run) | **0.536s** |
| Median incremental full-hit | **0.027s** |
| **Speedup** | **19.64×** |
| Target | ≥5× |
| Status | PASS |

## Scenario 2 — Partial re-parse (1 file changed of 83)

A fresh copy of Flask is git-initialised, the cache is seeded with an
incremental run, then a single file (`src/flask/app.py`) is touched,
committed, and `--incremental HEAD~1` is run. Only the touched file
should hit the ingest → static → graph re-parse path.

```
=== Baseline (no incremental, 3 runs) ===
  run 1: 0.522s
  run 2: 0.537s
  run 3: 0.562s

=== Seed cache ===
  seed run: 0.584s

=== Incremental partial run (1 file changed, 5 runs) ===
  run 1: 0.100s (cache_hit=True, reparsed=1/83)
  run 2: 0.096s
  run 3: 0.097s
  run 4: 0.090s
  run 5: 0.091s
```

| Metric | Value |
| --- | --- |
| Median baseline (full re-run) | **0.537s** |
| Median incremental partial-hit | **0.096s** |
| Files re-parsed | 1 / 83 |
| **Speedup** | **5.57×** |
| Target | ≥2× |
| Status | PASS |

## Observations

- The **no-change** path is cheap because `PipelineRunner._incremental_preflight`
  short-circuits the run and returns the cached `stage_results` directly.
  The ~27 ms floor is git-diff plumbing, cache lookup, and JSON deserialise.
- The **partial** path still pays ingest + normalize + graph over the
  filtered file list, plus the downstream stages (`translate`,
  `statespace`, `process`) which currently re-run over the merged graph
  rather than being patched in place. Reducing those would push the
  partial speedup higher, but the 5.57× result already clears the target
  with margin.
- Baselines held steady at 0.52–0.56 s across both scenarios, indicating
  a stable measurement environment.
- The cache file for a full flask bundle is ~0.6 MB of JSON, so disk
  overhead is negligible compared to compute savings.

## Reproduction

From `projects_in_progress/cogant/cogant/`:

```bash
# CLI smoke (note: includes Python + typer startup ≈ 0.3 s)
uv run cogant translate ../../evaluation/eval_repos/flask \
    --incremental HEAD \
    --cache-dir /tmp/cogant_bench/cache \
    --skip dynamic,export,validate

# Programmatic (excludes CLI startup)
uv run python <<'PY'
from cogant.api.pipeline import PipelineConfig, PipelineRunner
cfg = PipelineConfig(
    incremental_since="HEAD",
    cache_dir="/tmp/cogant_bench/cache",
    output_dir="/tmp/cogant_bench/out",
    skip_stages=["dynamic", "export", "validate"],
)
runner = PipelineRunner()
bundle = runner.run("../../evaluation/eval_repos/flask", cfg)
print(bundle.metadata["incremental_stats"])
PY
```
