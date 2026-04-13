# AGENTS.md — Learning paths module

Curated reading orders through the rest of the COGANT documentation,
organized by audience. Each path is almost pure links — a learning path
should *route* a reader, not duplicate content. Owned by whoever owns the
overall docs information architecture.

## Purpose and ownership

Learning paths solve the "where do I start?" problem. New contributors,
new users, and AI agents arriving at the docs for the first time need a
breadcrumb trail instead of a flat file list. Each path is curated for a
specific audience and kept short enough to be actionable.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC of the five paths | When a path is added, removed, or retargeted |
| `AGENTS.md` | This file — maintenance rules | When the "links not content" policy or ownership changes |
| `new-user.md` | Shortest path from zero to "first scan read" | When getting-started or tutorials spine changes |
| `api-consumer.md` | Embedding COGANT in a Python service or pipeline | When API, runner, or config surfaces change |
| `theory-reader.md` | Researchers and reviewers; "why" before "how" | When `../concepts/`, `../theory/`, or `../evaluation/` structure changes |
| `plugin-author.md` | Adding languages, rules, validators, or exporters | When `../plugins/` structure or the plugin tutorial changes |
| `contributor.md` | Working on the repository itself: code, tests, docs | When `AGENTS.md` at the repo root, the test policy, or the roadmap changes |

## Adding a new path

1. Only add a path if an identifiable audience is currently poorly served
   by the existing five. Prefer to extend an existing path first.
2. Use a short, lower-case, hyphenated slug that names the audience, not
   the subject (for example `security-auditor.md`, not `threat-model.md`).
3. Structure every path identically: audience paragraph, estimated time,
   numbered reading list with a one-sentence rationale per link, and a
   short "what next" section that hands off to another path or module.
4. Do not inline concept explanations or command examples; link out to the
   canonical page instead. A learning path should be ~80 percent links
   and ~20 percent commentary.
5. Add a row to the `## Contents` table in `README.md`.

## Known gotchas

- This module is **not** content. If a page here starts growing its own
  prose sections, the content belongs in `../concepts/`, `../guides/`, or
  `../cookbook/` instead, and the path should link to it from there.
- Cross-module links here are load-bearing. Run
  `uv run python docs/verify_doc_links.py` after every edit and fix any
  broken targets before merging.
- The filenames use hyphens rather than underscores to match the existing
  `new-user.md` / `api-consumer.md` convention. Do not mix conventions
  inside this module.
