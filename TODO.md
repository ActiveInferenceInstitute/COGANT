# COGANT TODO

- Status: Active (P0–P5 roadmap below).
- Owner: DAF.
- Last reviewed: 2026-08-01 (hostile red-team pass: Miner/Medium fixes implemented; Major findings scoped in the "Major — Scoped (deferred)" section below).

This is the future-only execution backlog. Completed work belongs in Git
history, generated evidence, audit reports, or the taskboard; it must not be
reintroduced here as `[x]` history. Every item below is active or upcoming and
has an explicit priority, dependency, deliverable, and acceptance condition.

Status markers:

- `[~]` active work or an unresolved current baseline issue.
- `[ ]` planned work that is not yet started.
- `[!]` blocked work; the blocker is recorded in the item.

Source-of-truth rules:

- Numeric manuscript claims come from
  [`cogant/evaluation/METRICS.yaml`](cogant/evaluation/METRICS.yaml).
- Robustness, held-out, roundtrip, and batch claims come from generated
  artifacts with source/configuration provenance.
- Rendered manuscript outputs and visual QA are release artifacts, not manual
  substitutes for source validation.
- [`tasks.yaml`](tasks.yaml) mirrors the active workstreams and aliases below;
  Git history and task records retain completed work outside this file.

## P0 — Stabilize the current refactor

- [~] **cog-p0-01 — Restore a clean package baseline.**
  - Priority: P0.
  - Depends on: none; reconcile the existing parser/config/server worktree.
  - Deliverable: one coherent parser package, typed-config surface, server
    surface, exports, stubs, package-data rules, and mypy module identity.
  - Acceptance: strict Ruff, strict mypy, focused parser/config/server tests,
    clean-wheel import smoke, and supported non-upstream test collection pass.

- [~] **cog-p0-02 — Make developer and CI environments hermetic.**
  - Priority: P0.
  - Depends on: cog-p0-01.
  - Deliverable: tests use repository-local imports, routine installation is
    independent of the optional upstream GNN checkout, and the upstream smoke
    job is separate and resource-bounded.
  - Acceptance: a clean offline environment collects and runs the documented
    core suite without an unrelated installed `tests` package or upstream
    network access.
  - Blocker: the complete historical `pytest tests/` lane now collects cleanly
    but still contains legacy contract failures in older configuration,
    reverse-matrix, cache-layout, parser-loader, server-error, GNN-package,
    and optional-upstream tests. The canonical registry and strict server
    boundary remain authoritative; the focused current-contract lane must not
    be presented as a full-suite certification.

- [~] **cog-p0-03 — Close the documentation and packaging boundary.**
  - Priority: P0.
  - Depends on: cog-p0-01.
  - Deliverable: documented installable parser/language tree, repaired example
    links, current parser paths/capability wording, and corrected Rust format
    commands using `cargo fmt --all --check`.
  - Acceptance: folder-doc, package-data, public-export, Rust format/check/test,
    and clippy audits pass.

- [~] **cog-p0-04 — Reconcile generated evidence after refactor changes.**
  - Priority: P0.
  - Depends on: cog-p0-01, cog-p0-02, cog-p0-03.
  - Deliverable: regenerated [`METRICS.yaml`](cogant/evaluation/METRICS.yaml),
    manuscript variables, figures,
    injected manuscript tree, figure manifest, and artifact manifest; optional
    Rust references resolve through the public adapter.
  - Acceptance: metrics freshness, manuscript crossrefs, citations,
    formalisms, numbers, links, claim scope, synthetic-surface, renderer,
    robustness, visual-QA, and publication-readiness gates pass.
  - Blocker: `check_metrics_fresh.py --fail-on-dirty` remains intentionally
    red until these source edits are committed and metrics are regenerated
    against that commit; the current worktree has been regenerated from the
    live sources but cannot claim commit-bound freshness while uncommitted.

## P1 — Canonical public contracts and reliability

- [~] **cog-p1-01 — Canonical typed configuration.**
  - Priority: P1.
  - Depends on: cog-p0-01.
  - Deliverable: `ProjectConfig` and one preset registry as the authoritative
    model, legacy translation/warnings for one deprecation cycle, and a schema
    version/migration mechanism.
  - Acceptance: compatibility fixtures prove precedence
    `defaults < preset < file < environment < CLI`; no parallel registry remains.

