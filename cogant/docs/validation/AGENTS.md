# AGENTS.md — Validation module

The COGANT validation pipeline: how generated GNN packages, role
assignments, and roundtrip artifacts are checked for correctness,
completeness, and policy compliance. The module documents both the
shipped validator set and the extension points for custom validators.

## Purpose and ownership

Validation is how COGANT is gated: every pipeline run ends in a
validation pass, every CI integration reads a validation report, and
every release gate cites validation coverage. Documentation here has to
be accurate down to the issue-level severity and category taxonomy.
Owned by whoever is editing `py/cogant/validation/` or the CI pipeline
stage that consumes validation reports.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC and recommended reading order | When a file is added, removed, or renamed |
| `AGENTS.md` | This file — maintenance rules | When the severity taxonomy or ownership changes |
| `overview.md` | What the validation layer does and where it sits in the pipeline | When the validation pipeline stages change |
| `validation_via_cli.md` | Running validators from the command line | When the CLI surface changes |
| `validation_stages.md` | Stage-by-stage walk through the validation pipeline | When stages are added, removed, or reordered |
| `issue_levels.md` | Severity model: error, warning, info | When severity semantics change |
| `issue_categories.md` | Categorical taxonomy of validation issues | When a new category is added or retired |
| `validation_report.md` | Schema and consumer guide for the report artifact | When the report schema changes — bump schema version in the same PR |
| `thresholds_policies.md` | Configurable thresholds and gating policies | When thresholds or gating defaults change |
| `custom_validators.md` | Authoring and registering your own validators | When the custom-validator API changes |
| `audit_trail.md` | Reproducible audit trail of validator runs | When the audit format or retention changes |
| `verification_and_test_posture.md` | How COGANT itself is tested and verified | When the test posture changes |
| `cogant_implementation_verification_report.md` | Snapshot verification report for the implementation | When a new snapshot is produced |
| `archival_note.md` | Provenance of historical validation artifacts | Rarely; treat as archived |
| `see_also.md` | Cross-links to related modules | When link targets move |

## Adding a new doc

1. Decide whether the new content is about the shipped pipeline (overview
   / stages / report / thresholds), extension (custom validators), or
   assurance (audit trail / verification posture), and place it with its
   siblings.
2. Use a short, lower-case, underscore-separated slug.
3. Open with the `overview.md` diagram reference so readers know which
   stage your page is about.
4. If the new content changes the report schema, the issue taxonomy, or
   the severity model, mention it in `../roadmap/deprecation_policy.md`
   and the changelog.
5. Add a row to the `## Contents` table in `README.md`.

## Known gotchas

- `issue_levels.md` and `issue_categories.md` are the taxonomy files that
  every other page in this module (and `../cli/`, and several CI integration
  docs) cites. Changing them is a backwards-incompatible change — bump the
  report schema version when you do.
- `cogant_implementation_verification_report.md` is a dated snapshot. Do
  not edit it in place when re-running verification; produce a new
  dated sibling file and link to it from the README.
- `audit_trail.md` overlaps with the `../security/` module's notion of
  audit logging. Keep this file focused on validator-run provenance; the
  security audit log story belongs under `../security/security_controls.md`.
