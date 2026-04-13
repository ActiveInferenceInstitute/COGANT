# AGENTS.md — Theory module

Formal theoretical background for COGANT: Active Inference, the
"code as generative model" thesis, the GNN intermediate representation,
and the isomorphism theorem. Unlike `../concepts/`, which is expressly
informal, theory pages are expected to be defensible at a workshop-paper
level of rigour.

## Purpose and ownership

This module is the written half of the scientific record. It has to stay
consistent with the manuscript under `../../../manuscript/` and the dated
empirical studies under `../evaluation/`. Owned by whoever is editing the
manuscript or running the formal proof track.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC and recommended reading order | Any time a file is added, removed, or renamed |
| `AGENTS.md` | This file — maintenance rules | When ownership, notation conventions, or the manuscript-consistency policy changes |
| `active_inference_primer.md` | Short introduction for readers new to Active Inference | When the primer's audience or vocabulary changes |
| `active_inference.md` | Theoretical justification for the code-to-role mapping | When the mapping, the rule rationale, or the matrices change |
| `code_as_generative_model.md` | The "code is a generative model" thesis | When the thesis is refined or extended |
| `gnn_format.md` | Short narrative on the GNN format as COGANT uses it | When the headline story about GNN changes |
| `gnn_format_reference.md` | Exhaustive reference for the 18-section GNN package | When a section is added, removed, or renamed in the AII GNN spec or the COGANT emitter |
| `isomorphism.md` | Formal statement and proof sketch of the isomorphism theorem | When the theorem statement, assumptions, or proof outline changes |

## Notation and consistency

- Every symbol used in multiple pages (for example `A`, `B`, `C`, `D`
  matrices, hidden states, observations, actions) has to match the
  manuscript's appendix on inference mathematics. When you rename a
  symbol, grep `docs/` and `manuscript/` and update both in the same PR.
- `active_inference.md` is the theory-track counterpart to
  `../evaluation/ACTIVE_INFERENCE_MAPPING.md`. The evaluation file is
  dated and citable; this file is the stable, non-dated statement. Keep
  them in agreement but do not merge them.
- `gnn_format.md` defers to the upstream Active Inference Institute spec
  where it exists. Do not fork the spec; cite it.

## Adding a new doc

1. Pick a short, lower-case, underscore-separated slug.
2. Open with a one-sentence claim and a "Status" line (draft / stable /
   superseded).
3. Put formal definitions and theorem statements in clearly numbered
   blocks so the manuscript can cite them by number.
4. Add a row to the `## Contents` table in `README.md`.

## Known gotchas

- `isomorphism.md` is the theorem the whole project rests on. Do not
  weaken its statement without updating the manuscript, the evaluation
  roundtrip study, and `../concepts/roundtrip.md` in the same PR.
- `gnn_format.md` and `gnn_format_reference.md` overlap deliberately: the
  short page orients a first-time reader, the reference page enumerates
  the 18 sections. When the upstream GNN spec changes, update the
  reference first and then the short page.
