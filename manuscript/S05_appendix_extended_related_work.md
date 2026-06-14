# Appendix E — Extended Related Work {#sec:S05-appendix-extended-related-work}

This appendix consolidates the related-work references cited in the main
text (@sec:08-scope-and-related-work through @sec:08-04-world-models-boundaries-and-compatibility) and the annotated bibliography in `../cogant/docs/evaluation/LITERATURE.md`
(which contains {{BIB_ENTRIES}} entries organized into a broader bibliography outline). The list below is organized
into topical clusters spanning program analysis, active-inference tooling, learned code models,
graph kernels, abstract interpretation, POMDP planning, synthesis, bidirectional transformations,
Markov blankets, evidence provenance, reproducibility, visual analytics, organizational state-space models, differentiable programming, and world-model proof certificates. References are numbered consecutively across clusters;
in-text citations in other appendices use `[N]` format. Consult
`../cogant/docs/evaluation/LITERATURE.md` for
the full annotated pool; this appendix lists the curated subset most directly relevant
to COGANT's design and evaluation.

### E.1 Program analysis → GNN (learned and symbolic)

[1] Allamanis, M., Brockschmidt, M., Khademi, M. (2018). **Learning to
Represent Programs with Graphs.** *Proceedings of the International
Conference on Learning Representations (ICLR).* The canonical multi-edge
typed program graph reference; COGANT's {{NODE_KIND_COUNT}} node kinds and {{EDGE_KIND_COUNT}} edge kinds
extend this taxonomy with ActInf roles.

[2] Cummins, C., Fisches, Z. V., Ben-Nun, T., Hoefler, T., O'Boyle, M. F.,
Leather, H. (2021). **ProGraML: A Graph-based Program Representation for
Data Flow Analysis and Compiler Optimizations.** *ICML.* LLVM-IR level
unified AST/data-flow/control-flow program graph; design reference for
COGANT's unified edge labeling.

[3] Yamaguchi, F., Golde, N., Arp, D., Rieck, K. (2014). **Modeling and
Discovering Vulnerabilities with Code Property Graphs.** *IEEE Symposium on
Security and Privacy.* Introduces the CPG (merged AST/CFG/PDG);
COGANT's graph is conceptually a CPG restricted to ActInf-relevant edges.

[4] Dinella, E., Dai, H., Li, Z., Naik, M., Song, L., Wang, K. (2020).
**Hoppity: Learning Graph Transformations to Detect and Fix Bugs in
Programs.** *ICLR.* Learned graph-to-graph transformations on program
graphs; structurally analogous to COGANT's rule-based transformation stage.

[5] Li, Y., Tarlow, D., Brockschmidt, M., Zemel, R. (2016). **Gated Graph
Sequence Neural Networks.** *ICLR.* The foundational GGNN architecture used
by most learned program-graph models; cited for completeness of the
"learned GNNs over program graphs" lineage.

[6] Ben-Nun, T., Jakobovits, A. S., Hoefler, T. (2018). **Neural Code
Comprehension: A Learnable Representation of Code Semantics.** *NeurIPS.*
inst2vec: LLVM-IR embeddings for code representation; the learned
counterpart to COGANT's symbolic statespace module.

[7] Mir, A. M., Latoškinas, E., Proksch, S., Gousios, G. (2022). **Type4Py:
Practical Deep Similarity Learning-Based Type Inference for Python.** *ICSE.*
Learned type inference over Python program graphs; the closest "learned
role assignment" analogue to COGANT's declarative translate rules.

[8] Kanade, A., Maniatis, P., Balakrishnan, G., Shi, K. (2020). **Learning
and Evaluating Contextual Embedding of Source Code.** *ICML.* CuBERT: BERT
pretraining on Python source; baseline for position-aware token
representations that could serve as features for a hybrid COGANT variant.

### E.2 Active inference tooling and implementations

