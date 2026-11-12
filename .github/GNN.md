# GNN conformance

`gnn conformance (pinned)` is defined in `.github/workflows/ci.yml` (job key
`gnn-conformance`, which runs the `gnn` arm of the root `run_gate.py`) and
`.github/gnn-pin.json` records
`ActiveInferenceInstitute/Generalized_Notation_Notation` at `v5.0.3`
(`8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1`). The `gnn` arm calls
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
`tests/integration/test_upstream_gnn_pipeline.py`, and finishes with
`python ../tools/audit_release_integrity.py --no-openapi`. The shared reader
also discovers the repository's `*.gnn.md` specifications, including the zoo
examples. The audit surface reads the expected revision and tag from
`.github/gnn-pin.json` through `gnn.importers.read_pin`; `cogant/uv.lock`
remains observed dependency metadata, not an independent expected revision.

## Migration blocker

The current pinned release does not ship `gnn.importers`. The new arm fails
closed until COGANT adopts an upstream revision containing that reader.
This migration does not silently advance the release pin or vendor the reader.
