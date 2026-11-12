# GNN conformance

`gnn conformance (pinned)` is defined in `.github/workflows/ci.yml` (job key
`gnn-conformance`, which runs the `gnn` arm of the root `run_gate.py`) and
`.github/gnn-pin.json` records
`ActiveInferenceInstitute/Generalized_Notation_Notation` at `v5.0.3`
(`8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1`). The job does not read that file:
it installs the same commit through the `upstream` extra in
`cogant/pyproject.toml`, and its final step checks that pin against
`cogant/uv.lock`.

The job runs `uv sync --extra upstream --extra dev`, emits a package from
`cogant/examples/control_positive/calculator` with the pipeline runner, and
validates the resulting `gnn_package/model.gnn.md` at the `standard` and
`strict` levels of the pinned parser before running upstream steps 3, 5 and 6.
That probe is `cogant/scripts/gnn_conformance_probe.py`. It then runs `tests/unit/test_gnn_upstream_bridge.py`,
`tests/unit/test_gnn_upstream_bridge_contract.py`,
`tests/unit/test_upstream_pipeline_resolution.py` and
`tests/integration/test_upstream_gnn_pipeline.py`, and finishes with
`python ../tools/audit_release_integrity.py --no-openapi`. It does not scan the
rest of the repository for `*.gnn.md`; the three
`cogant/examples/zoo/*/model.gnn.md` files are outside this job's scope.