[9] Heins, C., Millidge, B., Demekas, D., Klein, B., Friston, K., Fields, C.,
Buckley, C., Tschantz, A. (2022). **pymdp: A Python library for active
inference in discrete state spaces.** *Journal of Open Source Software,
7(73).* The reference Python implementation of discrete active inference;
COGANT's `cogant.process` module targets pymdp's matrix conventions.

[10] Smith, R., Friston, K. J., Whyte, C. J. (2022). **A Step-by-Step
Tutorial on Active Inference and Its Application to Empirical Data.**
*Journal of Mathematical Psychology, 107.* The practitioner tutorial
against which COGANT's `cogant.process` test fixtures are checked.

[11] Parr, T., Pezzulo, G., Friston, K. J. (2022). **Active Inference: The
Free Energy Principle in Mind, Brain, and Behavior.** MIT Press. The
current textbook reference for discrete-time active inference and the A/B/C/D
matrix formalism that COGANT targets.

[12] Da Costa, L., Parr, T., Sajid, N., Veselic, S., Neacsu, V., Friston, K.
(2020). **Active Inference on Discrete State-Spaces: A Synthesis.**
*Journal of Mathematical Psychology, 99.* Explicit algorithms for policy
evaluation via Expected Free Energy; COGANT's EFE implementation follows
the pseudocode in this paper.

[13] Sajid, N., Ball, P. J., Parr, T., Friston, K. J. (2021). **Active
Inference: Demystified and Compared.** *Neural Computation, 33(3).* Compares
active inference to RL and optimal control; used to position COGANT's
choice of the A/B/C/D representation against reward-function alternatives.

[14] Friston, K. J., Lin, M., Frith, C. D., Pezzulo, G., Hobson, J. A.,
Ondobaka, S. (2017). **Active Inference, Curiosity and Insight.** *Neural
Computation, 29(10).* Decomposes EFE into pragmatic and epistemic
components; COGANT's EFE includes the epistemic term.

[15] Active Inference Institute (2022–2026). **infer-actively / pymdp
reference implementation and example gallery.** GitHub:
`infer-actively/pymdp`. The living library of example GNN specifications
against which COGANT's output is diffed in the reference-corpus
integration tests.

[16] Friston, K. J., Mattout, J., Trujillo-Barreto, N., Ashburner, J.,
Penny, W. (2007). **Variational Free Energy and the Laplace Approximation.**
*NeuroImage, 34(1).* SPM12 active-inference variational Bayesian framework;
a predecessor to pymdp and the source of the Laplace
approximation used in continuous-state extensions of COGANT.

[17] Smekal, J., Friedman, D. A. et al. (2023). **Generalized Notation
Notation: A Text-Based Format for Active Inference Generative Models.**
Active Inference Institute technical report. The maintained syntax reference
now distinguishes the syntax engine from the release bundle, and COGANT's
`cogant.gnn` formatter targets that current upstream bundle.

[18] Champion, T., Grzes, M., Bowman, H. (2022). **Branching Time Active
Inference: Empirical Study and Complexity Class Analysis.** *Neural
Networks, 152.* Demonstrates GNN-style specifications for hierarchical
active inference; target formalism for COGANT's branching-time extension.

### E.3 Code understanding and learned code models

[19] Feng, Z., Guo, D., Tang, D., Duan, N. et al. (2020). **CodeBERT: A
Pre-Trained Model for Programming and Natural Languages.** *Findings of
EMNLP.* Bimodal pretraining for code + NL; baseline for semantic
similarity tasks over code.

[20] Guo, D., Ren, S., Lu, S., Feng, Z. et al. (2021). **GraphCodeBERT:
Pre-training Code Representations with Data Flow.** *ICLR.* BERT-style model
with data-flow attention masks; the closest learned analogue to COGANT's
graph-structured role assignment.

[21] Guo, D., Lu, S., Duan, N., Wang, Y., Yin, M., Ren, S. (2022).
**UniXcoder: Unified Cross-Modal Pre-training for Code Representation.**
*ACL.* Unified encoder-decoder over AST, code, and comments.

