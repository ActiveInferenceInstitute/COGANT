# Current Status

This directory now contains only live planning guidance for the COGANT working
checkout. The active project state is defined by source files, generated
metrics, manuscript source, and validation gates listed in [`../ISA.md`](../ISA.md).

## Active Work Rules

- Re-run the relevant gate before relying on any generated number.
- Keep command output in `_artifacts/` only when it is needed to explain an
  active review decision.
- Prefer generator and test changes over narrative-only edits when a claim can
  be checked mechanically.
- Use `README.md`, `AGENTS.md`, `manuscript/`, `cogant/docs/`, and
  `cogant/evaluation/METRICS.yaml` as the public-facing contract.

## Current Evidence To Refresh

The roundtrip ledger, metrics YAML, injected manuscript tree, claim ledger, and
package test suite must be refreshed together before release-style conclusions.
