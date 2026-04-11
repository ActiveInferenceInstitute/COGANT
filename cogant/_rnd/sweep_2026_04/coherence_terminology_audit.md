# Wave 19 — Coherence & Terminology Audit

**Agent:** `coherence-terminology-agent`
**Date:** 2026-04-10
**Scope:** `cogant/docs/**/*.md` (excluding `manuscript/` — none present in this worktree).
**Authoritative glossary:** `cogant/docs/reference/glossary.md`.

## Summary

The audit normalized terminology across the COGANT documentation tree against a canonical
glossary. The glossary itself was extended with a "Canonical conventions" preface and
sixteen new or expanded entries. Five doc files received targeted normalization edits.
No `manuscript/` files were touched (none exist in the cogant subtree).

## Canonical term forms (now enshrined in glossary preface)

| Canonical | Variants normalized |
| --- | --- |
| `HIDDEN_STATE`, `OBSERVATION`, `ACTION`, `POLICY`, `CONSTRAINT`, `CONTEXT` | `hidden state`, `HiddenState`, `hidden_state`, lowercase role mentions in role-label contexts |
| `A matrix`, `B matrix`, `C matrix`, `D matrix` | `A_matrix`, `a_matrix`, `A-matrix` |
| `forward pipeline` / `reverse pipeline` | `forward pass` / `reverse pass` (operational contexts only — preserved in `ISOMORPHISM_THEOREM.md` for the categorical framing) |
| `fixpoint` | `fix-point`, `fixed point`, `fixed-point` |
| `ε` | "accuracy", "similarity" — explicitly **not** these |
| `ISOMORPHIC`, `APPROXIMATE`, `DIVERGENT` | lowercase tier names |
| `Markov blanket` | `markov blanket` (capitalized only in headings) |
| `Galois connection` | `galois connection` (capitalized only in headings) |
| `ε-bounded adjunction` | `epsilon-bounded`, `ε bounded` |
| `GNN` = Generalized Notation Notation | Graph Neural Network in COGANT-pipeline contexts |
| `PackagePlan`, `ProgramGraph`, `ReverseGNNModel` | `package_plan`, `program_graph`, `reverse_gnn_model`, `Package Plan`, `Program Graph`, `Reverse GNN Model` (in type-reference contexts) |

## Glossary changes

`docs/reference/glossary.md` (+148 / -25 lines):

1. **New "Canonical conventions" preface** — single-source enumeration of all canonical
   spellings, with explicit "do not write X" guidance.
2. **A matrix** — added canonical-spelling note rejecting `A_matrix` / `a_matrix`.
3. **B matrix**, **C matrix / C vector**, **D matrix / D vector** — same canonical-spelling
   notes; renamed C and D entries to lead with the matrix form.
4. **ACTION** — new role entry distinguishing canonical role label from Active-Inference
   theoretical noun.
5. **CONSTRAINT** — extended to clarify that the historical `cnst_` planner prefix is a
   stale internal artifact, not a canonical spelling.
6. **CONTEXT** — new role entry (was missing from glossary entirely).
7. **POLICY** — extended with canonical-capitalization clarification.
8. **OBSERVATION** — new role entry (the lowercase prose entry `Observation` was already
   present; the role-label entry was missing).
9. **ε** — new entry. Defines ε as the *fidelity score* of a roundtrip (count of ambiguous
   nodes), explicitly not "accuracy" or "similarity".
10. **ε-bounded adjunction** — new entry. Defines the ε-bounded categorical-strength claim
    relating COGANT's forward and reverse pipelines.
11. **Galois connection** — new entry. Order-theoretic definition tied to the COGANT
    forward / reverse pipelines.
12. **Fixpoint** — new entry establishing one-word canonical spelling (the existing
    `Fixpoint engine` entry assumed but did not state this).
13. **Forward pipeline** — new entry. Explicitly distinguishes operational use of
    "forward pipeline" from the formal categorical "forward pass" (the latter reserved
    for `ISOMORPHISM_THEOREM.md`).
14. **Reverse pipeline** — new entry, parallel structure to Forward pipeline. Replaces the
    old "Reverse mode" stub which now points to it.
15. **Reverse mode** — collapsed to a "see Reverse pipeline" pointer.
16. **`ReverseGNNModel`** — new entry. Defines the wrapper class produced by the reverse
    pipeline and rejects `reverse_gnn_model` / `Reverse GNN Model`.
17. **`PackagePlan`** — extended with canonical CamelCase note.
18. **Program graph** / **`ProgramGraph`** — extended to distinguish prose phrase from
    type-reference spelling.
19. **`GNNMatrices`** — updated body to use the canonical `A matrix`, `B matrix`, `C matrix`,
    `D matrix` forms (was previously "A / B / C / D matrices").