[22] Wang, Y., Wang, W., Joty, S., Hoi, S. C. H. (2021). **CodeT5:
Identifier-Aware Unified Pre-trained Encoder-Decoder Model for Code
Understanding and Generation.** *EMNLP.* Identifier-aware T5 for code;
node-kind classification parallels COGANT's {{NODE_KIND_COUNT}} node kinds.

[23] Alon, U., Zilberstein, M., Levy, O., Yahav, E. (2019). **code2vec:
Learning Distributed Representations of Code.** *POPL.* AST-path aggregation
for code embedding; complementary to COGANT's whole-graph approach.

[24] Hellendoorn, V. J., Sutton, C., Singh, R., Maniatis, P., Bieber, D.
(2019). **Global Relational Models of Source Code.** *ICLR.* Relational
graph attention over program graphs; validates COGANT's premise that
graph structure carries essential semantic information.

[25] Allamanis, M., Barr, E. T., Devanbu, P., Sutton, C. (2018). **A Survey
of Machine Learning for Big Code and Naturalness.** *ACM Computing Surveys,
51(4).* Landscape of learned code models against which COGANT is
positioned as a graph-based symbolic extractor.

[26] Bielik, P., Raychev, V., Vechev, M. (2016). **PHOG: Probabilistic Model
for Code.** *ICML.* Tree-conditional grammar for context-sensitive role
prediction; symbolic analogue of COGANT's rule engine with learned grammars.

[27] Raychev, V., Vechev, M., Krause, A. (2015). **Predicting Program
Properties from "Big Code".** *POPL.* CRF over program graphs for learned
role assignment; the learned counterpart to COGANT's rule engine.

### E.4 Graph kernels and structural similarity for code

[28] Shervashidze, N., Schweitzer, P., van Leeuwen, E. J., Mehlhorn, K.,
Borgwardt, K. M. (2011). **Weisfeiler-Lehman Graph Kernels.** *Journal of
Machine Learning Research, 12.* The foundational graph kernel that COGANT's
role-multiset similarity metric is a weighted analogue of (the WL-subtree
kernel reduces to multiset comparison at depth 1).

[29] Kriege, N. M., Johansson, F. D., Morris, C. (2020). **A Survey on
Graph Kernels.** *Applied Network Science, 5(1).* Comprehensive survey of
graph kernels; locates COGANT's role-match score in the kernel lineage.

[30] Nikolentzos, G., Siglidis, G., Vazirgiannis, M. (2021). **Graph Kernels:
A Survey.** *Journal of Artificial Intelligence Research, 72.* Alternative
survey with emphasis on structural kernels over labeled graphs.

### E.5 Formal methods: abstract interpretation and Galois connections in static analysis

[31] Cousot, P., Cousot, R. (1977). **Abstract Interpretation: A Unified
Lattice Model for Static Analysis of Programs by Construction or
Approximation of Fixpoints.** *POPL.* The foundational framework; COGANT's
confidence tiers and the forward/reverse functor pair are both instances.

[32] Cousot, P., Cousot, R. (1992). **Abstract Interpretation Frameworks.**
*Journal of Logic and Computation, 2(4).* Generalizes the 1977 framework
with explicit Galois connections between concrete and abstract domains.

[33] Nielson, F., Nielson, H. R., Hankin, C. (2005, 2nd printing).
**Principles of Program Analysis.** Springer. The standard textbook;
COGANT's translate stage is a worklist fixpoint in the monotone framework.

[34] Bravenboer, M., Smaragdakis, Y. (2009). **Strictly Declarative
Specification of Sophisticated Points-to Analyses.** *OOPSLA.* Doop and
Datalog-based static analysis; validates the principle that declarative
rule systems can handle sophisticated whole-program analyses at scale.

[35] Rice, H. G. (1953). **Classes of Recursively Enumerable Sets and
Their Decision Problems.** *Transactions of the AMS, 74(2).* Rice's
theorem establishes the fundamental undecidability that motivates the
approximate (Galois-connection) approach to semantic role assignment.

