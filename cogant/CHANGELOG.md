# CHANGELOG

## [0.2.0-rc1] - 2026-04-09

### Added
- cogant.reverse: GNN markdown parser + package synthesizer (parser.py, planner.py, synthesizer.py, idempotency.py)
- cogant explain subcommand: rule-level attribution for AI role assignments
- cogant doctor + cogant init ergonomics subcommands
- Composable pydantic config system (cogant/config/)
- Hypothesis fuzz harness (tests/fuzz/)
- 16 mkdocs-material documentation sections
- 6 Jupyter tutorial notebooks
- ML dataset v0.1: 6 fixtures with node-level role labels (HuggingFace card)
- ISOMORPHISM_THEOREM.md: Galois connection proof + ε-bounded roundtrip error
- GNN spec compliance: 3 AII non-conformances found and fixed
- Real-world evaluation: COGANT pipeline on 8 open-source Python repos
- Rust benchmark infrastructure (bench/ crate stubs)

### Changed
- Docs: complete README rewrite for v0.1.0→v0.2.0 feature set
- Test suite: 1072+ tests, 0 failures (56 skipped for optional deps)
- py.typed marker added (PEP 561 compliance)

### Fixed
- ActionRule: extended with encode/decode/dump/load keywords + ≥2 WRITES edge fallback
- SemanticMapping export: mapping.kind.value (was incorrect attribute access)
- PNG tests: matplotlib-dependent tests properly skipped when cogant[viz] not installed
- GNN upstream formatter: DiscreteTime token split, bare variable names in connections

## [0.1.0] - 2026-04-08

Initial R&D release: forward pipeline (ingest→static→normalize→graph→translate→export), 19 translation rules, 7 semantic roles, Markov blanket partition.
