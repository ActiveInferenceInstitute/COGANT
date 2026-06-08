# Validation

> The COGANT validation pipeline: how generated GNN packages, role assignments, and roundtrip artifacts are checked for correctness, completeness, and policy compliance. Read this section if you are debugging a failed scan, authoring custom validators, or wiring COGANT into CI.

## Contents

| Page | Description | Level |
|------|-------------|-------|
| [Overview](overview.md) | What the validation layer does and where it sits in the pipeline | Beginner |
| [Validation via CLI](validation_via_cli.md) | Running validators from the command line | Beginner |
| [Validation Stages](validation_stages.md) | Stage-by-stage walk through the validation pipeline | Intermediate |
| [Issue Levels](issue_levels.md) | Severity model: error, warning, info | Beginner |
| [Issue Categories](issue_categories.md) | Categorical taxonomy of validation issues | Intermediate |
| [Validation Report](validation_report.md) | Schema and consumer guide for the validation report artifact | Intermediate |
| [Thresholds and Policies](thresholds_policies.md) | Configurable thresholds and gating policies | Intermediate |
| [Custom Validators](custom_validators.md) | Authoring and registering your own validators | Advanced |
| [Audit Trail](audit_trail.md) | Reproducible audit trail of validator runs | Intermediate |
| [Verification and Test Posture](verification_and_test_posture.md) | How COGANT itself is tested and verified | Advanced |
| [COGANT Implementation Verification Report](cogant_implementation_verification_report.md) | Snapshot verification report for the implementation | Advanced |
| [See Also](see_also.md) | Cross-links to related documentation | Beginner |

## Getting started

New to the validation layer? Read [Overview](overview.md) for what it does, then run [Validation via CLI](validation_via_cli.md) to generate your first report. The **Recommended Reading Order** below links these steps in sequence.

## Recommended Reading Order

1. [Overview](overview.md) — understand what is being validated and why.
2. [Validation via CLI](validation_via_cli.md) — run a validation pass yourself.
3. [Issue Levels](issue_levels.md) and [Issue Categories](issue_categories.md) — learn how to read a report.
4. [Validation Stages](validation_stages.md) — see which stage produces which findings.
5. [Validation Report](validation_report.md) and [Thresholds and Policies](thresholds_policies.md) — wire results into CI gates.
6. [Custom Validators](custom_validators.md) — extend the system once you understand the defaults.
7. [Audit Trail](audit_trail.md) and [Verification and Test Posture](verification_and_test_posture.md) — operational and assurance considerations.

Agent notes: [AGENTS.md](AGENTS.md) - Hub: [../index.md](../index.md)