[36] Jones, N. D., Nielson, F. (1995). **Abstract Interpretation: A
Semantics-Based Tool for Program Analysis.** In *Handbook of Logic in
Computer Science.* Comprehensive reference for Galois-connection-based
static analysis; the categorical machinery used in @sec:S03-appendix-galois-sketch.

[37] Hoare, C. A. R. (1969). **An Axiomatic Basis for Computer Programming.**
*Communications of the ACM, 12(10).* The foundational paper for program
logic; COGANT's translate rules can be read as Hoare-style inference rules.

[38] Reynolds, J. C. (2002). **Separation Logic: A Logic for Shared Mutable
Data Structures.** *LICS.* Separation logic frame rule; analogue of
COGANT's Markov blanket extraction over program graphs.

[39] Milner, R. (1978). **A Theory of Type Polymorphism in Programming.**
*Journal of Computer and System Sciences, 17(3).* Hindley-Milner type
inference; COGANT's role assignment computes a "principal role" analogous
to a principal type.

[40] Leroy, X. (2009). **Formal Verification of a Realistic Compiler.**
*Communications of the ACM, 52(7).* CompCert: the gold standard for
verified program transformation; COGANT's roundtrip property is a weaker
but analogous correctness statement.

### E.6 POMDP solvers and planning

[41] Kaelbling, L. P., Littman, M. L., Cassandra, A. R. (1998). **Planning
and Acting in Partially Observable Stochastic Domains.** *Artificial
Intelligence, 101(1-2).* The foundational POMDP reference; establishes the
belief-state MDP reformulation that active inference specializes.

[42] Silver, D., Veness, J. (2010). **Monte-Carlo Planning in Large POMDPs.**
*NeurIPS.* POMCP: Monte Carlo tree search for large POMDPs. Alternative
planner to active inference's EFE-based policy selection; cited as a
scalable baseline for large extracted state spaces.

[43] Ye, N., Somani, A., Hsu, D., Lee, W. S. (2017). **DESPOT: Online
POMDP Planning with Regularization.** *Journal of AI Research, 58.*
Determinized Sparse Partially Observable Tree; anytime online POMDP
planner whose specification format could be generated from COGANT's
extracted A/B/C/D matrices as an alternative runtime.

[44] Kurniawati, H., Hsu, D., Lee, W. S. (2008). **SARSOP: Efficient
Point-Based POMDP Planning by Approximating Optimally Reachable Belief
Spaces.** *Robotics: Science and Systems.* Point-based value iteration;
the anytime offline counterpart to DESPOT. Relevant to COGANT extensions
that compute exact EFE-optimal policies rather than argmin-tie-break.

[45] Astrom, K. J. (1965). **Optimal Control of Markov Decision Processes
with Incomplete State Information.** *Journal of Mathematical Analysis
and Applications, 10(1).* A source for the belief-state MDP
reformulation used throughout the POMDP literature.

[46] Hansen, E. A. (1998). **Solving POMDPs by Searching in Policy Space.**
*UAI.* Finite-state controllers for POMDPs; an alternative representation
of π that could be extracted by COGANT from repository control flow.

### E.7 Program synthesis and reverse engineering

[47] Alur, R., Bodik, R., Juniwal, G., Martin, M. M. K., Raghothaman, M.,
Seshia, S. A., Singh, R., Solar-Lezama, A., Torlak, E., Udupa, A. (2013).
**Syntax-Guided Synthesis.** *FMCAD.* SyGuS framework; COGANT's reverse
is a specialization with Python AST as grammar and GNN as specification.

[48] Solar-Lezama, A. (2008). **Program Synthesis by Sketching.** PhD
thesis, UC Berkeley. The sketching paradigm; COGANT's reverse output is a
sketch whose holes correspond to behaviors underspecified by the GNN.

[49] Gulwani, S. (2011). **Automating String Processing in Spreadsheets
Using Input-Output Examples.** *POPL.* FlashFill; popularized program
synthesis from input-output examples. Relevant to future COGANT work
using extract(code)→GNN pairs as synthesis training data.

