# AGENTS.md — R&D notes module

Exploratory, work-in-progress research notes for the COGANT program.
Everything here is deliberately less polished than `../evaluation/`: notes
are scratchpads for active experiments, not dated gate reports. Treat any
content in this module as provisional unless it has been promoted to
`../evaluation/`, `../theory/`, or `../concepts/`.

## Purpose and ownership

`rnd/` is where an idea lives before anyone is willing to commit to it.
Once a note stabilizes — a mapping is locked down, a calibration result is
re-measured on a second dataset, a theoretical claim is written up — the
content moves to a more formal module and a short stub with a redirect
note is left behind here. Owned by whoever is actively running
experiments on that topic.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC and "how this differs from `../evaluation/`" guidance | When a note is added, renamed, or promoted out |
| `AGENTS.md` | This file — maintenance rules | When the promotion-out policy or ownership changes |
| `active_inference_mapping.md` | Scratchpad for the code-pattern to AI-role mapping | When a new mapping is being prototyped |
| `calibration.md` | Calibration backlog, open questions, and confidence-model notes | When a calibration experiment runs or a new open question surfaces |

## Promotion policy

A note graduates out of `rnd/` when all of the following are true:

1. The claim has been measured or checked twice, independently.
2. Another contributor has reviewed the writeup.
3. A stable home in `../evaluation/`, `../theory/`, or `../concepts/`
   exists or is about to.

When all three hold, move the content to the new home, leave a short stub
in `rnd/` that points at the new location, and update the `README.md`
table in both modules.

## Adding a new note

1. Pick a short, lower-case, underscore-separated slug.
2. Open with a one-sentence framing of the open question and a dated
   "Status" line so future readers know when the note was last touched.
3. Link to the relevant evaluation pages for context instead of repeating
   numbers or definitions.
4. Add a row to the `## Contents` table in `README.md`.

## Known gotchas

- Do **not** cite `rnd/` pages from `../evaluation/`, `../theory/`, or the
  manuscript. If an R&D note is solid enough to cite, it should be
  promoted first.
- The evaluation module has canonical counterparts for several `rnd/`
  topics (for example `rnd/active_inference_mapping.md` mirrors
  `../evaluation/ACTIVE_INFERENCE_MAPPING.md`). Keep the rnd version as
  the scratchpad and the evaluation version as the citable one.
