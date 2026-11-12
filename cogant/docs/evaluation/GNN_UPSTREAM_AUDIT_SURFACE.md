# GNN Upstream Audit Surface

This page records the verifier boundary for COGANT's optional integration with
the Active Inference Institute `generalized-notation-notation` package, and the
current compatibility scope. Dated earlier results are retained separately.

## Pinned Upstream Release

| Field | Value |
| --- | --- |
| Distribution | `generalized-notation-notation` (optional `cogant[upstream]` extra; not part of `all`) |
| Pin (`.github/gnn-pin.json`; dependency installation recorded in `cogant/pyproject.toml` and `cogant/uv.lock`) | `75c834bd8519dc7b5adc4d24f16bf393cfd1ecdf` |
| Distribution version / `gnn.__version__` | `5.1.0` / `5.1.0` |
| Pin tag | [v5.1.0](https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation/releases/tag/v5.1.0), dated 2026-11-12; annotated tag `7393a5d0ef3834d71f2e11cbf2a9ac34376af5dd`, peeled to the exact pinned commit; the importer-registry release, first tag whose tree contains `src/gnn/importers.py` |
| Import package | top-level `gnn` (GNN >= 4.0; the GNN 2.x `src.gnn` surface no longer exists) |
| License | CC-BY-NC-SA-4.0 (see [`LICENSES.md`](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/cogant/LICENSES.md)) |

The `GNN v2.0.0` value under `## GNNVersionAndFlags` in every COGANT
`model.gnn.md` is COGANT's own schema identifier
(`cogant.schema.versions.CURRENT_GNN_VERSION`). It is independent of the
upstream package release above.

## Current Pin (2026-11-12)

The pin moved from `v5.0.3` (`8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1`) to
`v5.1.0` (`75c834bd8519dc7b5adc4d24f16bf393cfd1ecdf`). That release is the first
whose tree contains `src/gnn/importers.py`, so the `gnn` arm now calls the
shared reader —
`python -m gnn.importers check --repo . --require-pointer --workflow .github/workflows/ci.yml --job gnn-conformance` —
from the prepared `upstream` environment, and `load_upstream_expectation()`
reads the same pin through `gnn.importers.read_pin`. `cogant/uv.lock` and the
installed distribution remain observations: the conformance probe rejects a run
whose PEP 610 commit differs from the pin, and `tools/audit_release_integrity.py`
keeps the `upstream`-extra/`uv.lock` commit agreement instead of re-reading the
pin. The collected evidence below was taken on `v5.0.3` and is retained as
dated history; no `v5.1.0` audit collection is claimed on this page.

## Compatibility collected on v5.0.3 (2026-11-01)

The pin at that time was the v5.0.3 tag; the release record for that tag was
created retroactively on 2026-11-03, and the tag still resolves to that commit,
`8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1`. The installed source's PEP 610
record, the lockfile, the
distribution version, `gnn.__version__` and the bridge version all named `5.0.3`
and that commit, and `tools/audit_release_integrity.py` cross-checks the
`upstream` extra's commit against `uv.lock`, failing when the two disagree.

The validator surface was re-established on the new pin: a freshly translated
calculator package scored 100/100 under COGANT's `GNNValidator` and reported 0
errors under upstream `validate_gnn_syntax` at both `standard` and `strict`,
against the installed 5.0.3 environment. The upstream unit suite that exercises
the bridge, its contract, the installed-release identity, the validator flags
and pipeline resolution passes with the extra installed. Upstream `HEAD` was the
pinned commit at collection time; the dependency target stays the release tag's
commit, not a branch.

The selected 25-step pipeline lane was re-collected on this pin with
`tools/gnn_upstream_audit_surface.py --collect --strict-version --strict-upstream`:
all 20 selected steps succeeded and upstream reported `SUCCESS_WITH_WARNINGS`.
The bridge selection skipped steps 1, 2, 11, 12 and 13, and upstream ran no step
outside that selection. The dated
[`gnn_v5_0_3_compatibility.json`](gnn_v5_0_3_compatibility.json) receipt records
the identity fields, the validator result and every step's status and duration.
No supply-chain scan was run for this pin, so that lane stays unscanned here and
the older scan results do not apply.

## Historical Result (2026-10-26, v5.0.1)

The latest published, non-prerelease GNN release at review time was v5.0.1.
The installed source's PEP 610 record, lockfile, and peeled release tag all
resolved to the then-pinned commit; distribution and engine versions were
both `5.0.1`. Upstream's default branch had moved beyond that release and is
not used as the dependency target.

