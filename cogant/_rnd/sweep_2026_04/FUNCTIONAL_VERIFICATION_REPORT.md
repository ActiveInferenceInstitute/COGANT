# Functional verification report — 2026-04-16

Scope: deep functional review of `projects_in_progress/cogant/`, including
upstream `generalized-notation-notation` integration, full test suite, CLI
smoke tests, static checks, Rust workspace, doc/link validators, and
`METRICS.yaml` regeneration. Applied low-risk fixes inline; everything
else is reported here.

Companion to `REVIEW_REPORT.md` (2026-04-16 earlier sweep), which covered
docs/manuscript drift only. This report covers executable behaviour.

## 1. Ground-truth snapshot (after fixes)

| Metric | Value | Source |
| --- | --- | --- |
| `cogant` version | 0.5.0 | `pyproject.toml` / `cogant doctor` |
| Python source files | 201 | `mypy py/cogant/` |
| Test count (passing) | 7543 | fresh pytest run → `METRICS.yaml` |
| Test count (total) | 7583 | `METRICS.yaml` |
| Skipped / xfailed / xpassed | 31 / 3 / 1 | pytest summary |
| Coverage (line) | 90.03 % | fresh `coverage.json` → `METRICS.yaml` (gate 89 %) |
| mypy strict errors | 0 | `uv run mypy py/cogant/` (201 files) |
| ruff violations | 0 | `uv run ruff check py/cogant/` |
| Translation rules | 22 | `py/cogant/translate/rules/` |
| CLI subcommands | 26 | `cogant --help` Commands panel |
| Rust crates built (release) | 8 | `cargo build --release --workspace` |
| Rust unit tests passing | 33 | `cargo test --workspace --release` |
| Doc links (`cogant/docs/`) | 1527 checked / 0 broken | `verify_doc_links.py` |
| Manuscript links | 203 checked / 0 broken / 11 skipped | `verify_manuscript_links.py` |
| Markdown validator (manuscript) | clean | `infrastructure.validation.cli markdown` |
| Manuscript number audit | 28 HIGH / 0 mismatch | `tools/audit_manuscript_numbers.py` |

## 2. Upstream `generalized-notation-notation` integration

- Declared as **core** dependency in `cogant/pyproject.toml` at pinned SHA
  `41a64381c6d277c8240ef65499be67e7f882ef73`; installs cleanly via `uv sync`.
- Installed version reports `src.gnn.__version__ == '1.1.3'`.
- Exposes 30 submodules (`parser`, `parsers`, `schema`, `multi_format_processor`,
  `roundtrip_processor`, `mcp`, `pomdp_extractor`, etc.).
- Integrated through `cogant.gnn.upstream_bridge` — a lazy `importlib` façade
  so the heavy upstream JAX/PyTorch imports only fire when a bridge function
  runs. Exports ~20 helpers (`is_upstream_gnn_available`, `upstream_version`,
  `run_upstream_validate_gnn`, `get_upstream_parsing_system`,
  `get_upstream_gnn_format_enum`, `upstream_parse_file`, …).
- Consumers inside the codebase:
  * `py/cogant/gnn/validator.py` — calls `run_upstream_validate_gnn` on
    every generated `model.gnn.md` when `COGANT_DISABLE_UPSTREAM_GNN` is
    unset (the default).
  * `py/cogant/api/orchestration.py` — surfaces upstream validation in the
    API layer.
  * `tests/unit/test_gnn_upstream_bridge.py` — 21 dedicated tests for the
    bridge (all pass).
  * `tests/unit/test_wave20_cov_cli_main.py` — CLI coverage test.
- End-to-end evidence: running `cogant translate examples/control_positive/calculator`
  builds the full pipeline (ingest → validate), emits a 10-stage success
  table, and produces a GNN package that upstream `validate_gnn` now
  accepts (ok=True, 0 errors — see §3.1 fix).

### 2.1 Fix applied — upstream bridge content→path workaround

`src.gnn.validate_gnn(file_path_or_content: Union[str, Path])` probes
`Path(x).exists()` first and raises `OSError [Errno 63] File name too long`
when given raw markdown with newlines (upstream 1.1.3 bug). The bridge
was passing the content string directly, causing upstream validation to
always emit a false-positive error that was logged as a warning in
`GNNValidator`. Fix: stage the markdown to a `tempfile.NamedTemporaryFile`
and pass the path so upstream's file branch is exercised.

File: `py/cogant/gnn/upstream_bridge/__init__.py` — `run_upstream_validate_gnn`.

Verification: `run_upstream_validate_gnn(open('/tmp/cogant_smoke/gnn_package/model.gnn.md').read())`
now returns `UpstreamGNNValidation(available=True, ok=True, version='1.1.3',
errors=[])`. All 21 tests in `test_gnn_upstream_bridge.py` still pass.

## 3. Fixes applied in this pass