- [~] **cog-p1-02 — Explicit parser capabilities.**
  - Priority: P1.
  - Depends on: cog-p0-01, cog-p0-03.
  - Deliverable: registry-only parser selection with language, extensions,
    implementation, optional dependency, fallback/degraded status, and source
    provenance.
  - Acceptance: tree-sitter is selected when installed; fallback is observable;
    unavailable-parser errors and capability tests cover every registered language.

- [~] **cog-p1-03 — Fail-closed pipeline contracts.**
  - Priority: P1.
  - Depends on: cog-p1-01, cog-p1-02.
  - Deliverable: stage outcomes (`success`, `partial`, `skipped`, `failed`,
    `unavailable`), required-artifact contracts, and a manifest containing
    source identity, config/parser/rule versions, stage outcomes, artifact
    digests, and reproducibility metadata.
  - Acceptance: validation/publication refuse incomplete bundles and partial
    results cannot be mistaken for valid evidence.

- [~] **cog-p1-04 — Correct incremental execution.**
  - Priority: P1.
  - Depends on: cog-p1-02, cog-p1-03.
  - Deliverable: cache keys based on repository content, config, parser, and
    rule digests, with deletion/rename/corruption handling and atomic writes.
  - Acceptance: fixture tests prove deterministic invalidation and equivalence
    of full and incremental outputs across all supported languages.

- [~] **cog-p1-05 — Versioned server boundary.**
  - Priority: P1.
  - Depends on: cog-p0-01, cog-p1-03.
  - Deliverable: API v1 request/response/error envelope with bounded bodies and
    archives, safe workspace paths, non-loopback authentication, timeouts,
    cancellation, concurrency/rate limits, and source-safe structured logs.
  - Acceptance: abuse/security tests pass and the default server remains
    local-only until an actual isolation boundary exists.

## P2 — Language and graph semantics

- [~] **cog-p2-01 — Complete graph normalization increments.**
  - Priority: P2.
  - Depends on: cog-p1-02, cog-p1-03.
  - Deliverable: method-receiver-to-class resolution, async-call edge kinds,
    decorator/annotation edges, generated-file detection, and test-only
    `NodeKind.TEST` classification.
  - Acceptance: positive/negative fixtures and graph invariants cover every
    increment without changing unrelated edge semantics.

- [~] **cog-p2-02 — Cross-language fixture matrix.**
  - Priority: P2.
  - Depends on: cog-p2-01.
  - Deliverable: Python, JavaScript, TypeScript, Rust, and Go fixture matrices
    covering positive, negative, fallback, source-span, import/package,
    generated-file, async, decorator, and test-symbol cases.
  - Acceptance: Rust and Go remain marked experimental until evidenced; Java is
    not advertised without a real implementation; every fixture exports mode
    and confidence metadata.

- [~] **cog-p2-03 — Capability-aware evidence.**
  - Priority: P2.
  - Depends on: cog-p1-02, cog-p2-01.
  - Deliverable: analysis reports and dashboards containing parser mode,
    confidence, unsupported constructs, skipped files, and degradation reasons.
  - Acceptance: invariants prevent unsupported syntax from silently becoming
    high-confidence graph evidence.

## P3 — Robustness, held-out evidence, and claim governance

- [~] **cog-6 / cog-p3-01 — Extend semantic-preservation robustness.**
  - Priority: P3.
  - Depends on: cog-p0-04, cog-p2-02.
  - Deliverable: equivalent loop/branch rewrites, inlining/outlining variants,
    parser/frontend variation, and canonical JSON/Markdown regeneration.
  - Acceptance: CI regenerates or rejects stale robustness artifacts; negative
    controls fail as expected and robustness audits remain clean.

- [~] **cog-7 / cog-p3-02 — Promote the held-out pilot.**
  - Priority: P3.
  - Depends on: cog-p3-01.
  - Deliverable: pinned source refs/digests, licensing and fixture intent,
    split/generator metadata, one additional permissively licensed fixture, and
    metrics/claim freshness integration.
  - Acceptance: held-out output regenerates deterministically, leakage rules are
    recorded, and claim-scope gates reject unsupported score relabelling.