[50] Jha, S., Gulwani, S., Seshia, S. A., Tiwari, A. (2010). **Oracle-Guided
Component-Based Program Synthesis.** *ICSE.* CEGIS loop; COGANT's forward
extraction is a natural correctness oracle for the reverse synthesis.

[51] Polozov, O., Gulwani, S. (2015). **FlashMeta: A Framework for
Inductive Program Synthesis.** *OOPSLA.* Witness-function synthesis
framework; candidate refactor for COGANT's reverse module.

[52] Gulwani, S., Polozov, O., Singh, R. (2017). **Program Synthesis.**
*Foundations and Trends in Programming Languages, 4(1-2).* The definitive
survey; locates COGANT's reverse in the deductive-from-formal-spec corner.

### E.8 Bidirectional transformations, lenses, and the categorical frame

[53] Foster, J. N., Greenwald, M. B., Moore, J. T., Pierce, B. C., Schmitt,
A. (2007). **Combinators for Bidirectional Tree Transformations: A
Linguistic Approach to the View-Update Problem.** *ACM TOPLAS, 29(3).*
The foundational lens paper; COGANT's forward/reverse pair is a partial
lens in this sense.

[54] Hofmann, M., Pierce, B. C., Wagner, D. (2011). **Edit Lenses.**
*POPL.* Extends lenses with edit actions; relevant to COGANT's incremental
update mode.

[55] Diskin, Z., Xiong, Y., Czarnecki, K., Ehrig, H., Hermann, F.,
Orejas, F. (2011). **From State- to Delta-Based Bidirectional Model
Transformations: The Symmetric Case.** *ICMT.* Symmetric lens
generalization; candidate for COGANT's future bidirectional synchronization.

[56] Fong, B., Spivak, D. I. (2019). **Seven Sketches in Compositionality:
An Invitation to Applied Category Theory.** Cambridge University Press.
Accessible reference for Galois connections (Chapter 1) and
databases-as-functors (Chapter 3); the mathematical home for COGANT's
confidence tiers and graph-as-category reading.

[57] Spivak, D. I. (2020). **Poly: An Abundant Categorical Setting for
Mode-Dependent Dynamics.** arXiv:2005.01894. The category **Poly** of
polynomial endofunctors on **Set**; the deepest categorical setting for
COGANT's forward/reverse functor pair.

[58] Niu, N., Spivak, D. I. (2023). **Polynomial Functors: A Mathematical
Theory of Interaction.** arXiv:2312.00990. 372-page monograph; the
reference for COGANT-Theory follow-on work.

[59] Awodey, S. (2010). **Category Theory (2nd ed.).** Oxford University
Press. The standard graduate textbook; definitions of functor, adjunction,
and unit/counit used in @sec:S03-appendix-galois-sketch.

### E.9 Markov blankets and active inference foundations

[60] Friston, K. J. (2010). **The Free-Energy Principle: A Unified Brain
Theory?** *Nature Reviews Neuroscience, 11(2).* The canonical statement of
the Free Energy Principle; the theoretical substrate of GNN notation.

[61] Pearl, J. (1988). **Probabilistic Reasoning in Intelligent Systems:
Networks of Plausible Inference.** Morgan Kaufmann. The book that
introduced Markov blankets for Bayesian networks; COGANT's blanket
extraction is over the program graph in Pearl's sense.

[62] Kirchhoff, M., Parr, T., Palacios, E., Friston, K., Kiverstein, J.
(2018). **The Markov Blankets of Life: Autonomy, Active Inference and the
Free Energy Principle.** *Journal of the Royal Society Interface, 15(138).*
Lifts Markov blankets from graphical models to dynamical systems; the
conceptual warrant for COGANT's "software Markov blanket" claim.

[63] Bruineberg, J., Dolega, K., Dewhurst, J., Baltieri, M. (2022). **The
Emperor's New Markov Blankets.** *Behavioral and Brain Sciences.* Critical
examination of Markov blanket usage; informs COGANT's cautious framing
(Pearl blankets, not Friston blankets).

