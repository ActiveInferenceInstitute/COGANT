# Plans

Working notes for broad COGANT review, red-team, and improvement passes.
These files are planning and audit records, not package runtime inputs.

Use this directory for durable planning artifacts that explain why a broad
docs, manuscript, evaluation, or validation pass changed scope. Keep generated
command output under [`_artifacts/`](_artifacts/) so the narrative plans stay
readable.

## Contents

- `FIRST_PRINCIPLES_AUDIT.md` - first-principles project review notes.
- `IMPROVEMENTS_2026-05-19.md` - improvement backlog from the May 2026 sweep.
- `PRE_STATE_2026-05-19.md` - pre-change state capture for the same sweep.
- `REDTEAM_FINDINGS.md` - adversarial review findings and follow-up notes.
- `WORLD_THREAT_MODEL_COGANT_2026-05-21.md` - COGANT-specific horizon stress
  test using the WorldThreatModelHarness frame and Perplexity research signals.
- `_artifacts/` - text snapshots from verification commands and audits.

## Ground Rules

- Do not treat these files as authoritative package documentation; update
  `README.md`, `AGENTS.md`, `manuscript/`, or `cogant/docs/` when behavior
  changes.
- Do not cite command-output snapshots as current truth without re-running the
  underlying command.
- Keep filenames date- or topic-scoped so later audits can distinguish active
  plans from historical notes.