- [ ] **cog-p3-03 — Strengthen semantic oracles.**
  - Priority: P3.
  - Depends on: cog-p2-03, cog-p3-01.
  - Deliverable: edge-kind, matrix-dimension, structural-invariant, behavior-
    oracle where justified, and human-labeled precision/recall checks.
  - Acceptance: role preservation is reported separately from accuracy,
    external validity, and generalization; oracle failures identify their layer.

- [ ] **cog-p3-04 — Stratify evidence and failure modes.**
  - Priority: P3.
  - Depends on: cog-p3-02, cog-p3-03.
  - Deliverable: claim-ledger lanes for in-sample, held-out, synthetic,
    negative-control, and externally validated evidence plus calibration and
    language/transformation failure taxonomy.
  - Acceptance: aggregate scores cannot conceal stratified regressions and no
    manuscript claim exceeds its evidence class.

## P4 — Scale and interoperability

- [~] **cog-p4-01 — Isolated upstream GNN integration.**
  - Priority: P4.
  - Depends on: cog-p1-02, cog-p5-03.
  - Deliverable: pinned optional dependency, bounded checkout/cache, license and
    provenance record, distinct unavailable versus validation-failed results,
    and a manually triggered CI smoke lane that never enters core installation.
  - Acceptance: core install/tests remain independent; upstream failures are
    fail-closed, bounded, and diagnosable.
  - Current state: the optional extra is excluded from `all`, the bridge
    distinguishes unavailable from failed validation, release integrity checks
    the full commit pin and license metadata, and CI has an explicit manual
    smoke job. The upstream checkout itself remains intentionally uninstalled
    in the core developer environment.

- [ ] **cog-p4-02 — Streaming and resource bounds.**
  - Priority: P4.
  - Depends on: cog-p1-03.
  - Deliverable: streaming export, bounded-memory processing, backpressure,
    cancellation, and large-graph benchmark fixtures with machine provenance.
  - Acceptance: documented resource limits hold and outputs match full runs under
    incremental, cancellation, and rerun scenarios.

- [ ] **cog-p4-03 — Monorepo and cross-repository analysis.**
  - Priority: P4.
  - Depends on: cog-p1-03, cog-p4-02.
  - Deliverable: source identity, package boundaries, collision handling,
    repository pinning, and reproducible remote-source manifests.
  - Acceptance: multi-package fixtures preserve identity and cannot merge
    unrelated symbols or silently lose repository provenance.

- [ ] **cog-p4-04 — Python/Rust parity and downstream utility.**
  - Priority: P4.
  - Depends on: cog-p2-03, cog-p4-02.
  - Deliverable: shared semantic parity tests and a separately labeled
    downstream inference/runtime utility evidence track.
  - Acceptance: Rust acceleration remains opt-in until parity passes, and
    downstream utility claims never certify structural translation quality.

- [ ] **cog-p4-05 — Isolation claims.**
  - Priority: P4.
  - Depends on: cog-p1-05, cog-p4-02.
  - Deliverable: threat model, subprocess/filesystem boundary, resource limits,
    and adversarial tests before any sandbox or arbitrary-code claim.
  - Acceptance: no production isolation wording appears until the tested
    boundary is real and the adversarial suite is green.

## P5 — Release, security, documentation, and maintenance

- [~] **cog-p5-01 / cog-m1 — Aggregate release gate.**
  - Priority: P5.
  - Depends on: cog-p0-04, cog-p1-03, cog-p2-03, cog-p3-04, cog-p4-01.
  - Deliverable: [`tools/release_gate.py`](tools/release_gate.py), one go/no-go
    command covering code quality, installation, collection, Rust checks,
    freshness, generated artifacts, manuscript audits,
    visual QA, security, provenance, and reproducibility.
  - Acceptance: the gate fails closed on any required lane and produces a
    reviewable machine-readable summary with exact remediation paths.
  - Blocker: the gate remains red until the historical full-suite failures are
    reconciled and the dirty-worktree metrics freshness check is rerun after
    commit-bound regeneration.

- [~] **cog-p5-02 — Documentation truth pass.**
  - Priority: P5.
  - Depends on: cog-p0-03, cog-p1-01, cog-p2-03.
  - Deliverable: implementation-aligned README, FAQ, configuration, parser,
    evaluation, and security documentation; aspirational claims are labeled.
  - Acceptance: folder-doc, link, docs-constant, and claim-scope audits pass
    against the current code and generated artifacts.

