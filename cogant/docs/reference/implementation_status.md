## Implementation status

Authoritative for **what is wired in the Python package today** (see `py/cogant/api/orchestration.py`). Broader language claims elsewhere in this document may be **aspirational** until noted here.

| Area | Status | Location / notes |
| --- | --- | --- |
| Repository ingest + file enumeration | Implemented | `cogant.ingest`, `FileEnumerator`, `RepoIngester` |
| Python AST extraction | Implemented | `cogant.static.parser.PythonASTParser` |
| Canonical normalization + graph builder | Implemented | `normalize/`, `graph/builder.py` |
| Pipeline + Session orchestration | Implemented | `api/orchestration.py`, `api/pipeline.py`, `api/session.py` |
| Translation rules + confidence | Partial | `translate/` (rules apply to built graphs; coverage varies by repo) |
| State space + process extraction | Partial | `statespace/compiler.py`, `process/extractor.py` |
| CLI | Implemented | `cogant.cli.main` |
| Export stage (`gnn_package/`) | Implemented | `api/orchestration.run_export`: writes JSON artifacts and builds `output_dir/gnn_package/` when graph + state space + process model + `_semantic_mappings` dict are available; failures are non-fatal (warnings) |
| CLI `validate` | Implemented | Bundle file, `gnn_package` directory, run dir with `gnn_package/` or `bundle.json`; see [CLI_GUIDE § validate](../cli/README.md) |
| Rust crates / native acceleration | Planned / staged | `rust/` |
| Additional language front-ends (JS, Java, …) | Planned | `parsers/*`, roadmap |

