# GNN conformance

`gnn conformance (pinned)` is defined in `.github/workflows/ci.yml` (job key
`gnn-conformance`, which runs the `gnn` arm of the root `run_gate.py`) and
`.github/gnn-pin.json` records
`ActiveInferenceInstitute/Generalized_Notation_Notation` at `v5.1.0`
(`75c834bd8519dc7b5adc4d24f16bf393cfd1ecdf`). The `gnn` arm calls
`python -m gnn.importers check --repo . --require-pointer --workflow .github/workflows/ci.yml --job gnn-conformance`
from the prepared upstream environment, with `--repo` anchored to the project
root. The shared reader owns pin, pointer and specification validation.

The job runs `uv sync --extra upstream --extra dev`, emits a package from
`cogant/examples/control_positive/calculator` with the pipeline runner, and
validates the resulting `gnn_package/model.gnn.md` at the `standard` and
`strict` levels of the pinned parser before running upstream steps 3, 5 and 6.
That probe is `cogant/scripts/gnn_conformance_probe.py`. It then runs `tests/unit/test_gnn_upstream_bridge.py`,
`tests/unit/test_gnn_upstream_bridge_contract.py`,
`tests/unit/test_upstream_pipeline_resolution.py` and
`tests/integration/test_upstream_gnn_pipeline.py`, then the audit-surface tests
in `tests/test_gnn_upstream_audit_surface.py`, and finishes with
`python ../tools/audit_release_integrity.py --no-openapi`. The shared reader
also discovers the repository's `*.gnn.md` specifications, including the zoo
examples. The probe reads the same pin through `gnn.importers.read_pin` and
rejects a `standard`/`strict` run whose installed distribution records a
different PEP 610 commit; `cogant/uv.lock` remains observed dependency metadata
that the audit cross-checks against the `upstream` extra, not an independent
expected revision.

## Cutover record

The pin moved from `v5.0.3` at `8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1` to
`v5.1.0` at `75c834bd8519dc7b5adc4d24f16bf393cfd1ecdf`, the first release whose
tree contains `src/gnn/importers.py` (added upstream in `e6a9d3917`). That
revision is the boundary the
[GNN–FEP contract](https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation/blob/main/docs/workflows/gnn-fep.md)
sets: before it, the arm could not call `python -m gnn.importers`; with it, the
interim local readers are deleted in the same change.

- `tools/gnn_upstream_audit_surface.py` read the expected revision from the
  `upstream` extra in `cogant/pyproject.toml` and the version from
  `cogant/uv.lock`. It now calls `gnn.importers.read_pin` on this pin.
- `tools/audit_release_integrity.py` held a second copy of pin-shape and
  pointer-token validation and `tests/test_release_integrity_pin.py` was its
  only subject. Both are deleted; `check_importer` and `check_pointer` report
  those findings, and the audit keeps the dependency facts it alone observes.
- No reader is vendored, and the pin advance is the only change to the
  revision the arm installs.