On CPython 3.13.17 with the locked `all` and `upstream` extras, a freshly
translated calculator package passed COGANT package validation and upstream
single-file validation at `standard` and `strict`. The audit helper's
`--strict-version --strict-upstream` collection passed all 20 selected steps
with `SUCCESS_WITH_WARNINGS` overall. The selection excluded setup, upstream
tests, render, execute, and LLM steps (`1, 2, 11, 12, 13`). Warnings retained
missing render/execute prerequisites and optional capabilities. No supply-chain
scan was run in this review; the older scan results below do not apply to this
environment.

The retained [machine-readable compatibility receipt](gnn_v5_0_1_compatibility.json)
records exact source identities, selected steps, validator results, and the
unscanned supply-chain lane. Raw run paths in that receipt locate this local
collection; the JSON is a dated compatibility record, not a portable runtime.

The installed-release regression compares distribution/import versions and
PEP 610 source identity to `uv.lock`. A subprocess regression runs the actual
COGANT bridge with an importable retired namespace present, verifying that
only the installed top-level provider determines availability and version.
Existing real pipeline tests also exercised parsing, typing, and validation
on a package emitted by the current formatter.

The release adds numerical witnesses, an offline inspector, and bounded file
workers. Updating the parser/pipeline dependency does not establish admission
of every COGANT-derived model to a witness or validate source-program behavior.
See the [DiffProg review](../rnd/differentiable_programming.md) for scoped
connections and further admission requirements.

## Dependency Scan for COGANT 0.8.0 (2026-10-27)

The [separate dependency-scan receipt](dependency_audit_0_8_0.json) records the
locked `all` + `upstream` environment after upgrading certifi from 2026.7.22 to
2026.10.23 for [GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2).
No known vulnerabilities were returned for the registry packages audited.
COGANT and GNN themselves were excluded because their installed versions have
no PyPI advisory records. Their source identity and compatibility are checked
separately; the scan does not establish advisory coverage for those packages.
The 2026-10-26 receipt's unscanned lane remains unchanged.

## Claims Kept Separate

1. **Version currentness.** The installed upstream commit (PEP 610
   `direct_url.json`) equals the commit read by `gnn.importers.read_pin` from
   `.github/gnn-pin.json`. The `uv.lock` entry must match that commit, and both
   the distribution version and `gnn.__version__` must equal the locked version.
   The pin supplies the expected commit and tag; the lock supplies observed
   dependency metadata. The helper hard-codes no release.
2. **Bridge usability.** `cogant.gnn.upstream_bridge` imports upstream and
   reports the same version (it refuses GNN < 4.0 and a `gnn` package owned by
   another distribution). The negative control requires a clean
   (`python -I`, empty working directory) `import src.gnn` to fail: a passing
   import would mean a GNN 2.x install or an unrelated `src` package is
   shadowing the reference.
3. **COGANT-owned method health.** COGANT's package validator plus upstream
   `validate_gnn_syntax` (`standard` and `strict`) on a freshly translated
   control-positive model.
4. **Selected upstream all-step execution.** The optional upstream pipeline is
   a stricter compatibility surface. Product code treats selected upstream-step
   failures as advisory; audit mode promotes them to fatal so a report cannot
   quietly convert partial compatibility into a full execution claim. The
   helper also reconciles the bridge selection against upstream's own run
   summary, because GNN 4.x adds hard prerequisite steps and drops steps it is
   told to skip.

## Audit Helper

The project-root helper `tools/gnn_upstream_audit_surface.py` either builds an
audit directory (`--collect`) or reads an existing one, then writes the
surface. Collection needs an interpreter that imports `cogant` with the
`upstream` extra installed; from the COGANT project root:

```bash
uv run --directory cogant --extra upstream python ../tools/gnn_upstream_audit_surface.py \
  --collect --audit-dir output/gnn_upstream_audit
```

`--collect` writes, in order:

