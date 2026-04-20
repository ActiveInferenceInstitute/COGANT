# Signposting & Nav Audit — Wave 19

**Agent:** `signposting-nav-agent`
**Date:** 2026-04-10
**Scope:** `mkdocs.yml` nav completeness and discoverability

## Goal

Make every documentation page reachable from the mkdocs nav, and add a
"Learning Paths" section so newcomers, API users, theorists, plugin authors,
and contributors all have a curated entry sequence rather than having to
guess which page to read first.

## Method

1. Parsed `mkdocs.yml` to extract every `*.md` reference in the `nav:`.
2. Walked `docs/` for every `.md` file, excluding `AGENTS.md` and the
   `architecture/` subtree (per the task brief — the `architecture/` section
   was already complete and out of scope for this sweep).
3. Computed the set difference (`filesystem - nav`) to find unreferenced
   pages.
4. Added each unreferenced page to the most appropriate existing nav
   section.
5. Created `docs/learning-paths/` with five persona-curated paths.
6. Added a `Learning Paths` top-level nav section, placed between
   `Getting Started` and `Guides` so it sits where new users land.
7. Re-validated by parsing the updated `mkdocs.yml` with PyYAML and asserting
   that every nav entry resolves to an on-disk file.

## Findings — files that existed but were unreferenced

Total unreferenced pages found: **103**.

Distribution by section:

| Section            | Unreferenced count | Notes                                              |
| ------------------ | ------------------ | -------------------------------------------------- |
| `cli/`             | 14                 | Entire mini-site of per-topic CLI docs was orphaned |
| `reference/`       | 36                 | Many legacy how-to and stub pages from earlier docs sweeps |
| `evaluation/`      | 21                 | All R&D reports except CALIBRATION/ROUNDTRIP_EVAL/V1.0_READINESS were unlinked |
| `roadmap/`         | 12                 | Several auxiliary roadmap pages (benchmarks, contingencies, see_also, etc.) |
| Section `README.md` indices | 13         | One per section: api, cli, concepts, export, getting-started, guides, plugins, reference, rnd, roadmap, rules, security, tutorials, validation |
| `validation/`      | 4                  | archival_note, verification_and_test_posture, implementation_verification_report, see_also |
| `security/`        | 5                  | future_improvements, python_package_audit_module_exports, references, security_documentation, see_also |
| `plugins/`         | 2                  | plugin_taxonomy_abstract_bases, see_also |
| `api/`             | 3                  | installation, quick_start, see_also |
| `rules/`           | 1                  | see_also |
| `export/`          | 1                  | see_also (README handled in indices row) |

(Counts above are approximate buckets — exact list is the 103 files surfaced
by the diff script in the working notes.)

The biggest single discovery: the `cli/` mini-site of fourteen task-oriented
pages was completely invisible in nav. Anyone hunting for environment
variables, troubleshooting tips, or the command index had no path through the
sidebar — they had to know the URL. Same story, on a smaller scale, for the
36 `reference/` how-to stubs.

## Fix — what changed in `mkdocs.yml`

1. **Added `Learning Paths` top-level section** between `Getting Started`
   and `Guides`, with five entries: New User, API Consumer, Theory Reader,
   Plugin Author, Contributor.
2. **Added `Section Index: <area>/README.md`** as the first child of every
   section that had an unlinked README (13 sections).
