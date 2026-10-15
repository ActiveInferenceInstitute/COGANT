# GNN Upstream Audit Surface (generalized-notation-notation 4.1.0)

## Claim Boundary

This report separates version currentness, COGANT-owned GNN method health, selected upstream pipeline execution, and supply-chain state. A high COGANT validator score is not an all-25 upstream execution claim.

## Release Evidence

| Field | Value |
| --- | --- |
| Pinned commit (`cogant/pyproject.toml`) | `46459949944e3217f8a6a804d4ff8c52829ef275` |
| Locked version / commit (`cogant/uv.lock`) | `4.1.0` / `46459949944e3217f8a6a804d4ff8c52829ef275` |
| Installed commit | `46459949944e3217f8a6a804d4ff8c52829ef275` |
| Distribution version | `4.1.0` |
| Engine version (`gnn.__version__`) | `4.1.0` |
| Release tag commit (informational) | `v4.1.0` -> `9255e19f951d4c9c1461514464d420bd3fc8b912` |
| Upstream default-branch HEAD (informational) | `46459949944e3217f8a6a804d4ff8c52829ef275` |
| Bridge import (`cogant.gnn.upstream_bridge`) | PASS |
| Negative control (clean `import src.gnn` fails) | PASS |

## Verdicts

- Version and bridge currentness: PASS
- Single-file validation of the translated model: PASS
- Selected upstream steps: 20/20 succeeded (upstream overall status `SUCCESS_WITH_WARNINGS`)
- Supply-chain scan: PASS

## Single-File Validation

| Validator | Level | Verdict | Detail | Errors |
| --- | --- | --- | --- | --- |
| cogant GNNValidator | package | PASS | score 100.0/100 | 0 |
| upstream validate_gnn_syntax | standard | PASS | upstream 4.1.0 | 0 |
| upstream validate_gnn_syntax | strict | PASS | upstream 4.1.0 | 0 |

## Selected Upstream Steps

| Step | Script | Status | Duration (s) | Reason |
| --- | --- | --- | --- | --- |
| 0 | `0_template.py` | SUCCESS | 0.1 |  |
| 3 | `3_gnn.py` | SUCCESS | 0.2 |  |
| 4 | `4_model_registry.py` | SUCCESS | 0.1 |  |
| 5 | `5_type_checker.py` | SUCCESS_WITH_WARNINGS | 1.0 |  |
| 6 | `6_validation.py` | SUCCESS | 0.3 |  |
| 7 | `7_export.py` | SUCCESS | 0.2 |  |
| 8 | `8_visualization.py` | SUCCESS | 6.3 |  |
| 9 | `9_advanced_viz.py` | SUCCESS_WITH_WARNINGS | 10.1 |  |
| 10 | `10_ontology.py` | SUCCESS | 0.1 |  |
| 14 | `14_ml_integration.py` | SUCCESS | 0.1 |  |
| 15 | `15_audio.py` | SUCCESS | 0.2 |  |
| 16 | `16_analysis.py` | SUCCESS_WITH_WARNINGS | 0.9 |  |
| 17 | `17_integration.py` | SUCCESS | 0.4 |  |
| 18 | `18_security.py` | SUCCESS_WITH_WARNINGS | 0.1 |  |
| 19 | `19_research.py` | SUCCESS | 0.1 |  |
| 20 | `20_website.py` | SUCCESS | 0.2 |  |
| 21 | `21_mcp.py` | SUCCESS | 1.5 |  |
| 22 | `22_gui.py` | SUCCESS | 0.1 |  |
| 23 | `23_report.py` | SUCCESS | 0.2 |  |
| 24 | `24_intelligent_analysis.py` | SUCCESS | 0.1 |  |

Steps outside the bridge selection: 1, 2, 11, 12, 13.

## Interpretation

COGANT-owned validation/type-check/export/roundtrip/runner paths can be green while selected optional upstream pipeline steps fail. Steps outside the bridge selection are not part of the all-step gate, even when upstream ran them as prerequisites. Manuscript and docs should state that boundary explicitly.