| Artifact | Contents |
| --- | --- |
| `version_probe.txt` | Distribution version, `gnn.__version__`, installed commit, bridge availability and version, clean-interpreter `import src.gnn` (negative control) and `import gnn` results, the pin and lock values, and, when the network allows, `git ls-remote` of upstream `HEAD` and the `v<version>` tag. |
| `gnn_package/` | COGANT translation of `cogant/examples/control_positive/calculator` (built in a temporary directory, then copied). |
| `single_file_validation.json` | COGANT `GNNValidator` verdict and upstream `validate_gnn_syntax` at `standard` and `strict`. |
| `upstream_full/` | `run_upstream_pipeline` with the bridge's default selection (`DEFAULT_SKIP_STEPS == {1, 2, 11, 12}`) and `skip_llm=True`: bridge summary `upstream_pipeline_summary.json`, console log `upstream_pipeline.log`, upstream run summary `00_pipeline_summary/`, and per-step outputs. |
| `pip_audit_path.json` | `uvx pip-audit --format json --path <site-packages>` over the probing interpreter (skipped when neither `uvx` nor `pip-audit` is on `PATH`; `--no-pip-audit` disables it). |
| `collect_manifest.json` | Phase timings and the expectation used. |

Summarize an existing audit directory without re-collecting:

```bash
uv run python tools/gnn_upstream_audit_surface.py \
  --audit-dir output/gnn_upstream_audit \
  --output-dir output/gnn_upstream_audit/published_surface
```

The helper writes:

| Output | Purpose |
| --- | --- |
| `gnn_upstream_audit_surface.json` | Machine-readable claim classification. |
| `gnn_upstream_audit_surface.md` | Human-readable report for reviews and release notes. |
| `gnn_upstream_audit_surface.svg` | Compact visualization of version, upstream-step, and supply-chain lanes. |

Strict flags are independent: `--strict-version` fails when the version/bridge
claim fails, `--strict-upstream` fails on any selected upstream step failure,
and `--strict-supply-chain` fails on pip-audit findings or an absent/incomplete scan.
Collection requires a new or empty audit directory and preserves previous runs.
`--pin` selects another canonical pin, `--lock` selects dependency observations,
and `--no-ls-remote` skips the network probe. The helper requires upstream's
`gnn.importers`, which the pinned `v5.1.0` release ships; run it from the
`upstream` environment the `gnn` arm prepares.

## Reading The SVG

The SVG has three lanes: version/bridge, selected upstream all-step gate, and
supply-chain scan. Below them is one cell per upstream step index. Green means
a selected step succeeded; red means a selected step failed; pale green or
pale red marks a step upstream ran outside the bridge selection (a hard
prerequisite); grey marks a step that did not run. This is a visual claim
ledger, not a decorative figure: if the all-step lane is red, the docs must not
say that COGANT's package fully executes through every selected upstream step.

## Historical Result (2026-10-15)

