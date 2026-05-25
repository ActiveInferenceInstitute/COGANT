# Agents - tests/golden/roundtrip

## Scope

Golden roundtrip expectation files consumed by
`tests/integration/test_roundtrip_stability_gaps.py`.

## Rules

- Keep field names backward-compatible unless the corresponding tests and docs change in the same pass.
- Use `role_preservation_score` / role-preserved language for v0.6 semantics; strict structural isomorphism is a separate status.
- Run from the package root:

```bash
uv run pytest tests/integration/test_roundtrip_stability_gaps.py -q --no-cov
```
