# COGANT Real-World Forward-Pipeline Evaluation

**Evidence source:** `cogant/evaluation/real_world_eval_summary.json`
**Measured fixture date:** 2026-04-20
**Pipeline:** `cogant translate --no-dynamic`, followed by `cogant export-gnn --format markdown`

This page summarizes the checked-in external-repository forward-pipeline
fixture. It is a scaling and output-completeness fixture, not the native v0.6
roundtrip ledger. Release roundtrip counts come from
`cogant/evaluation/METRICS.yaml`.

## Scope

The fixture runs the forward graph-to-GNN path over eight Python libraries:
`flask`, `requests`, `httpx`, `fastapi`, `pydantic`, `click`, `rich`, and
`dulwich`. Each run records wall time, peak RSS, node/edge counts, bundle
creation, markdown export, required GNN section presence, A/B/C/D block
presence, and validator pass/fail status.

## Current Checked-In Results

| Repo | PyFiles | Nodes | Edges | Time(s) | Peak RSS(MB) | Required sections | A | B | C | D | Result |
|---|---:|---:|---:|---:|---:|:-:|---:|---:|---:|---:|:-:|
| flask | 83 | 978 | 1136 | 2.92 | 148.3 | 4/4 | 28 | 28 | 144 | 28 | pass |
| requests | 36 | 706 | 885 | 4.84 | 168.5 | 4/4 | 29 | 29 | 138 | 29 | pass |
| httpx | 60 | 1192 | 1525 | 4.10 | 236.2 | 4/4 | 60 | 60 | 259 | 60 | pass |
| fastapi | 1121 | 6050 | 5213 | 19.11 | 447.2 | 4/4 | 84 | 84 | 1700 | 84 | pass |
| pydantic | 402 | 8425 | 9318 | 49.38 | 1308.5 | 4/4 | 225 | 225 | 959 | 225 | pass |
| click | 63 | 1129 | 1426 | 4.01 | 220.9 | 4/4 | 52 | 52 | 249 | 52 | pass |
| rich | 213 | 2047 | 2542 | 8.50 | 521.5 | 4/4 | 123 | 123 | 418 | 123 | pass |
| dulwich | 233 | 8601 | 15441 | 380.02 | 8510.9 | 4/4 | 448 | 448 | 1687 | 448 | pass |

**Fixture result:** 8/8 completed with exit 0, each emitted a bundle, each
emitted GNN markdown, each populated all four required sections, and each had
non-empty A/B/C/D blocks.

## Interpretation

The fixture supports a forward-pipeline claim: COGANT can produce structurally
valid GNN bundles for a diverse set of external Python repositories. It does
not support a claim of semantic completeness, strict roundtrip isomorphism, or
performance readiness for all large repositories.

The dulwich row is the load-bearing caveat. It passes functionally, but the
checked-in fixture records 380.02 seconds and 8510.9 MB peak RSS. The current
scaling page documents the post-fix regression target and the remaining need
for a refreshed external-repository run.

## Reproduction Contract

Re-run the fixture from the package root with equivalent commands:

```bash
uv run cogant translate <repo-path> --no-dynamic -o <out-dir>
uv run cogant export-gnn <out-dir>/bundle.json --format markdown -o <markdown-out>
```

Then refresh `cogant/evaluation/real_world_eval_summary.json` and this page
together. Do not promote the checked-in external fixture to a roundtrip claim;
use `METRICS.yaml` for roundtrip status.