The pinned commit `46459949944e3217f8a6a804d4ff8c52829ef275` was verified on
CPython 3.12 with the locked `all` and `upstream` extras. Strict version,
selected-upstream, and supply-chain gates passed; all 20 selected steps
succeeded. COGANT package validation and both upstream single-file validation
levels passed. The clean-interpreter `src.gnn` import failed as expected.
The machine-generated [audit JSON](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/cogant/evaluation/gnn_upstream_audit_surface.json)
and [audit report](https://github.com/ActiveInferenceInstitute/COGANT/blob/main/cogant/evaluation/gnn_upstream_audit_surface.md) preserve the
per-step statuses and the exact pin/lock/installed commit identity.

## Historical Result (2026-10-14)

Historical result collected on 2026-10-14 with Python 3.13 against
`b4a583a5851021612a9a5df94e428f78aa6f76a0`, using the
default selection and `skip_llm=True`, in an environment synced from the
committed `cogant/uv.lock` (`uv sync --frozen --extra upstream --extra dev`):

```bash
uv run --directory cogant --frozen --extra upstream --extra dev \
  python ../tools/gnn_upstream_audit_surface.py --collect \
  --audit-dir /tmp/cogant_gnn_upstream_audit
```

| Claim | Result |
| --- | --- |
| Version and bridge currentness | **PASS**: installed commit `b4a583a5…` equals the pin and the lock; distribution `4.1.0`; `gnn.__version__` `4.1.0`; upstream `HEAD` was the pinned commit at collection time; `v4.1.0` resolves to `9255e19f…`. |
| Bridge and negative control | **PASS**: the bridge reports `4.1.0`; a clean `import src.gnn` fails with `ModuleNotFoundError: No module named 'src'`; a clean `import gnn` reports `4.1.0`. |
| Single-file validation | **PASS**: COGANT `GNNValidator` 100.0/100 with 0 errors; upstream `validate_gnn_syntax` 0 errors at both `standard` and `strict`. |
| Selected upstream steps | **20/20 succeeded**; upstream overall status `SUCCESS_WITH_WARNINGS`; one bridge invocation of about 78 s wall time. |
| Supply-chain scan | **PASS**: `pip-audit` over the environment's 137 installed distributions reported no known vulnerabilities. |

Per-step outcomes for the bridge selection (steps 0, 3–10, 14–24; step 13 is
excluded by `skip_llm=True`):

| Step | Script | Status | Duration (s) | Reason |
| --- | --- | --- | --- | --- |
| 0 | `0_template.py` | SUCCESS | 0.3 |  |
| 3 | `3_gnn.py` | SUCCESS | 0.4 |  |
| 4 | `4_model_registry.py` | SUCCESS | 0.3 |  |
| 5 | `5_type_checker.py` | SUCCESS_WITH_WARNINGS | 4.1 |  |
| 6 | `6_validation.py` | SUCCESS | 1.2 |  |
| 7 | `7_export.py` | SUCCESS | 0.6 |  |
| 8 | `8_visualization.py` | SUCCESS | 40.8 |  |
| 9 | `9_advanced_viz.py` | SUCCESS | 13.2 |  |
| 10 | `10_ontology.py` | SUCCESS | 0.3 |  |
| 14 | `14_ml_integration.py` | SUCCESS | 0.5 |  |
| 15 | `15_audio.py` | SUCCESS | 1.3 |  |
| 16 | `16_analysis.py` | SUCCESS_WITH_WARNINGS | 3.1 |  |
| 17 | `17_integration.py` | SUCCESS | 1.5 |  |
| 18 | `18_security.py` | SUCCESS_WITH_WARNINGS | 0.3 |  |
| 19 | `19_research.py` | SUCCESS | 0.3 |  |
| 20 | `20_website.py` | SUCCESS | 0.5 |  |
| 21 | `21_mcp.py` | SUCCESS | 4.3 |  |
| 22 | `22_gui.py` | SUCCESS | 0.4 |  |
| 23 | `23_report.py` | SUCCESS | 0.6 |  |
| 24 | `24_intelligent_analysis.py` | SUCCESS | 0.7 |  |

Selection notes:

- **Explicit skips hold.** The bridge passes its skip set (`1, 2, 11, 12`
  plus `13` under `skip_llm`) to upstream as `--skip-steps`. Upstream applies
  skips after resolving declared prerequisites, so `11_render` and
  `12_execute` did not run even though `16_analysis` declares `3, 7, 12` and
  `18_security` declares `11`; both dependents finished
  `SUCCESS_WITH_WARNINGS` with upstream prerequisite warnings about the
  missing render/execute outputs.
- **Auto-included prerequisites are reported.** When a requested step's
  prerequisite is not skipped, upstream runs it; the bridge lists such steps in
  `UpstreamPipelineResult.auto_included` and includes their step records.
  None were auto-included in this run.
- **Optional extras.** Several steps degrade gracefully without optional
  upstream extras (D2 CLI for `9_advanced_viz`, scikit-learn for
  `14_ml_integration`, Gradio for `22_gui`); they still report `SUCCESS`.
- **Earlier same-day run.** A run made before the bridge passed explicit
  skips recorded 20/21: upstream auto-included and ran `11_render` (4/4
  framework renderings) and `12_execute` (`SUCCESS_WITH_WARNINGS`; DisCoPy,
  JAX and PyMDP scripts executed without a sandbox, upstream default
  `GNN_SANDBOX=off`), and the requested step 13 was reported `NOT_RUN`
  because `--skip-llm` removes it upstream. Its `pip-audit` findings
  (anyio 4.13.0, fsspec 2026.3.0, idna 3.11, mkdocs-material 9.7.6, multidict
  6.7.1, pillow 12.2.0, pymdown-extensions 10.21.2, starlette 1.0.0, urllib3
  2.6.3) came from an environment built from the pre-refresh lock; the
  refreshed lock resolves newer releases of every one of them.

## Historical Boundary (4.1.0)

Against the former 4.1.0 release-line pin, COGANT's validation, type-check,
export, visualization, roundtrip, and runner paths pass, the generated
calculator model passes upstream validation at `standard` and `strict`, and
every selected upstream step succeeds. Render and execute (`11`/`12`) are off
by default and were not exercised in this run; opt in with `skip_steps=[]`
(they ran successfully for the calculator package in the earlier run).
Optional upstream extras (D2, scikit-learn, Gradio, bnlearn, an LLM backend)
change what several steps can exercise. Treat a 100/100 COGANT package score
as a structural-validation statement, not as proof that every upstream
framework backend can render and run every COGANT package.