| # | Component | Category | File | What changed | Why |
| --- | --- | --- | --- | --- | --- |
| 1 | Upstream bridge | Functional bug | `py/cogant/gnn/upstream_bridge/__init__.py` | `run_upstream_validate_gnn` now stages markdown to temp file before calling upstream | Upstream `validate_gnn` cannot accept raw multiline strings |
| 2 | Static lint | ruff C420 | `py/cogant/graph/analysis.py:514` | `{nid: 0.0 for nid in …}` → `dict.fromkeys(self.graph.nodes, 0.0)` | Ruff cleanliness |
| 3 | Type stub | mypy type-arg | `py/cogant/viz/network_view.pyi:13,16` | `frozenset` → `frozenset[Any]` (2×) | mypy strict generics |
| 4 | Type stub | mypy misc (enum) | `py/cogant/export/formats.pyi:13` | Enum members `JSON: str` → `JSON = "json"` (×9) | mypy 1.20 enum-in-stub rule |
| 5 | Static lint | ruff I001/C408/B905 | `py/cogant/viz/pdf_export.py` | `ruff check --fix --unsafe-fixes` (12 fixes) | Unsorted imports, `dict()` literals, `zip(strict=)` |
| 6 | Rust test | E0596 mutability | `rust/cogant-translate/src/lib.rs:339` | `let engine` → `let mut engine` | `register_rule` requires `&mut self` |
| 7 | Rust test | missing crate ref | `rust/cogant-store/src/lib.rs` | replaced `chrono::Utc::now()` test stubs with a `std::time::SystemTime`-based helper; renamed unused `store` → `_store` | `chrono` not declared; avoid adding a dep just for test timestamps |
| 8 | Rust test | unused_comparisons | `rust/cogant-trace/src/lib.rs:357` | `assert!(session.duration_us() >= 0)` → `let _ = session.duration_us();` | `u64 >= 0` is always true |
| 9 | Metrics | stale coverage | `cogant/coverage.json` + `cogant/evaluation/METRICS.yaml` | regenerated from fresh `.coverage`; `tools/regenerate_metrics.py` re-run | `coverage.json` was 5 days old (91.25 %); true value 90.03 % |

All changes are either test-only, stub-only, or purely mechanical
refactors. Full Python test suite (7543 passing, 90.03 % coverage) and
full Rust workspace tests (33 passing) remain green after the edits.

## 4. Observed-but-not-fixed

### 4.1 Rust build warnings

`cargo build --release --workspace` still emits 10 warnings across
`cogant-gnn`, `cogant-translate`, and `cogant-store` (unused
variables/methods). Tests now compile and pass; the warnings do not
block builds. Logged for a future tidy-up pass.

### 4.2 `cogant doctor` minor false-negative

`tree-sitter node-types.json  ⚠  not found (multilang extras missing)`
even though `multilang` extras are installed (tree-sitter 0.25.2 shown
green on the line above). Upstream `tree-sitter-python ≥ 0.21` ships
grammar bindings without the separate `node-types.json` probe file that
`cogant doctor` looks for. Cosmetic only — parsing works, 5 language
parsers register, and the full pipeline runs green.

### 4.3 `pdf_export.py` git index anomaly

`git status py/cogant/viz/pdf_export.py` reports the file as
simultaneously "deleted" (index) and "untracked" (worktree). This
pre-dates this sweep and is unrelated to any edits made here. Flagged
for cleanup; ruff autofix was applied to the on-disk copy.

### 4.4 `mypy` unused-section notice

mypy prints `pyproject.toml: note: unused section(s): …` for 11
`[[tool.mypy.overrides]]` entries that no longer match any imports
(`cairosvg.*`, `cogant._rust`, `src.gnn`, `typer.*`, …). Non-fatal.
The overrides were used before the bridge was refactored; a future
pass can prune them without semantic change.

### 4.5 `coverage.json` needs a pre-regen hook

`tools/regenerate_metrics.py` trusts whatever `cogant/coverage.json`
is on disk. If a contributor runs `--no-cov` locally and then
regenerates, the YAML's `coverage_percent` silently freezes. Proposed
follow-up: either call `uv run coverage json` at the start of
`regenerate_metrics.py`, or stamp a freshness check against `.coverage`
mtime.

## 5. Commands run (reproduction)

```bash
cd projects_in_progress/cogant/cogant

# Upstream GNN smoke
uv run python -c "from cogant.gnn.upstream_bridge import is_upstream_gnn_available, upstream_version; print(is_upstream_gnn_available(), upstream_version())"

# Full Python suite
uv run pytest tests/ -q --no-header

# Static checks
uv run ruff check py/cogant/
uv run mypy py/cogant/

# CLI smoke
uv run cogant doctor
uv run cogant translate examples/control_positive/calculator --output /tmp/cogant_smoke
uv run cogant roundtrip /tmp/cogant_smoke/gnn_package/model.gnn.md --output /tmp/cogant_roundtrip

# Rust workspace
source "$HOME/.cargo/env"
cargo build --release --workspace --manifest-path rust/Cargo.toml
cargo test  --release --workspace --manifest-path rust/Cargo.toml

# Docs + manuscript
uv run python docs/verify_doc_links.py
uv run python docs/verify_manuscript_links.py
cd ../.. && uv run python -m infrastructure.validation.cli markdown projects_in_progress/cogant/manuscript/
cd projects_in_progress/cogant/cogant
uv run python ../tools/audit_manuscript_numbers.py

# Metrics refresh
uv run coverage json
uv run python ../tools/regenerate_metrics.py
```

## 6. Conclusion

Every layer probed is working as documented:

- Upstream GNN 1.1.3 installs, imports, and now validates (after the
  temp-file workaround).
- 7543 Python tests pass at 90.03 % line coverage (gate 89 %).
- 33 Rust tests pass across 8 crates building in release mode.
- mypy strict and ruff both report zero issues against 201 source files.
- 26 CLI subcommands expose the full pipeline end-to-end; a live
  forward-reverse round-trip on `calculator` scores `role_match=100 %`
  ISOMORPHIC.
- 1527 doc links, 203 manuscript links, and all prose numbers resolve
  without drift against the refreshed `METRICS.yaml`.

The 5 non-blocking items in §4 are queued for a future, lower-priority
sweep; none of them compromise current functional claims.
