# GNN conformance

`gnn conformance (pinned)` is defined in `.github/workflows/ci.yml` (job key
`gnn-conformance`, which runs the `gnn` arm of the root `run_gate.py`) and
`.github/gnn-pin.json` records
`ActiveInferenceInstitute/Generalized_Notation_Notation` at `v5.0.3`
(`8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1`). The job installs that commit
through the `upstream` extra in `cogant/pyproject.toml`. Its final
`audit_release_integrity.py` step reads the JSON pin and rejects schema,
repository, commit or release-tag drift against the extra and `cogant/uv.lock`,
and checks that this pointer names the pin, revision, workflow and job.

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

The workflow-group contract stages shared-reader adoption by the pin: `v5.0.3`
predates `gnn.importers`. Until the pin advances to a release containing that
module, the arm retains its local reader and drift checks; it neither invokes
the unavailable module nor vendors it. The shared-reader cutover remains in
[PR #16](https://github.com/ActiveInferenceInstitute/COGANT/pull/16).
