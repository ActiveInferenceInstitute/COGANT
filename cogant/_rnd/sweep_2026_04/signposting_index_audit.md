# Wave 19 Signposting / Section Index Audit

**Agent:** `signposting-index-agent`
**Date:** 2026-04-10
**Scope:** Every `docs/<section>/README.md` should have (a) a one-paragraph description, (b) a Contents table with descriptions and difficulty level, and (c) a Recommended Reading Order.

> **Note on parallel execution:** A sibling Wave 19 signposting agent (commit `23a0cd9 docs(w19/signposting): mkdocs nav audit + learning paths (5 personas)`) committed README rewrites for 14 of the 15 target sections in parallel with this agent's work. After re-reading every README on disk, the content of those 14 files matched this agent's intended rewrite — same audience-paragraph + Contents table + Recommended Reading Order format — so this agent's local edits collapsed to no-ops against `HEAD`. The audit below describes what each README *should* contain (and now does); the only file with this agent's diff still pending was `docs/architecture/README.md`, which a different sibling agent had additively enriched with a "Pipeline stage → API reference" cross-reference table. That sibling enrichment was preserved and re-applied on top of this agent's restructured architecture index. The end state: all 15 READMEs are substantive, and the architecture README now contains both the layered restructure from this agent and the API cross-reference table from the crosslink-architecture-api sibling.

## Method

For each target subdirectory:

1. Listed the directory contents to enumerate the actual pages.
2. Read the existing `README.md` (none of the targets used `index.md` instead).
3. Categorized as **substantive** (already has the three required sections) or **hollow** (flat link list, missing reading order, missing levels, etc.).
4. Rewrote the README in the standard signposting format. The format always contains:
   - H1 with the section name.
   - One blockquote-style description paragraph naming audience and intent.
   - One or more Contents tables with `Page | Description | Level` columns.
   - A numbered Recommended Reading Order.
   - Footer with AGENTS / hub cross-links where they previously existed.

No new pages were created. Only the section README files were edited.

## Per-section status

| Section | Before | After | Notes |
|---|---|---|---|
| `docs/concepts/` | Hollow (12 lines, flat list) | Substantive (25 lines, table + reading order) | 6 concept pages organized Beginner -> Advanced. |
| `docs/tutorials/` | Hollow (13 lines, flat numbered table only) | Substantive (29 lines) | 7 numbered tutorials + calculator/flask companion docs, with reading order. |
| `docs/api/` | Hollow (24 lines, flat list with duplicate Overview entry) | Substantive (69 lines) | Reorganized into Orientation / Core Orchestration / Translation+Scoring+Review / Analysis / Extension / Operational. Duplicate Overview removed. |
| `docs/architecture/` | Long but flat (108 lines, ~100 unstructured links, generated-name pages with bracketed JSON in titles) | Substantive (137 lines) | Pulled out Orientation, Cross-cutting concerns, Pipeline stages (canonical 6+ingest), and grouped the long tail of stage-by-stage step pages into a single appendix table tagged by stage. Reading order recommends the canonical six stages. |
| `docs/getting-started/` | Hollow (6 lines) | Substantive (18 lines) | Two pages, Beginner level, with onward pointers to tutorials/concepts. |
| `docs/guides/` | Hollow (7 lines) | Substantive (15 lines) | Single guide, but framed against getting-started and tutorials for navigation. |
| `docs/reference/` | Long but flat (45 lines, all 40+ pages in one bullet list) | Substantive (89 lines) | Reorganized into Orientation / Concepts+Architecture / Schemas+Data / Configuration+CLI / Operational Recipes / Implementation Snapshots. |
| `docs/validation/` | Hollow (19 lines, flat list) | Substantive (33 lines) | Single contents table sorted by validation lifecycle, reading order from Overview to Custom Validators. |
| `docs/rules/` | Hollow (15 lines, flat list) | Substantive (34 lines) | Reading order walks Overview -> Core Rules -> Custom Rules -> Testing -> Conflict Resolution -> Performance/Debugging. |
| `docs/security/` | Hollow (18 lines, flat list) | Substantive (37 lines) | Threat-model-first ordering; Responsible Disclosure flagged Beginner so external reporters land on it quickly. |
| `docs/cookbook/` | Substantive table but missing Level and Reading Order (43 lines) | Substantive (55 lines) | Added Level column to all 20 recipes and a Recommended Reading Order pointing at the highest-leverage recipes (01, 02, 03, 04, 08/09, 06/14). Preserved the existing Prerequisites block. |
| `docs/evaluation/` | Substantive table but missing Level and Reading Order (22 lines) | Substantive (63 lines) | Reorganized into Release Readiness / Theory / Empirical Studies / Bibliography. Added every doc that exists in the directory (the previous table was incomplete). |
| `docs/plugins/` | Hollow (14 lines, flat list) | Substantive (31 lines) | Reading order picks the right base class first, then the plugin-type-specific page, then publishing. |
| `docs/notebooks/` | Hollow placeholder ("Coming soon") that listed only the planned 01-06 notebooks even though 12 notebooks now exist | Substantive (39 lines) | All 12 notebooks listed with description+level. Background cross-links from the previous version preserved. Run instructions retained. |
| `docs/rnd/` | Hollow (8 lines) | Substantive (19 lines) | Frames the section as provisional working notes vs. the dated reports under `evaluation/`. |

## Constraints respected

- **No edits under `manuscript/`.** `git status --short | grep -i manuscript` returned empty.
- **No new files created under `docs/`.** Only the 15 target README files were touched. The audit summary is written to `_rnd/sweep_2026_04/`, not `docs/`.
- **No `index.md` created** where a `README.md` already existed. The format expected by the task allows either; we kept the existing convention (`README.md`) for every section.
- **Existing cross-links retained**: AGENTS.md links and `../index.md` hub links from the previous READMEs were preserved in the new versions.
- **Front-matter / generation banners**: none of the touched READMEs had them, so none were stripped.

## Caveats

1. The `docs/architecture/` directory contains ~100 generated step-by-step pages, several of which have bracketed JSON or example output in their titles (e.g. `totalidentities_n_uniquehashinputs_m_typemodule_x.md`). These are listed in the appendix table with cleaned-up display names rather than as a flat dump. They probably want a follow-up consolidation pass in a separate wave; flagging here so it does not get lost.
2. The `docs/api/README.md` previously had a duplicate `[Overview](overview.md)` line. Removed in the rewrite.
3. The `docs/notebooks/README.md` was a "Coming soon" placeholder. The directory now actually contains 12 notebooks, several of which only exist as `.ipynb` (no `.md`). The new index links to `.md` where it exists and falls back to `.ipynb` otherwise.
4. Levels (Beginner / Intermediate / Advanced / Reference) are this agent's best-effort classification based on the page name and section context, not on a manual read of every single page. Subsequent waves are encouraged to refine.

## Next-wave suggestions

- Consolidate the long tail of `docs/architecture/step_*` and `parse_*` / `analyze_*` / `extract_*` pages into a smaller number of stage-overview pages, then have the README link to those.
- Generate `.md` siblings for the four notebooks that currently only ship as `.ipynb` (07, 08, 09, 10, 11, 12) so the docs site has rendered versions.
- Decide whether `docs/getting-started/` and `docs/guides/` should be merged (they overlap) or split more cleanly.
