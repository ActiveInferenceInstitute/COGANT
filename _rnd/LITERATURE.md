# COGANT Literature Review

This file documents key papers across all research areas relevant to COGANT's design and theoretical foundations. Sections 1–9 cover the core areas; sections 10–13 were added in the extended search pass.

---

## 10. Bidirectional Transformations and Lenses

**Search terms used:** "bidirectional transformations lenses Foster 2007 Boomerang", "symmetric lenses category theory bidirectional programming", "bx bidirectional model transformation"

**Relevance to COGANT:** COGANT's forward+reverse functor pair constitutes a lens in the sense of Foster et al.: the source code is the "concrete" structure, the GNN specification is the "abstract" view, and `cogant.extract` / `cogant.reverse` are the `get` and `put` functions. Positioning COGANT in this literature grounds the round-trip guarantee in a well-studied algebraic framework.

### Key Papers

**Foster, J. N., Greenwald, M. B., Moore, J. T., Pierce, B. C., & Schmitt, A. (2007).** Combinators for Bidirectional Tree Transformations: A Linguistic Approach to the View-Update Problem. *ACM Transactions on Programming Languages and Systems (TOPLAS)*, 29(3), Article 17.
- DOI: 10.1145/1232420.1232424
- The foundational paper defining the lens framework: a lens is a pair of functions `get : S → A` and `put : A → S → S` satisfying round-trip laws. The Boomerang language instantiates this for tree-structured data. COGANT's functor pair satisfies the same laws with S = source AST graph and A = GNN specification bundle.

**Hofmann, M., Pierce, B. C., & Wagner, D. (2011).** Edit Lenses. *Proceedings of the 38th Annual ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL 2011)*, pp. 495–508.
- DOI: 10.1145/1926385.1926392
- Extends the basic lens framework to handle insertions and deletions (edit actions) rather than just value replacement. Relevant to COGANT's incremental update mode, where only changed AST nodes need to propagate through the translation pipeline.

**Diskin, Z., Xiong, Y., Czarnecki, K., Ehrig, H., Hermann, F., & Orejas, F. (2011).** From State- to Delta-Based Bidirectional Model Transformations: The Symmetric Case. *Proceedings of the 4th International Conference on Model Transformation (ICMT 2011)*, Lecture Notes in Computer Science, Vol. 6707, pp. 61–76.
- DOI: 10.1007/978-3-642-21732-6_5
- Generalizes lenses to the symmetric case where both the source and target can be modified and changes must be synchronized. Directly applicable to COGANT scenarios where both code and GNN specification evolve and must be kept consistent.

---

## 11. Round-Trip Synthesis / Bidirectional Program Transformation

**Search terms used:** "round-trip program transformation synthesis", "program synthesis from specifications executable", "bidirectional program transformation verified"

**Relevance to COGANT:** `cogant.reverse` is a program synthesizer: given a GNN specification (the abstract view), it must produce a Python skeleton (the concrete program) that satisfies it. This places COGANT's reverse module in the program synthesis literature, specifically in the inductive/deductive synthesis tradition where correctness is defined relative to a formal specification.

### Key Papers

**Alur, R., Bodík, R., Juniwal, G., Martin, M. M. K., Raghothaman, M., Seshia, S. A., Singh, R., Solar-Lezama, A., Torlak, E., & Udupa, A. (2013).** Syntax-Guided Synthesis. *Proceedings of the IEEE International Conference on Formal Methods in Computer-Aided Design (FMCAD 2013)*.
- Available: https://sygus.org/assets/pdf/Journal_SyGuS.pdf
- Defines the SyGuS framework: synthesis from a formal specification and a grammar constraining the output program. COGANT's reverse step is a specialization where the grammar is Python's AST and the specification is the GNN bundle's state-space and transition constraints.

**Solar-Lezama, A. (2008).** Program Synthesis by Sketching. *PhD Dissertation, University of California, Berkeley.*
- The "sketching" paradigm: a partial program with holes is completed by a synthesizer. COGANT's reverse module generates a skeleton (a sketch) rather than a fully complete program; holes correspond to behaviors the GNN specification leaves underspecified.

**Gulwani, S. (2011).** Automating String Processing in Spreadsheets Using Input-Output Examples. *Proceedings of the 38th Annual ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL 2011)*, pp. 317–330.
- DOI: 10.1145/1926385.1926358
- The FlashFill system: program synthesis from input-output examples. Provides the template for data-driven synthesis that `cogant.reverse` could adopt if example code fragments are available to guide skeleton generation.

