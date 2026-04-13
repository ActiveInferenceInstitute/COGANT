# AGENTS.md — Guides module

Narrative, prose-style guides that sit between the terse
`../getting-started/` pages and the deeper `../tutorials/` walkthroughs.
Guides explain *why* a workflow exists and *when* to choose it, with less
hand-holding than a tutorial but more context than a cookbook recipe.

## Purpose and ownership

A guide is a mental-model consolidation exercise: after reading the
getting-started pages, a reader should be able to pick up a guide and come
out the other end with a durable understanding of the end-to-end flow. The
module is intentionally small — we would rather have one great guide than
five mediocre ones. Owned by whoever last shipped a user-facing workflow
change.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC and recommended reading order | When a guide is added, renamed, or removed |
| `AGENTS.md` | This file — maintenance rules | When the "narrative, not steps" policy or ownership changes |
| `first_project.md` | End-to-end `translate → roundtrip → interpret` narrative on the `examples/zoo/01_simple_state` fixture | When the zoo fixture, CLI contract, or interpretation flow changes |

## Adding a new guide

1. Pick a short, lower-case, underscore-separated slug (for example
   `plugin_development_workflow.md`).
2. Open with the audience and the pain point: who should read this and
   what problem does it solve for them.
3. Narrate the flow end-to-end. Include just enough commands that a reader
   can follow along, but keep the emphasis on *why* each step matters.
   If the page becomes dominated by copy-pasted commands, it is really a
   cookbook recipe — move it to `../cookbook/` instead.
4. Add a row to the `## Contents` table in `README.md` and place the guide
   in `## Recommended Reading Order`.
5. Cross-link to related tutorial, cookbook, and concept pages instead of
   duplicating their content.

## Known gotchas

- This module is easy to confuse with `../tutorials/` and `../cookbook/`.
  Rule of thumb: a tutorial teaches, a cookbook recipe executes, a guide
  explains. If a proposed page would mostly be a sequence of shell blocks
  with minimal prose, it is a cookbook recipe.
- The `first_project.md` slug is intentionally distinct from
  `getting-started/quickstart.md`: the latter is a five-minute taster, the
  former is a half-hour consolidation. Do not merge them.
