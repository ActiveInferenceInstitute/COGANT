# AGENTS.md — Concepts module

Conceptual primers for COGANT contributors and AI agents: Active Inference,
Generalized Notation Notation (GNN), Markov blankets, the program graph
abstraction, role assignment, and the forward/reverse roundtrip. The goal of
this module is to give readers the minimum vocabulary they need to follow the
rest of the documentation without drowning in math or implementation detail.

## Purpose and ownership

Short, opinionated primers — not a textbook and not an API reference. When
a concept has a longer, formal treatment elsewhere, this module links out
to it (usually to `../theory/` or `../evaluation/`). Owned by whoever is
editing the manuscript or theory track; keep definitions in lockstep with
`manuscript/S04_appendix_inference_mathematics.md` and
`../theory/isomorphism.md`.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC for the module and recommended reading order | Any time a file is added, removed, or renamed here |
| `AGENTS.md` | This file — maintenance rules | When the ownership, filename conventions, or cross-link policy changes |
| `active_inference.md` | Primer on the Free Energy Principle and the roles COGANT uses | When the role vocabulary or FEP framing changes |
| `gnn.md` | What a GNN package is, why COGANT emits one | When the GNN IR spec changes materially (see `../theory/gnn_format_reference.md`) |
| `markov_blanket.md` | How sensory/active/internal/external partitions are derived | When the blanket derivation algorithm changes |
| `program_graph.md` | The static + dynamic program-graph abstraction | When the program-graph schema or extraction pipeline changes |
| `role_assignment.md` | Code-to-role mapping and confidence model | When rule-engine defaults or the confidence model change |
| `roundtrip.md` | Forward/reverse roundtrip and the isomorphism criterion | When the isomorphism or equivalence definition changes |

## Adding a new doc

1. Pick a short, lower-case, underscore-separated slug (for example
   `free_energy.md`). Avoid numeric prefixes — this module is read
   topically, not sequentially.
2. Open with a one- or two-sentence definition that a newcomer can understand.
3. Defer formal math to `../theory/` and link to it instead of inlining proofs.
4. Add a row to the `## Contents` table in `README.md` with a 5-15 word
   description and a difficulty level (`Beginner | Intermediate | Advanced`).
5. Update the recommended reading order in `README.md` if the new page
   belongs in the main spine rather than as a leaf.

## Known gotchas

- Keep terminology consistent with the manuscript. If you change a defined
  term (for example "Markov blanket" vs. "Markov boundary") here, mirror the
  change in `manuscript/` and search the rest of `docs/` for inconsistent usage.
- `roundtrip.md` and `../theory/isomorphism.md` cover overlapping ground; the
  concepts page is the gentle introduction and `theory/isomorphism.md` is the
  formal statement. Keep them in agreement but do not merge them.
