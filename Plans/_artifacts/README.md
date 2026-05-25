# Plan Artifacts

Command-output snapshots supporting the planning notes in [`..`](..).

These files are intentionally low-ceremony text captures from audits, lint
checks, cross-reference checks, claim-ledger runs, and sanity probes. They are
useful for reconstructing why a plan was written, but they are not current
verification evidence after the worktree changes.

## Use

- Add new snapshots only when they help explain a plan or review decision.
- Prefer plain `.txt` output with the command name in the filename.
- Re-run the corresponding command before relying on an artifact in active
  documentation or manuscript prose.