20. **GNN** — extended with explicit "GNN always means Generalized Notation Notation"
    statement and an explanatory note about why the JSON twins happen to be structurally
    usable as input to a downstream graph-neural-network trainer (a coincidence of
    representation, not a claim about COGANT's pipeline).
21. **ISOMORPHIC** / **APPROXIMATE** / **DIVERGENT** — three new tier entries with explicit
    ε-based criteria and ordering.
22. **Isomorphism** — body updated to use `forward pipeline` / `reverse pipeline`.

## Cross-doc normalizations applied

- `docs/reference/render_site.md` — line 180: stale "actual graph neural network logic"
  bullet replaced with "Map program graphs to Generalized Notation Notation
  (Active Inference Institute) state-space models. Note: GNN here means Generalized Notation
  Notation, not graph neural networks." (Concurrent edit by another agent had already begun
  this fix; the final text reflects the canonical disambiguation.)
- `docs/faq.md` — `epsilon-bounded` → `ε-bounded` in the isomorphism FAQ entry; the
  graph-neural-network training FAQ was clarified by a parallel agent to explicitly
  acknowledge the distinction.
- `docs/changelog.md` — `epsilon-bounded` → `ε-bounded` in the v0.2.0 release block.
- `docs/evaluation/RELEASE_NOTES_v0.2.0.md` — `epsilon-bounded` → `ε-bounded` in the
  Galois-connection paragraph.

## Cases intentionally **not** normalized

The following matches were considered and deliberately left in place:

1. **`docs/evaluation/LITERATURE.md` line 305** — describes Tarlow et al. 2020, an external
   paper that genuinely uses graph neural networks for bug-fixing. This is a legitimate
   citation of GNN-the-ML-method, not a COGANT-pipeline claim.
2. **`docs/evaluation/ISOMORPHISM_THEOREM.md` and `docs/theory/isomorphism.md`** — these
   documents use "forward pass" and "reverse pass" as the *category-theoretic* names for
   the functors F : 𝒫 → 𝒢 and R : 𝒢 → 𝒫. The canonical-conventions preface explicitly
   reserves this usage for these documents.
3. **`cnst_*` references in `CONSTRAINT_FIX.md`, `FINAL_REPORT.md`,
   `ROUNDTRIP_IMPROVEMENT.md`, and `changelog.md`** — these document a historical
   reverse-pipeline planner string-prefix bug. The canonical rule "(not `cnst_`)" applies
   to *role labels*, not to bug-history strings; the relevant CONSTRAINT glossary entry now
   says so.
4. **"Markov Blanket" / "Galois Connection" capitalizations in section headings** —
   acceptable typography under the canonical convention (capitalized only in headings).
   Plurals in citation entries (e.g. "The Markov Blankets of Life") are also paper titles
   and were preserved verbatim.
5. **`A_matrix` in `docs/evaluation/ROUNDTRIP_VALIDATION.md` line 92–93** — this is a
   Python `dict` key inside a code block, not a prose mention. Canonical role-label rules
   apply to prose, not to literal data keys whose form is fixed by the on-disk JSON
   schema.
6. **`build_package_plan` in `docs/tutorials/06_reverse_mode.md`** — this is the actual
   Python function name, not a type reference; snake_case is correct here.

## Files searched (partial)

```
grep -r "graph neural\|Graph Neural\|graph_neural" docs/ --include="*.md" -l   →  11 files
grep -r "hidden state\|HiddenState\|hidden_state" docs/ --include="*.md" -l    →  38 files
grep -r "epsilon-bounded\|ε bounded\|ε-Bounded" docs/ --include="*.md" -l       →   4 files
grep -r "fix-point\|fixed point" docs/ --include="*.md" -l                       →   0 files
grep -r "forward pass\|reverse pass" docs/ --include="*.md" -l                  →   8 files (left in place; categorical contexts)
grep -r "markov blanket\|Markov Blanket" docs/ --include="*.md" -l              →   4 files (headings / citations only)
grep -r "galois connection\|Galois Connection" docs/ --include="*.md" -l        →   3 files (headings only)
grep -r "cnst_" docs/ --include="*.md" -l                                       →   4 files (bug-history references; left in place)
grep -r "A_matrix\|a_matrix\|B_matrix\|b_matrix" docs/ --include="*.md" -l      →   1 file  (JSON key in code block; left in place)
grep -r "package_plan\|reverse_gnn_model\|Package Plan\|Reverse GNN Model" docs/ --include="*.md"  →  function-name occurrences only (left in place)
```

## Constraints honoured

- **No `manuscript/` edits.** The `cogant/manuscript/` directory does not exist in this
  worktree, so the constraint is vacuously satisfied. `git status manuscript/` returned
  "No such file or directory" before any edits were made.
- **One commit before exit** with the prescribed commit message under
  `docs(w19/coherence): terminology normalization`.

## Result

The glossary preface gives every future contributor (and every future review agent) a
single, scannable list of canonical spellings. Every term in the canonical-form list now
has at least one glossary entry that explicitly rejects its variant spellings. The
`epsilon-bounded` → `ε-bounded` normalization eliminates the only ASCII-only variant of the
ε notation in the docs tree. The render_site.md fix removes the only remaining COGANT-pipeline
claim that COGANT does "graph neural network logic". External-paper citations and
category-theoretic uses of "forward pass" / "reverse pass" are left intact and explicitly
documented as exceptions in the audit.