- [~] **cog-p5-03 — Supply-chain and release integrity.**
  - Priority: P5.
  - Depends on: cog-p1-05, cog-p4-01.
  - Deliverable: OpenAPI checks, dependency/license/SBOM report, reproducible
    wheel checks, package/API version consistency, pinned remote provenance,
    and CI wiring for clean-wheel attribution.
  - Acceptance: release artifacts can be rebuilt and independently attributed
    without network-dependent hidden inputs.
  - Current state: `audit_release_integrity.py` emits the release report and
    CycloneDX-shaped SBOM, verifies wheel `RECORD` hashes and byte-identical
    clean builds, checks OpenAPI request/response coverage, and verifies the
    optional upstream commit pin. Independent CI execution and final human
    license review remain open.

- [ ] **cog-p5-04 — Deprecation and maintenance policy.**
  - Priority: P5.
  - Depends on: cog-p1-01, cog-p1-02.
  - Deliverable: removal schedule for legacy config fields, parser aliases, stub
    paths, and CLI behavior; generated output remains disposable and reproducible.
  - Acceptance: deprecation warnings, migration tests, and regeneration docs
    remain green for one complete compatibility cycle.

## Execution order

1. Complete P0 and make the current refactor green.
2. Land canonical config, parser, pipeline, cache, and server contracts.
3. Complete language/graph fixtures and capability-aware reporting.
4. Finish robustness and held-out evidence gates without widening claims.
5. Add scale and upstream integration as isolated capability tracks.
6. Run the aggregate release gate, regenerate all publication artifacts, and
   update `tasks.yaml` so only genuinely active/upcoming work remains in the
   execution view while taskboard history stays outside this file.

## Completed/Closed — 2026-08-01 hostile red-team pass

Items implemented and closed this pass (each verified by a targeted test run,
with Ruff clean and strict mypy clean on changed source; the full `not slow`
suite remained at its documented 137-failure P0 baseline — see `cog-p0-02`).

- [x] **ingest/files.py — symlink-containment guard.** `FileEnumerator.enumerate`
  now resolves each enumerated path and rejects any whose real path escapes the
  repo root (scope-escape / external-file-read). Regression test added
  (`TestFileEnumerator.test_enumerate_rejects_symlink_outside_repo`).
- [x] **ingest/repo.py — remote clone dir sanitisation.** `repo_name` is derived
  via `Path(...).name` with a salted-hash fallback so a hostile URL cannot
  escape `work_dir` or target an unrelated directory for `rmtree`.
- [x] **cache/store.py — durable atomic writes.** fsync before rename so a crash
  cannot leave a zero-length/incomplete entry that misleads `get_latest`.
- [x] **cache/hasher.py — bounded memory + symlink containment.**
  `hash_repo` now streams per file (no unbounded `bytes` buffer) and walks with
  `os.walk(followlinks=False)`, pruning out-of-tree real paths from the digest.
- [x] **graph/analysis.py — deterministic community + centrality sample.**
  `louvain_communities(..., seed=0)` and `centrality_sample` uses the
  deterministic `_centrality_sample_nodes(3)` instead of insertion order.
- [x] **statespace/compiler.py — monotone preference weight.** Zero-confidence
  constraints no longer boomerang to weight 1.0; certainty is monotone in weight
  (test-pinned positive confidence values unchanged).
- [x] **server/app.py — auth decoupled from rate limiting.** A configured
  `auth_token` now protects every non-unlimited route, independent of
  `rate_limited_paths` (previously `/api/v1/rules`, `/api/v1/metrics`, and any
  newly added route silently skipped auth). Regression tests added
  (`TestAuthDecoupling`).
- [x] **server/app.py — redacted 500 envelopes.** The four 500-error sites no
  longer leak `{Type}: {exc}` to remote clients; exceptions are logged
  server-side and a static message returned (consistent with `/reverse`).
- [x] **server/app.py — bounded rate-limiter memory.** Empty drained buckets are
  pruned so `_RateLimiter._history` cannot grow unbounded across client IPs.
- [x] **audit_test_names gate.** Fixed a content-regex false positive
  (`"wave-3 debris"` descriptive prose → `"legacy campaign debris"`); the naming
  audit now passes cleanly at HEAD.
- [x] **test_metrics_api.py — de-tautologised assertion.**
  `test_strict_isomorphism_count_is_strict_count` now asserts against the
  authoritative METRICS ledger field instead of a self-comparison.
