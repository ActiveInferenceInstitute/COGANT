# AGENTS.md — Getting started module

The shortest path from "I have never heard of COGANT" to "I just analyzed
my first repository". Two pages only: install the tool, then run the
quickstart. The module is intentionally tiny — depth lives in
`../tutorials/` and `../concepts/`.

## Purpose and ownership

Every sentence here has to survive a cold read by a user who does not know
what COGANT is. If you find yourself wanting to explain *why* something
works, move that sentence into `../concepts/` and link to it. Owned by
whoever last shipped a CLI or install change that a new user would trip on.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC and recommended first 15 minutes of the docs | When install or quickstart flows materially change |
| `AGENTS.md` | This file — maintenance rules | When the "two pages only" policy or ownership changes |
| `installation.md` | `pip` / `uv` install instructions and `cogant doctor` verification | When install steps change, a new optional extra ships, or a platform breaks |
| `quickstart.md` | First `cogant scan` run end-to-end on a sample repository | When the CLI default output, scan flags, or sample repo change |

## Adding a new doc

Do not add a third page unless you are certain it belongs in the onboarding
spine. In almost every case the right place is either
`../tutorials/` (for a longer walkthrough) or `../cookbook/` (for a specific
how-to). If you really do need a third getting-started page:

1. Pick a short, lower-case, underscore-separated slug.
2. Keep it under 100 lines and 5 minutes of hands-on time.
3. Add a row to the `## Contents` table and put the page at the right place
   in the `## Recommended Reading Order`.
4. Cross-link forward to `../tutorials/01_quickstart.md` so readers know
   where to go next.

## Known gotchas

- Do not include architecture discussion here. A new user does not need
  to know what a Markov blanket is before running their first scan.
- Every command shown must be copy-pasteable into a fresh shell. No
  implicit environment variables, no "assume you have X already".
- `installation.md` and the root `README.md` of the package can drift.
  When editing install steps, grep the repo for `pip install cogant` and
  update every occurrence in the same PR.