---

## 12. World Models from Code / Program Semantics as Generative Models

**Search terms used:** "world model neural network code program semantics", "program semantics as generative model probability", "operational semantics stochastic"

**Relevance to COGANT:** The central theoretical claim of COGANT is that source code implicitly defines a generative model of the system's behavior — a claim that needs empirical and theoretical backing. This section grounds that claim in existing work on probabilistic operational semantics and world models.

### Key Papers

**Hafner, D., Pasukonis, J., Ba, J., & Lillicrap, T. (2023).** Mastering Diverse Domains through World Models. *arXiv preprint arXiv:2301.04104.*
- arXiv: https://arxiv.org/abs/2301.04104
- DreamerV3: a general reinforcement learning algorithm that learns a latent world model from observations and uses it to plan. The architecture (encoder → latent dynamics model → decoder) is structurally analogous to COGANT's pipeline (AST parser → program graph IR → GNN specification). The world model here is learned; in COGANT it is extracted symbolically. The comparison is productive: COGANT produces an explicit, interpretable world model rather than a learned latent one.

**Kaddar, Y., & Staton, S. (2023).** Stochastic Memoization in Probabilistic Programming. *arXiv preprint arXiv:2309.09467.*
- arXiv: https://arxiv.org/abs/2309.09467
- Develops categorical semantics for probabilistic programs via monads on presheaf categories. Relevant to COGANT's theoretical framing: if program execution is modeled as a stochastic process, the semantics of a program is a probability distribution over traces, which is precisely the kind of generative model that active inference agents consume.

**Mak, C., Ong, C.-H. L., Paquet, H., & Wagner, D. (2020).** Densities of Almost-Surely Terminating Probabilistic Programs are Differentiable. *arXiv preprint arXiv:2004.03924.*
- arXiv: https://arxiv.org/abs/2004.03924
- Proves that higher-order probabilistic programs with sampling-style operational semantics have almost-everywhere differentiable density functions. Provides theoretical scaffolding for treating COGANT's extracted state-space as a differentiable generative model amenable to variational inference — a direction identified as future work in COGANT's confidence model.

---

## 13. Polynomial Functors and Wiring Diagrams

**Search terms used:** "polynomial functors Spivak categorical systems theory", "wiring diagrams monoidal categories composition", "David Spivak polynomial dynamics systems"

**Relevance to COGANT:** Spivak's polynomial functor framework provides the strongest categorical foundation for COGANT's functor pair. A polynomial functor `p = Σ_{i∈p(1)} y^{p[i]}` captures a system with positions (states) and directions (transitions), and the composition of two polynomial functors corresponds exactly to composing COGANT's `extract` and `reverse` functors. This gives COGANT's architecture a precise categorical semantics.

### Key Papers

**Spivak, D. I. (2020).** Poly: An Abundant Categorical Setting for Mode-Dependent Dynamics. *arXiv preprint arXiv:2005.01894.*
- arXiv: https://arxiv.org/abs/2005.01894
- DOI: https://doi.org/10.48550/arXiv.2005.01894
- Introduces the category **Poly** of polynomial endofunctors on **Set** as a natural home for dynamical systems with time-varying inputs. The four interacting monoidal structures on Poly give COGANT's functor pair four distinct compositional interpretations (sequential, parallel, dependent, Cartesian). Coalgebras in Poly are identified with deterministic automata, matching COGANT's finite-state-machine view of program behavior.

**Niu, N., & Spivak, D. I. (2023).** Polynomial Functors: A Mathematical Theory of Interaction. *arXiv preprint arXiv:2312.00990.*
- arXiv: https://arxiv.org/abs/2312.00990
- A 372-page monograph treating polynomial endofunctors on **Set** as a unified framework for interaction, dynamical systems, and database schemas. Chapter 4 on wiring diagrams is directly applicable to COGANT: the wiring diagram for `cogant.extract ∘ cogant.reverse` is precisely the round-trip composition whose correctness properties mirror the lens laws of Section 10.

**Spivak, D. I. (2022).** A Reference for Categorical Structures on Poly. *arXiv preprint arXiv:2202.00534.*
- arXiv: https://arxiv.org/abs/2202.00534
- A reference compendium of adjunctions, coclosures, and monoidal structures on **Poly**. Useful for formally specifying the type of COGANT's functor pair: `cogant.extract : Code → GNN` and `cogant.reverse : GNN → Code` form a section-retraction pair in a suitable monoidal closed structure on Poly, which is the categorical statement of the round-trip guarantee.
