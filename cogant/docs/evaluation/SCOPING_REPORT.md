# COGANT Scope and Readiness Report

**Current package version:** v0.6.0
**Primary numeric source:** `cogant/evaluation/METRICS.yaml`
**Roundtrip ledger:** `cogant/evaluation/dataset/roundtrip_results.jsonl`

This report states the current scope of the project and the release evidence
that is checked into the repository. It intentionally avoids release
archaeology; use `git log` for provenance.

## Current Scope

COGANT translates software repositories into Active Inference-oriented GNN
artifacts through a reproducible static-analysis pipeline:

1. ingest source files;
2. parse and normalize a typed program graph;
3. apply 22 declarative translation rules to produce semantic mappings;
4. compile state-space variables and A/B/C/D matrices;
5. export GNN, JSON, GraphML, Parquet, HTML, and dashboard artifacts;
6. validate generated artifacts and expose provenance.

The project is strongest for Python static analysis and GNN export. JavaScript
and TypeScript support exist as forward parsers and cross-language fixtures, but
the native v0.6 release ledger is Python-centered.

## Current Evidence Snapshot

| Evidence area | Current checked-in status | Source |
|---|---:|---|
| Collected tests | 9691 | `METRICS.yaml` |
| Passing tests | 9687 | `METRICS.yaml` |
| Failing tests | 0 | `METRICS.yaml` |
| Line coverage | 95.55% | `METRICS.yaml` / `coverage.json` |
| mypy strict errors | 0 | `METRICS.yaml` |
| ruff violations | 0 | `METRICS.yaml` |
| Python source files | 231 | `METRICS.yaml` |
| Roundtrip targets | 24 | `METRICS.yaml` |
| Role-preserved targets | 22 | `METRICS.yaml` |
| Drift targets | 2 | `METRICS.yaml` |
| Failed targets | 0 | `METRICS.yaml` |
| Strict structural isomorphism | 0 | `METRICS.yaml` |

## Supported Claims

- The package has a deterministic Python pipeline from repository input to
  validated GNN bundle output.
- The default translation engine registers 22 concrete rules across structural,
  semantic, control, behavioral, and resilience families.
- The native v0.6 roundtrip ledger in `METRICS.yaml` reports the current
  role-preserved, drift, and failed target counts.
- Strict structural isomorphism is not achieved by the checked-in ledger.
- The forward external-repository fixture completes on eight Python libraries,
  but its dulwich row remains a scaling caveat until that fixture is rerun.

## Out of Scope for Current Claims

- Whole-program semantic soundness.
- General claims about all Python repositories or all programming languages.
- Learned confidence calibration against a human-labeled corpus.
- Strict PutGet/GetPut lens laws.
- Production security for the packaged demo server; it requires deployment
  behind the user's own TLS, authentication, and reverse proxy.

## Release Gaps

| Gap | Why it matters | Needed evidence |
|---|---|---|
| Two drift targets (`cli_tool`, `notebook_module`) | The current roundtrip ledger is not all role-preserved | Reverse-synthesis or role-mapping fixes plus regenerated native ledger |
| 0 strict structural isomorphism rows | Strict roundtrip wording is unsupported | Structural-invariant preservation or narrower published claim |
| External-repository fixture needs refresh | The checked-in fixture predates the post-fix dulwich scaling target | Rerun `REAL_WORLD_EVAL.md` fixture and commit updated JSON |
| Confidence calibration remains unlearned | Rule scores are principled defaults, not empirical precision estimates | Human-labeled corpus and calibration report |
| JS/TS release evidence is incomplete | Cross-language docs should not imply parity with Python | Native JS/TS roundtrip ledger and CI gate |

## Validation Commands

```bash
uv run python tools/check_metrics_fresh.py
uv run python tools/audit_docs_constants.py
uv run python tools/audit_manuscript_numbers.py
uv run python tools/audit_manuscript_crossrefs.py
uv run python tools/audit_manuscript_citations.py
uv run --directory cogant python docs/verify_doc_links.py
uv run --directory cogant python docs/verify_manuscript_links.py
uv run python tools/claim_ledger.py --manuscript-dir manuscript --output-dir /tmp/cogant_claim_ledger --fail-on-literal-numbers
```