[64] Biehl, M., Pollock, F. A., Kanai, R. (2021). **A Technical Critique of
Some Parts of the Free Energy Principle.** *Entropy, 23(3).* Conditions
under which FEP's Markov blanket claims hold rigorously vs break down;
COGANT's discrete-graph setting sidesteps the continuous-dynamics concerns.

### E.10 Evidence provenance, reproducibility, and visual analytics

[65] Green, T. J., Karvounarakis, G., Tannen, V. (2007). **Provenance
Semirings.** *PODS.* Shows how annotations can propagate through relational
and Datalog-style fixed points; COGANT's rule-evidence trace is a practical
engineering analogue rather than a full semiring implementation.

[66] Moreau, L., Missier, P. (2013). **PROV-DM: The PROV Data Model.**
*W3C Recommendation.* Defines the entity/activity/derivation vocabulary that
best describes COGANT's artifact chain from source files through rules,
figures, claim ledger, and rendered manuscript.

[67] Peng, R. D. (2011). **Reproducible Research in Computational Science.**
*Science.* Establishes the requirement to publish enough computation and
data for results to be independently rerun; COGANT's `METRICS.yaml`,
figure registry, and claim ledger instantiate this requirement.

[68] Sandve, G. K., Nekrutenko, A., Taylor, J., Hovig, E. (2013). **Ten
Simple Rules for Reproducible Computational Research.** *PLOS Computational
Biology.* Motivates COGANT's checklist-oriented recording of inputs,
versions, commands, intermediate artifacts, and outputs.

[69] Wilkinson, M. D. et al. (2016). **The FAIR Guiding Principles for
scientific data management and stewardship.** *Scientific Data.* Provides
the machine-actionable metadata framing behind COGANT's manifests, JSON
sidecars, and script-readable figure/claim registries.

[70] Shneiderman, B. (1996). **The Eyes Have It: A Task by Data Type
Taxonomy for Information Visualizations.** *IEEE Symposium on Visual
Languages.* The source of the overview/zoom-filter/details-on-demand mantra;
COGANT's inspection dashboard follows this progression from graphical
abstract to rule-level and matrix-level detail.

[71] Munzner, T. (2009). **A Nested Model for Visualization Design and
Validation.** *IEEE Transactions on Visualization and Computer Graphics.*
Frames visualization quality as nested domain, abstraction, encoding, and
algorithm choices; COGANT uses this to treat wrong program abstractions as
visualization failures, not only rendering failures.

[72] Hohman, F., Kahng, M., Pienta, R., Chau, D. H. (2019). **Visual
Analytics in Deep Learning: An Interrogative Survey for the Next Frontiers.**
*IEEE Transactions on Visualization and Computer Graphics.* Motivates the
dashboard panels that let reviewers ask why mappings fired, where confidence
comes from, and when generated model artifacts fail.

The same cluster also motivates COGANT's audit-surface visualizations. A
validator-status SVG is treated as a compact claim ledger: it does not merely
decorate a report, but separates version currentness, bridge importability,
package-native validation, upstream executable compatibility, and supply-chain
state into distinct lanes. In Munzner's terms, this keeps the abstraction and
encoding choices honest; a red upstream-execution lane is a domain finding even
when the package-validator lane is green.

[73] Sugiyama, K., Tagawa, S., Toda, M. (1981). **Methods for Visual
Understanding of Hierarchical System Structures.** *IEEE Transactions on
Systems, Man, and Cybernetics.* Provides the layered graph-drawing precedent
behind COGANT's containment-first program-graph layout.

[74] Fruchterman, T. M. J., Reingold, E. M. (1991). **Graph Drawing by
Force-Directed Placement.** *Software: Practice and Experience.* Provides the
alternate force-directed logic for non-hierarchical program-graph fragments.

[75] Gansner, E. R., Koutsofios, E., North, S. C., Vo, K.-P. (1993). **A
Technique for Drawing Directed Graphs.** *IEEE Transactions on Software
Engineering.* Establishes the directed-graph drawing tradition behind
pipeline and program-relation visualizations.

