# Signposting Headers Audit — Wave 19

**Agent:** `signposting-headers-agent`
**Date:** 2026-04-10
**Working dir:** `projects_in_progress/cogant/cogant`

## Goal

Add a consistent four-line signposting block (What this page is / Prerequisites / Reading time / Next steps) to all substantive doc pages in `docs/`, immediately after the H1 (or top H2 where no H1 exists), so readers can orient themselves before reading the body.

## Format applied

```markdown
> **What this page is:** [one-sentence description]
>
> **Prerequisites:** [what to read/know first — or "None"]
>
> **Reading time:** [~X minutes]
>
> **Next steps:** [Link1](path) · [Link2](path) · [Link3](path)
```

All "Next steps" links are relative paths that resolve to real files under `docs/`.

## Pages updated (29 total)

### `docs/concepts/` — 6 / 6
- `active_inference.md`
- `gnn.md`
- `markov_blanket.md`
- `program_graph.md`
- `role_assignment.md`
- `roundtrip.md`

### `docs/tutorials/` — 9 / 9
- `01_quickstart.md`
- `02_small_repo_walkthrough.md`
- `03_flask_walkthrough.md`
- `04_custom_rules.md`
- `05_gnn_interpretation.md`
- `06_reverse_mode.md`
- `07_plugin_authoring.md`
- `calculator.md`
- `flask.md`

### `docs/getting-started/` — 2 / 2
- `installation.md`
- `quickstart.md`

### `docs/guides/` — 1 / 1
- `getting_started.md`

### `docs/api/` — 6 (overview / quick_start / installation + Session / PipelineRunner / Bundle)
- `overview.md`
- `quick_start.md`
- `installation.md`
- `session_api.md`
- `pipelinerunner_api.md`
- `bundle_api.md`

### `docs/reference/` — 3
- `overview.md`
- `core_concepts.md`
- `glossary.md`

### Top-level — 2
- `docs/index.md`
- `docs/faq.md`

## Pages skipped

- `AGENTS.md` files in every subdirectory (per binding rules — agent guidance, not user docs)
- `README.md` files in every subdirectory (auto-generated indexes)
- Auto-generated architecture stubs under `docs/architecture/` (deferred to a future signposting pass)
- `manuscript/` — never touched (binding rule)
- API reference pages that are pure mkdocstrings `:::` directives or under ~80 lines without a clear narrative entry (`gnn.md`, `markov.md`, `runtime.md`, `static.md`, `translate.md`, `plugin_api.md` — handled by other w19 agents)

## Link policy

Each "Next steps" triplet was chosen to match the page's position in the learning flow:

- **Concepts** → other concept pages, then a tutorial that exercises the concept.
- **Tutorials** → adjacent tutorials and the closest API reference page.
- **API** → adjacent API references plus a tutorial that demonstrates the API.
- **Reference** → other reference pages plus core concept pages.
- **Top-level (`index.md`, `faq.md`)** → installation, first tutorial, primary concept page.

All link targets verified to exist with `ls` before commit.

## Coordination notes

This wave ran in parallel with several other w19 agents
(`crosslink-rnd`, `validate-api-signatures`, `coherence-terminology`,
`learning-paths`). Many of the per-page signposting edits in this audit
were already swept into the following commits by parallel agents that
also touched the same files:

- `40862a9 docs(w19/validate): API signature drift fixes`
- `32d3abb docs(w19/crosslink): tutorials → theory/concepts back-links`
- `9cf9a8b docs(w19/coherence): terminology normalization`
- `23a0cd9 docs(w19/signposting): mkdocs nav audit + learning paths`

The remaining unstaged edits owned by this agent — the API stable-class
references, the reference index pages, the FAQ, the program-graph
concept page, and tutorials 02 / 05 — are the subject of this commit.

## Verification

```bash
grep -l "What this page is" docs/concepts/*.md docs/tutorials/*.md \
  docs/getting-started/*.md docs/guides/*.md docs/api/*.md \
  docs/reference/*.md docs/index.md docs/faq.md
```

Returns 29 paths — every targeted page now opens with the signposting
block.
