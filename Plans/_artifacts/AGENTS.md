# AGENTS.md - plan artifact snapshots

This directory stores raw or lightly trimmed command-output snapshots for
planning records.

## Rules

- Do not edit these files to make a validation result look current.
- Do not cite these snapshots as proof of present repository health; rerun the
  original command and cite the fresh output instead.
- Keep generated logs small enough to review. If output is too large, store a
  focused excerpt and name the command that produced it in the parent plan.
- Avoid adding secrets, credentials, local absolute temporary paths, or private
  repository URLs to stored snapshots.
