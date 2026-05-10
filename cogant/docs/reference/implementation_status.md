## Implementation status

Authoritative for **what is wired in the Python package today** (see `py/cogant/api/orchestration.py`). Broader language claims elsewhere in this document may be **aspirational** until noted here.

| Area | Status | Location / notes |
| --- | --- | --- |
| Repository ingest + file enumeration | Implemented | `cogant.ingest`, `FileEnumerator`, `RepoIngester` |
| Python AST extraction | Implemented | `cogant.static.parser.PythonASTParser` |
| Canonical normalization + graph builder | Implemented | `normalize/`, `graph/builder.py` |
| Pipeline + Session orchestration | Implemented | `api/orchestration.py`, `api/pipeline.py`, `api/session.py` |
| Translation rules + confidence | Partial | `translate/` — 22 shipped declarative rules with fixpoint + conflict resolution; many repositories exercise only a structural subset, so mapping counts vary by project shape (see `docs/rules/`). |
| State space + process extraction | Partial | `statespace/compiler.py`, `process/extractor.py` — **implemented**; “partial” means not every codebase yields full behavioral fidelity without dynamic traces or optional parsers. |
| CLI | Implemented | `cogant.cli.main` |
| Export stage (`gnn_package/`) | Implemented | `api/orchestration.run_export`: writes JSON artifacts and builds `output_dir/gnn_package/` when graph + state space + process model + `_semantic_mappings` dict are available; failures are non-fatal (warnings) |
| CLI `validate` | Implemented | Bundle file, `gnn_package` directory, run dir with `gnn_package/` or `bundle.json`; see [CLI_GUIDE § validate](../cli/README.md) |
| Rust crates / native acceleration | Shipped (partial acceleration) | Workspace under `rust/`: **eight crates** (`cogant-core`, `cogant-graph`, `cogant-translate`, `cogant-statespace`, `cogant-store`, `cogant-trace`, `cogant-gnn`, `cogant-ffi`) with PyO3 in `cogant-ffi`. `METRICS.yaml` reports `rust.ffi_available` when the extension built. Today **Python remains the default path** for most stages; the FFI accelerates **connected components** and related entry points (see `cogant.__rust_version__`, `cogant doctor`, `COGANT_USE_RUST`). Full “Rust on all hot paths” is ongoing; `COGANT_USE_RUST=0` forces pure-Python for A/B tests. |
| Additional language front-ends | Partial | **Python** is first-class. **JS/TS** (and other tree-sitter grammars) are **optional**: install `cogant[multilang]` and an available grammar; parity is exercised in integration tests when those pieces are present. Further front-ends (e.g. Java) remain **planned** — see `parsers/*`, roadmap. |