[76] Heer, J., Shneiderman, B. (2012). **Interactive Dynamics for Visual
Analysis.** *Communications of the ACM.* Connects static manuscript figures
to the inspection dashboard's filter, inspect, and drill-down affordances.

[77] Lin, J. (1991). **Divergence Measures Based on the Shannon Entropy.**
*IEEE Transactions on Information Theory.* The reference for the
Jensen-Shannon distance used in @sec:S03-appendix-galois-sketch's distributional restatement of
role-preservation, separate from the shipped multiset score.

[78] Brehmer, M., Munzner, T. (2013). **A Multi-Level Typology of Abstract
Visualization Tasks.** *IEEE Transactions on Visualization and Computer
Graphics.* Supplies the why/how/what task vocabulary now used to separate
COGANT's lookup, compare, summarize, review, and explanation views.

[79] Sedlmair, M., Meyer, M., Munzner, T. (2012). **Design Study
Methodology: Reflections from the Trenches and the Stacks.** *IEEE
Transactions on Visualization and Computer Graphics.* Frames the next
validation step for COGANT's dashboard: a user-facing design study rather
than only manifest and rendering QA.

[80] Storey, M.-A. D. (2005). **Theories, Methods and Tools in Program
Comprehension: Past, Present and Future.** *International Workshop on
Program Comprehension.* Connects COGANT's visualization workbench to the
software-comprehension literature on navigation, orientation, and task
support.

### E.11 Organizational state spaces and differentiable surrogates

[81] World Wide Web Consortium Government Linked Data Working Group (2014).
**The Organization Ontology.** *W3C Recommendation.* Defines core linked-data
terms for organizations, sub-organizations, memberships, roles, posts, sites,
and change events; for COGANT this is the closest standards anchor for reading
an org chart as a typed graph rather than as behavior.

[82] Object Management Group (2014). **Business Process Model and Notation
(BPMN), Version 2.0.2.** *OMG formal specification.* Provides a stakeholder-readable
business-process notation with machine-readable specification artifacts; COGANT's
future organization-state-space track would treat BPMN tasks, events, gateways,
and handoffs as typed process evidence, not as measured execution.

[83] Galbraith, J. R. (1974). **Organization Design: An Information Processing
View.** *Interfaces, 4(3).* Frames organization design around task uncertainty
and information-processing demands; this is the management-theory analogue of
COGANT's claim that structure matters because it constrains information flow.

[84] Carley, K. M. (1995). **Computational and Mathematical Organization
Theory: Perspective and Directions.** *Computational and Mathematical
Organization Theory, 1.* Treats organizations as collections of processes and
adaptive agents studied through formal computational and mathematical models;
this is the closest organization-science home for a COGANT-style typed
coordination model.

[85] Levinthal, D. A. (1997). **Adaptation on Rugged Landscapes.**
*Management Science, 43(7).* Models organizational form as search over
interdependent design choices; useful for bounding any optimization story
around "differentiable typed corporations" to surrogate search rather than
guaranteed organizational improvement.

[86] Zou, N., Li, J. (2017). **Modeling and Change Detection of Dynamic Network
Data by a Network State Space Model.** *IISE Transactions, 49(1).* Proposes a
network state-space model where dynamic network observations are linked to
latent node propensities and used for change detection. This is the direct
methodological bridge from static org-chart edges to dynamic organizational
state inference.

[87] Baydin, A. G., Pearlmutter, B. A., Radul, A. A., Siskind, J. M. (2018).
**Automatic Differentiation in Machine Learning: A Survey.** *Journal of
Machine Learning Research, 18.* Clarifies automatic differentiation and
differentiable programming for machine-learning systems; it bounds COGANT's
future differentiable-organization language to explicit differentiable
surrogates.

[88] Mak, C., Ong, C.-H. L., Paquet, H., Wagner, D. (2021). **Densities of
Almost Surely Terminating Probabilistic Programs are Differentiable Almost
Everywhere.** *European Symposium on Programming.* Establishes a formal route
from probabilistic programs to almost-everywhere differentiable densities under
specific conditions; relevant as a boundary condition for differentiating
compiled generative-model surrogates.

