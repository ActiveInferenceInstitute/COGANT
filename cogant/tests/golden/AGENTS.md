# `tests/golden`

Golden-file regression tests. Each test loads a JSON snapshot from
this directory (the "golden" expectation), runs the corresponding
COGANT path live, and asserts that the live output still satisfies
the recorded contract.

## Layout

| Path | Role |
| --- | --- |
| `test_bundle_json_schema.py` | Asserts the canonical top-level keys of `Bundle.save_json()`. |
| `roundtrip/` | Per-fixture roundtrip snapshots (`<fixture>.json`). Each holds the documented original-role multiset, minimum synthesized-role floor, expected `shape_match`, `min_role_match_score` compatibility floor, and v0.6 `must_be_role_preserved` status. Consumed by `tests/integration/test_roundtrip_stability_gaps.py::TestGoldenRoundtripOutputs`. |
| `README.md` | High-level overview. |

## Snapshot conventions

* Goldens encode **floors and minimums**, not exact equality. The
  pipeline legitimately over-emits some role kinds (e.g. CONSTRAINT,
  POLICY, CONTEXT mappings the source GNN didn't declare); strict
  equality would be brittle.
* Each snapshot includes a `notes` field explaining why the floors are
  what they are so future updates have context.
* When a golden needs to change, update the snapshot in the same
  commit as the code change and explain the rationale in
  `CHANGELOG.md`. Goldens are version-controlled expectations — never
  auto-regenerate them in CI.

## Adding a new golden

1. Pick a stable fixture (under `examples/zoo/` or
   `examples/control_positive/`).
2. Run the live path once, capture the output, and trim it to the
   minimum invariants you want to lock in.
3. Drop the snapshot under the appropriate subdirectory and reference
   it from a parametrised test in `tests/integration/` or
   `tests/golden/`.

Parent: [`../AGENTS.md`](../AGENTS.md).
