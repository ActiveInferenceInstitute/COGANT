# COGANT v0.2.0-rc1 — Release Notes

**Release date:** 2026-04-09
**Status:** Release Candidate 1 (Alpha)
**Wheel:** `cogant-0.2.0rc1-py3-none-any.whl`

## What's New

COGANT v0.2.0-rc1 completes the round-trip story that v0.1.0 only sketched. The
forward pipeline (code → GNN) now has a symmetric reverse pipeline (GNN → code):
a new `cogant.reverse` subpackage parses GNN markdown, plans a Python package
layout, and synthesizes an idempotent Python package whose re-ingestion recovers
the original roles up to an ε-bounded roundtrip error. The ISOMORPHISM_THEOREM
document formalizes this as a Galois connection between source repositories and
GNN state-space representations, with a proof sketch and measured error bounds
on the 6-fixture evaluation set.

Beyond the reverse pipeline, this release focuses on turning COGANT from a
research prototype into something practitioners can actually run. The CLI gains
`cogant doctor`, `cogant init`, and `cogant explain` (rule-level attribution for
every AI role assignment), a composable pydantic config system replaces the
previous YAML sprawl, and 16 mkdocs-material documentation sections plus 6
Jupyter tutorial notebooks give new users an on-ramp. The test suite now sits
at 1072+ tests with zero failures (56 skipped for optional deps), a Hypothesis
fuzz harness hardens the translation rules, and the package ships a `py.typed`
marker for PEP 561 compliance.

On the rigor side, we audited COGANT against the Active Inference Institute's
GNN specification, found and fixed 3 non-conformances (DiscreteTime token
split, bare variable names in connections, ActionRule edge-based fallback),
published v0.1 of a labeled ML dataset (6 fixtures, node-level role labels,
HuggingFace-style card), and ran the full COGANT pipeline end-to-end on 8
real-world open-source Python repositories to catch pipeline edge cases that
synthetic fixtures never exercise.

## Breaking Changes

None. v0.2.0-rc1 is additive over v0.1.0:
- All v0.1 CLI subcommands keep the same flags and exit codes.
- The forward pipeline output schema is unchanged (ingest → static → normalize
  → graph → translate → export).
- New subcommands (`reverse`, `explain`, `doctor`, `init`) are additive.
- Config files from v0.1 continue to load; new pydantic config system is
  opt-in and backwards compatible.

## Install

From the built wheel:

```bash
pip install cogant-0.2.0rc1-py3-none-any.whl
```

With optional extras:

```bash
pip install 'cogant[viz]-0.2.0rc1-py3-none-any.whl'        # plotly + matplotlib
pip install 'cogant[multilang]-0.2.0rc1-py3-none-any.whl'  # tree-sitter JS/TS
pip install 'cogant[all]-0.2.0rc1-py3-none-any.whl'        # everything
```

Verify:

```bash
python -c "import cogant; print(cogant.__version__)"   # -> 0.2.0rc1
cogant doctor                                          # environment check
cogant --help                                          # subcommand list
```

Requires Python >=3.11.

## Known Limitations

- **Roundtrip fidelity on event-driven pipelines.** The `event_pipeline` fixture
  currently achieves only 47.6% role match after a full
  code→GNN→code roundtrip. Tracked as `test_event_pipeline_roundtrip`
  (xfail); fan-out synthesis is a known v0.1 synthesizer limitation slated for
  v0.2.0 final.
- **Rust hot path is a stub.** The `bench/` crate and `cogant._rust` extension
  module expose the build scaffolding and a `get_version()` symbol, but the
  Rust-accelerated graph kernels are not yet wired into the forward pipeline.
  All timings in the benchmark harness currently reflect pure-Python
  execution.
- **ML dataset is small.** Dataset v0.1 ships 6 fixtures with node-level role
  labels. It is large enough for smoke tests and calibration but too small for
  supervised role-classifier training.
- **Multilang substrate is Python-complete, JS/TS-partial.** The tree-sitter
  JS/TS parsers are wired in but only a subset of translation rules have
  JS/TS-equivalent patterns; expect reduced coverage on non-Python repos.
- **mkdocs site is built but not deployed.** The GitHub Pages deploy workflow
  exists; the site has not yet been published to a stable URL.
- **Subjective calibration.** The `CALIBRATION.md` document lists per-rule
  confidence scores derived from 6-fixture agreement. These should be
  treated as indicative until the dataset grows.

## Next Steps Toward v0.2.0 Final

1. Close `test_event_pipeline_roundtrip` fan-out xfail.
2. Wire at least one Rust kernel into the forward pipeline and publish a
   before/after benchmark.
3. Grow the ML dataset to 20+ fixtures with inter-annotator agreement.
4. Deploy the mkdocs site to GitHub Pages.
5. Tag `v0.2.0` once the RC has soaked for 1-2 weeks with no P0/P1 issues.