[89] Smithe, T. St C. (2024). **Structured Active Inference.** *arXiv.*
Generalizes active inference using categorical systems theory, structured
interfaces, typed policies, and agents managing other agents. It supplies the
active-inference-specific bridge from typed program or organization interfaces
to compositional multi-agent GNN bundles.

[90] Westenhaver, Y., Branscomb, M., Grant, A. (2026). **Recursive
Self-Improvement is a Portfolio Optimization Problem.** *AlphaFund white
paper.* An industry white paper that frames recursive self-improvement as a
capital-allocation process over Economic World Models, channel histories, and
portfolio optimization. COGANT uses it only as conceptual adjacent work for
economic-world-model and typed-corporation framing, not as peer-reviewed
evidence and not as support for current COGANT implementation claims.

The provisional validator in `../tools/organization_state_space_audit.py`
turns this cluster into a falsifiable design-review surface: static
organization artifacts, dynamic traces, factor evidence, transition evidence,
and negative controls must be present before COGANT prose can use
surrogate-model language for an organization-level sketch.

### E.12 World-model proof and exported-model certificates

[91] Bakhta, A. (2026). **ProvableWorldModel: commit-and-audit proofs for
world-model inference.** Software artifact. ProvableWorldModel demonstrates
a commitment-bound audit pattern for exact quantized world-model inference:
Merkle commitments bind model and trace artifacts, Fiat-Shamir derives the
audit challenge, Freivalds checks fixed-weight matrix multiplications, and
cheap deterministic operations are replayed exactly. For COGANT, it is most
useful as a boundary reference and future-method target for exported-model
certificates: COGANT can bind source, config, package checksums, and runtime
trace digests today, but it should not claim a proof of inference execution
without implementing a comparable verifier [@provableworldmodel2026].

### E.13 Scholarship coverage checklist

The main text uses this appendix as a coverage check, not as an
exhaustive bibliography. The current manuscript should be read as satisfying
the following reviewer-facing scholarship commitments:

| Commitment | Primary anchor cluster | Where the main text answers it |
|---|---|---|
| Program graphs are grounded in existing AST/CFG/PDG/CPG practice. | E.1 and @sec:08-01-landscape-and-tool-categories | @sec:02-01-program-graph-and-formal-foundations, @sec:08-02-program-analysis-for-ml-and-tables |
| Deterministic rules are positioned against learned code models without strawman comparisons. | E.1, E.3, and LLM surveys in `references.bib` | @sec:01-introduction, @sec:08-05-threats-to-validity |
| Active-inference language is bounded by POMDP and matrix-validity evidence. | E.2, E.6, and E.9 | @sec:02-04-gnn-export-and-error-handling, @sec:08-04-world-models-boundaries-and-compatibility, @sec:09-ablation |
| Roundtrip language is weaker than full bidirectional-transformation proof. | E.7 and E.8 | @sec:08-03-lenses-and-synthesis, @sec:S01-appendix-roundtrip-epsilon |
| Reproducibility claims are tied to manifests, metrics, sidecars, and scripts. | E.10 | @sec:06-experimental-setup, @sec:07-reproducibility, @sec:S06-appendix-source-references |
| Figure claims are task- and evidence-bounded. | E.10 | @sec:04-rendered-end-to-end-figures, @tbl:figure-reading-order, @tbl:figure-provenance-groups |
| Organization-level extensions are treated as future typed surrogate models, not shipped corporate simulators. | E.11 | @sec:02-03-state-space-and-behavior, @sec:08-04-world-models-boundaries-and-compatibility, @sec:10-conclusion |
| Exported-model proof language is bounded by implemented artifact checks, not borrowed from adjacent proof systems. | E.12 | @sec:08-04-world-models-boundaries-and-compatibility |

: Scholarship coverage checklist for the COGANT manuscript. {#tbl:S05-scholarship-coverage-checklist}
