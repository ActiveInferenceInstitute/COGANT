# COGANT Related Work

This file provides extended related-work commentary that supplements `../manuscript/08_scope_and_related_work.md`. Each section connects a body of literature to a specific COGANT design decision or theoretical claim.

---

## Bidirectional Transformations and the Lens View of COGANT

The bidirectional transformation literature [@foster2007lenses; @hofmann2011edit; @diskin2011symmetric] offers the cleanest mathematical characterization of what COGANT does at the architectural level. A *lens* in the sense of Foster et al. (2007) is a pair of functions `get : S → A` and `put : A → S → S` satisfying two round-trip laws: `get(put(a, s)) = a` (PutGet) and `put(get(s), s) = s` (GetPut). COGANT's `extract` and `reverse` modules are precisely such a pair, with S = a source repository (its AST-level program graph) and A = the emitted GNN specification bundle. The PutGet law says that extracting a GNN from a synthesized skeleton recovers the original specification; the GetPut law says that synthesizing a skeleton from an extracted GNN and then re-extracting produces the same GNN. Neither law holds perfectly in COGANT v0.1.x — the confidence model introduces lossy abstraction — but the lens framing makes the deviation measurable: the confidence tier of each assertion is a quantitative record of how far the extraction falls short of an exact `get`.

The *edit lens* extension [@hofmann2011edit] generalizes the basic framework to handle incremental edits: instead of replacing the entire concrete value, a delta `∂s` is propagated to a delta `∂a` on the abstract side and vice versa. This is directly relevant to COGANT's incremental update mode (planned for v0.2.x), where only AST diffs need to flow through the translation pipeline rather than a full re-extraction. Edit lenses provide the algebraic laws that an incremental COGANT implementation must satisfy.

The *symmetric lens* variant [@diskin2011symmetric] drops the asymmetry between source and target, allowing modifications on either side to be synchronized. This is the right model for the collaborative workflow envisioned in COGANT's human-review loop: a practitioner may edit the GNN specification directly (modifying the abstract side), and COGANT must propagate those changes back to the code skeleton (the concrete side). Symmetric lenses have been studied in the context of model-driven engineering under the label "bidirectional model transformations" (BX), and the ICMT conference series is the primary venue for this work; COGANT's reverse module should be evaluated against the BX benchmarks when the collaborative editing feature is implemented.

Positioning `cogant.reverse` in this literature also clarifies what it is *not*: it is not a general-purpose program synthesizer in the SyGuS [@alur2013sygus] or FlashFill [@gulwani2011flashfill] sense, because it does not search an arbitrary program space. Instead, it inverts a known, rule-based `get` function — a strictly simpler problem that is guaranteed to have a solution whenever the GNN specification was itself produced by `cogant.extract`. The synthesis problem only becomes hard when the GNN specification has been hand-edited or partially authored, a case that falls squarely in the symmetric-lens regime described above.

The categorical account of lenses via polynomial functors [@spivak2020poly; @niu2023polynomial] unifies both the asymmetric and symmetric cases. In the category **Poly** of polynomial endofunctors on **Set**, a lens from `p` to `q` is a natural transformation `p → q` in the coKleisli category of the comonad `p ⊗ -`. COGANT's functor pair lives in this category: `cogant.extract` is a morphism `Code_poly → GNN_poly` and `cogant.reverse` is a morphism `GNN_poly → Code_poly`, and their composition in the appropriate monoidal structure is the round-trip map whose deviation from identity is measured by the confidence model. This categorical framing is currently informal; formalizing it would constitute the theoretical contribution of a follow-on paper, tentatively scoped in `R&D_LOG.md` under the heading "COGANT-Theory."

### References

- Foster, J. N., Greenwald, M. B., Moore, J. T., Pierce, B. C., & Schmitt, A. (2007). Combinators for bidirectional tree transformations: A linguistic approach to the view-update problem. *ACM TOPLAS*, 29(3). DOI: 10.1145/1232420.1232424
- Hofmann, M., Pierce, B. C., & Wagner, D. (2011). Edit lenses. *POPL 2011*, pp. 495–508. DOI: 10.1145/1926385.1926392
- Diskin, Z. et al. (2011). From state- to delta-based bidirectional model transformations: The symmetric case. *ICMT 2011*, LNCS 6707. DOI: 10.1007/978-3-642-21732-6_5
- Spivak, D. I. (2020). Poly: An abundant categorical setting for mode-dependent dynamics. arXiv:2005.01894
- Niu, N., & Spivak, D. I. (2023). Polynomial functors: A mathematical theory of interaction. arXiv:2312.00990
