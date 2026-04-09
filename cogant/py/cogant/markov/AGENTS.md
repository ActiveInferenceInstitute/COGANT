# AGENTS — cogant.markov

This folder owns Markov-blanket extraction. Keep it pure and
graph-theoretic: no language- or domain-specific heuristics belong
here. If you need to bias the partition toward certain code patterns,
do it via a seed strategy in `extractor.py`, not by mutating the
`partition_by_seeds` primitive in `blanket.py`.

## Responsibilities

- `blanket.py` — data model (`MarkovBlanket`, `BlanketRole`),
  deterministic partitioning primitive, JSON serializer.
- `extractor.py` — seed-selection strategies and the user-facing
  `MarkovBlanketExtractor.extract` API.
- `network.py` — collapsed four-role aggregate view for visualization.

## Invariants

- Every node in the input `ProgramGraph` receives exactly one role.
- The partition is deterministic for the same `(graph, seeds)` pair.
- Serialization must be JSON-safe (no enums, no dataclasses at leaves).
- `MarkovBlanket.metadata["strategy"]` records which seed strategy was
  used so downstream diffing tools can compare apples to apples.
- New seed strategies must be added to `SeedStrategy` and to the
  `extract` dispatcher; the strategy name has to appear in the
  module docstring table and in `README.md`.

## Don't

- Do not import from `cogant.gnn`, `cogant.viz`, or other downstream
  packages — those depend on `cogant.markov`, not the other way round.
- Do not mutate the input graph.
- Do not assume `NodeKind` or `EdgeKind` values beyond what
  `cogant.schemas.core` exports.

## Tests

Unit tests live under `tests/markov/`. At minimum cover:
- A minimal hand-built graph where the partition is known by inspection.
- Every seed strategy at least once.
- Round-trip through `serialize_blanket` → JSON → parse.