3. **Expanded `CLI Reference`** from a single-page link into a section
   containing the legacy single-page reference plus all 14 cli/* pages.
4. **Expanded `API Reference`** to include `installation`, `quick_start`,
   and `see_also`.
5. **Expanded `Plugins`** to include `plugin_taxonomy_abstract_bases` and
   `see_also`.
6. **Expanded `Validation`** to include `verification_and_test_posture`,
   `cogant_implementation_verification_report`, `archival_note`, `see_also`.
7. **Expanded `Rules`** to include `see_also`.
8. **Expanded `Export`** to include `see_also`.
9. **Expanded `Security`** to include `future_improvements`,
   `python_package_audit_module_exports`, `security_documentation`,
   `references`, `see_also`.
10. **Expanded `Reference`** with 36 newly-linked pages, grouped by purpose
    (overview, schemas, implementation status, "How-To" stubs, next steps).
11. **Expanded `Evaluation`** with all 21 unlinked R&D reports
    (FINAL_REPORT, EMPIRICAL_CLAIM, MUTATION_REPORT, ISOMORPHISM_THEOREM,
    SCALING_ANALYSIS, RELEASE_NOTES_v0.{2,5}.0, etc.) in a logical order:
    overview → final/readiness → calibration/empirical → mappings → roundtrip
    → benchmarks → real-world → literature → release notes.
12. **Expanded `Roadmap`** with 12 newly-linked pages (benchmarks,
    cogant_benchmarks, community_milestones, contingencies, budget_resources,
    documentation_roadmap, related_work, success_metrics_post_10,
    changelog, see_also).
13. **Added `Section Index: rnd/README.md`** to R&D.

## Learning paths created

`docs/learning-paths/` (new directory, five files):

| File                         | Persona            | Estimated time   |
| ---------------------------- | ------------------ | ---------------- |
| `new-user.md`                | New User           | ~45m read + 30m hands-on |
| `api-consumer.md`            | API / Integration  | ~90m read + 2h hands-on |
| `theory-reader.md`           | Researcher / Reviewer | ~3h read |
| `plugin-author.md`           | Extender           | ~2h read + half-day hands-on |
| `contributor.md`             | Contributor        | ~2h read |

Each path is a numbered list of 4–6 docs with one-paragraph context per step
plus an "adjacent reading" section and a "where to go next" section that
cross-links to the other paths. All links use mkdocs-style relative paths
(`../concepts/gnn.md` etc.) and were verified to point at files that exist.

## Verification

Final state, confirmed by re-parsing `mkdocs.yml` with PyYAML and walking
the nav tree:

- **Nav entries:** 294 `.md` files referenced (up from 164).
- **Filesystem entries (excluding AGENTS.md, architecture/):** 269.
- **Unreferenced filesystem files:** 0.
- **Nav entries pointing at non-existent files:** 0 (the only "extra" in nav
  is `theory/AGENTS.md`, which exists — it was filtered out of the audit
  scope but is correctly referenced).
- **YAML parses cleanly:** yes.
- **`manuscript/` touched:** no.

The 25-entry gap between "294 nav entries" and "269 filesystem files" is
accounted for by the `architecture/` subtree, which was already fully linked
in nav before this sweep and is out of scope for the audit.

## Files touched

- `mkdocs.yml` — nav expansion + Learning Paths section
- `docs/learning-paths/new-user.md` (new)
- `docs/learning-paths/api-consumer.md` (new)
- `docs/learning-paths/theory-reader.md` (new)
- `docs/learning-paths/plugin-author.md` (new)
- `docs/learning-paths/contributor.md` (new)
- `_rnd/sweep_2026_04/signposting_nav_audit.md` (this file)

No file under `manuscript/` was read or modified.

## Followups (out of scope for this wave)

1. Several `reference/` pages are clearly stub how-tos from an earlier docs
   sweep (one-line "navigate to python package directory" type entries).
   They are now linked, but they should probably be consolidated or
   absorbed into the proper `getting-started/` and `guides/` flows in a
   future cleanup wave.
2. The `cli/` mini-site duplicates content from the single-page
   `cli_reference.md`. A future wave should pick one canonical source and
   redirect the other.
3. The `Reference` section is now very long (40+ entries). Consider
   subdividing into "Conceptual Reference", "API/Schema Reference", and
   "How-To Reference (legacy)" in a follow-up.
4. The Learning Paths cross-link to `AGENTS.md` from the project root in the
   Contributor path; mkdocs will not serve files outside `docs/`. The link
   currently reads as descriptive text with the path explicit; if tighter
   integration is wanted, copy the relevant working-conventions content into
   `docs/AGENTS.md` (which is already inside the doc tree).
