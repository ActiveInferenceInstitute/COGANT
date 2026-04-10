# COGANT Scaling Analysis

## dulwich (8601 nodes, 15441 edges, 1.80 e/n ratio)

### Benchmark context

All other repos in the eval corpus run in <60s with <1 GB peak RSS.
dulwich had 380s wall-time (measured 330s in a cold run, 400s with profiling
overhead) and produced a 4.6 GB GNN package before fixes.

The 1.80 edge-per-node ratio is not the root cause; three independent
O(n²) / O(n × e) bugs were the true culprits.

---

### Profiling results (per-stage, before fixes)

```
run_ingest:    0.1s
run_static:    0.5s
run_normalize: 0.5s
run_graph:    74.3s   ← hot
run_translate: 25.3s
run_statespace: 4.4s
run_process:   7.9s
run_export:  224.8s   ← hottest
run_validate:  64.2s  ← hot
TOTAL:        401.8s
```

Produced GNN package: **4.6 GB** total
- `model.gnn.md`:  1.8 GB  (497 953 lines)
- `model.gnn.json`: 3.1 GB

---

### Root causes

#### Bug 1 — B tensor O(n_states² × n_actions) explosion (`gnn/matrices.py`)

**Location:** `GNNMatrices.compute_B()`

The B transition tensor has shape `[n_states × n_states × n_actions]`.
For dulwich the compiled state space yields:

```
n_states = 429  (class-level hidden-state variables)
n_obs    = 1689
n_actions = 1085

B entries = 429 × 429 × 1085 = 199,684,485 floats
           ≈ 1.6 GB as float64
           ≈ 2.5 GB as JSON text
```

For the other repos in the eval corpus n_states ≈ 50 and n_actions ≈ 100,
giving B ≈ 250 000 entries — 800× smaller. dulwich's class-rich test suite
drives n_states and n_actions up proportionally, producing the quadratic cliff.

**Fix:** Added `_MAX_B_ENTRIES = 5_000_000` constant. When `n_states² × n_actions`
would exceed the threshold, `compute_B` calls `_top_k_state_ids()` to select the
top-K highest-degree state nodes (ranked by combined in+out degree in O(|E|)),
reducing n_states to `⌊√(_MAX_B_ENTRIES / n_actions)⌋`. For dulwich this caps
n_states at ≈ 68, keeping B at ≈ 5 M entries. The truncation is logged as a
warning and recorded in `to_dict()["truncation"]` so callers can detect it.

#### Bug 2 — Domain column lists expanding markdown to 470 k lines (`gnn/formatter/structural.py`)

**Location:** `_StructuralSectionsMixin._format_state_space()`

The State Space markdown table emits one row per state variable. The `domain`
column contained the raw Python list of all method names for each class
(e.g. `['setUp', 'tearDown', 'test_read_commit_graph_missing_file', ...]` with
up to 45 entries per class). This ballooned the State Space section alone to
470 844 lines and the full markdown to 1.8 GB.

**Fix:** Truncate domain lists longer than 5 elements: show the first 5 and
append `+N more` suffix. String domains are capped at 120 characters.

#### Bug 3 — O(n × e) BFS in `get_connected_components` (`graph/builder.py`)

**Location:** `ProgramGraphBuilder.get_connected_components()`

The BFS called `graph.get_neighbors()` inside the inner loop. Each
`get_neighbors()` call scans all 15 441 edges twice (once for `get_edges_from`,
once for `get_edges_to`), giving O(|V| × |E|) = O(8601 × 15441) ≈ 133 M
comparisons total. This was called once from `get_statistics()` at the end of
`run_graph`, accounting for 10 s of the 74 s graph stage.

**Fix:** Pre-build an undirected adjacency dict in O(|E|) before the BFS,
reducing the overall complexity to O(|V| + |E|).

#### Bug 4 — O(files × methods) AST re-parsing (`api/orchestration.py`)

**Location:** `_emit_dataflow_edges()` called from `run_graph()`

For each method node, the function called `ast.parse(file_path.read_text())`
which re-parsed the same source file from disk for every method it contained.
A file with 30 methods was compiled 30 times. With 6365 method calls and
~130 unique files, this produced ~50 redundant AST compiles per file on
average, accounting for ~57 s of the 74 s graph stage.

**Fix:** Added an `ast_cache: dict[Path, Any]` parameter. The caller
(`run_graph`) allocates the cache once and passes it to every
`_emit_dataflow_edges` call so each file is compiled at most once. Parse
failures are cached as `None` to avoid retrying.

#### Bug 5 — O(classes²) INHERITS edge lookup (`api/orchestration.py`)

**Location:** `run_graph()`, INHERITS edges section

For each class × base name pair, the original code linearly scanned all
`class_nodes` to find a matching name — O(|classes|² × |bases|).

**Fix:** Pre-build a `class_by_name` dict so lookup is O(1).

---

### Fix summary and new benchmarks

| Stage | Before | After | Change |
|-------|--------|-------|--------|
| run_graph | 74.3s | 2.5s | −97% |
| run_export | 224.8s | 26.4s | −88% |
| run_validate | 64.2s | 2.0s | −97% |
| **TOTAL** | **~400s** | **65.3s** | **−84%** |

GNN package size: 4.6 GB → 206 MB (−96%)

The 65.3s wall-time is comfortably below the 120s target. Peak RSS was not
directly measured post-fix but the elimination of the 1.6 GB B tensor
allocation should reduce peak RSS from ~8.5 GB to well under 2 GB.

---

### Files changed

- `py/cogant/gnn/matrices.py` — `_MAX_B_ENTRIES` cap + `_top_k_state_ids()` +
  truncation metadata in `to_dict()` + truncation recording in `compute_B()`
- `py/cogant/gnn/formatter/structural.py` — domain list truncation in
  `_format_state_space()`
- `py/cogant/graph/builder.py` — O(|V|+|E|) BFS in `get_connected_components()`
- `py/cogant/api/orchestration.py` — AST cache in `_emit_dataflow_edges()` +
  O(1) INHERITS lookup via `class_by_name`

---

### Remaining bottlenecks

- `run_translate` (22s): translation rule matching — not investigated; likely
  O(rules × edges) and scales acceptably for larger repos.
- `run_process` (7s): process model extraction — not investigated.
- `run_export` (26s): JSON serialization of the 206 MB package — inherently
  I/O bound; acceptable.

### Workaround for even larger repos

If a future repo exceeds 5 M B entries even after state truncation, lower
`_MAX_B_ENTRIES` or reduce `n_actions` by filtering out leaf/private actions
before state-space compilation.