- [x] **tasks.yaml — stale in-progress end dates.** Rolled forward internally
  inconsistent past `end` dates for `cog-6`, `cog-7`, and `cog-m1`; the
  `audit_roadmap_truth` and `audit_test_names` gates stay green.
- [x] **run_all_runner.py — subprocess timeouts.** `run_cmd` accepts a `timeout`
  and the remote `git clone` is bounded (300s, matching `ingest/repo.py`), with
  a `TimeoutExpired` → exit 124 fail-closed path.

## Major — Scoped (deferred)

Validated Major findings from the 2026-08-01 hostile red-team pass. These were
intentionally NOT implemented (manifest requires Minor/Medium only this pass).
Each is a concrete, actionable scope item.

- **M1 — Git option-injection → arbitrary command execution on clone.**
  Affected: `tools/run_all_runner.py` `ensure_git_clone` (argv `git_url`/`git_ref`
  appended with no `--` separator or scheme/leading-`-` validation) and
  `cogant/py/cogant/ingest/repo.py::ingest_git_remote`. Why it matters: a crafted
  URL/ref in the batch JSON (or repo-name derivation) is parsed by git as its own
  option (verified: `--upload-pack=id` is consumed as an option), enabling RCE on
  the host that runs "analyze hostile code". Suggested fix: require an
  allowlisted `scheme://host` regex, reject tokens beginning with `-`, insert
  `--` before URL/ref.
- **M2 — Synchronous pipeline work blocks the asyncio event loop.**
  Affected: `server/app.py` `/analyze`, `/roundtrip`, `/reverse` call blocking
  `_run_forward_pipeline` / `verify_repo_roundtrip` / `_synthesize_zip_from_gnn_text`
  inside `async` handlers (only `/visualize` correctly uses `to_thread`), so
  `asyncio.wait_for` timeout and the semaphore cap are ineffective and one slow
  request stalls `/health`, `/ready`, `/metrics`. Suggested fix: offload to
  `asyncio.to_thread(...)` with a process-level timeout for true preemption.
- **M3 — Coverage line-number decode is off-by-one.**
  Affected: `dynamic/coverage.py` `_decode_numbits` (`lines.append(byte_index*8 +
  bit_index)`) reports 0-based lines while coverage.py numbits is 1-based, and
  the unit tests pin the wrong 0-based decode. Why it matters: dynamic coverage
  enrichment mis-attributes write/dynamic evidence to the wrong graph node source
  ranges, corrupting the dynamic-fact layer. Suggested fix: `+1`, and update the
  pinned test expectations + regenerate dynamic artifacts.
- **M4 — `TransitionMatrix.from_state_space` builds a silent uniform matrix.**
  Affected: `simulate/distributions.py` — `trans_id.split("_")` yields
  `"trans"`/`"act"` which never match state ids, so transitions stay uniform and
  all EFE/free-energy simulation runs on meaningless dynamics. Suggested fix: key
  on the real `source_state`/`target_state` fields the compiler populates.
- **M5 — Stable-ID / graph-collision hazard + positional preference IDs.**
  Affected: `normalize/identities.py` (`_build_hash_input` uses ambiguity-prone
  `"|".join` and excludes `entity_type`) and `statespace/compiler.py`
  `_extract_preferences` (`pref_{i}` positional IDs). Suggested fix: length-prefix
  or JSON-serialize hash components and include `entity_type`; key preferences by
  mapping_id. Deferred because it changes generated IDs (roundtrip/state-space
  artifact churn) and needs a coordinated regeneration.
- **M6 — Untracked `_targeted.py` campaign-coverage cohort.**
  Affected: ~92 `cogant/tests/unit/*_targeted.py` files (~52k LOC) of line-targeted
  coverage-padding tests whose `_targeted.py` suffix evades `audit_test_names`
  (which catches `_cov.py`/`_coverage.py` only). Suggested fix: add a `_targeted.py`
  pattern to the audit and reconcile the cohort into behavior-named tests.
- **M7 — `audit_test_names` (and related doc gates) not wired into CI / release.**
  Affected: `.github/workflows/ci.yml`, `tools/release_gate.py`. The naming audit
  and several audit tools run nowhere in CI, so a red gate currently blocks
  nothing. Suggested fix: wire into `release_gate.py`/CI once M6 is reconciled.
