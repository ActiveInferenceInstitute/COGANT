# Intermediate Representations (IR) progression, translation engine, and algorithms {#sec:02-02-ir-progression-translation-engine}

## Progressive IRs

Processing proceeds through a sequence of representations. Which stages are complete for a given repository is summarized in [`../cogant/docs/reference/implementation_status.md`](../cogant/docs/reference/implementation_status.md) (partial areas include translation rules, state space, and Rust acceleration):

1. **Repo IR** — entities and relationships extracted from parsers.
2. **Program graph IR** — consolidated graph with deduplication and metadata.
3. **Semantic mapping IR** — output of the translation rule engine.
4. **State space IR** — variables, actions, transitions, observations.
5. **Process model IR** — higher-level control patterns where implemented.
6. **Validation IR** — coverage, confidence analysis, schema checks.

COGANT's program graph sits in the same conceptual space as compiler intermediate representations such as LLVM [@lattner2004llvm] and MLIR [@lattner2021mlir], but targets behavioral extraction and export for downstream learning rather than code generation or optimization. Put differently, it borrows compiler discipline -- typed intermediate state, deterministic passes, and validation -- while stopping at a research artifact boundary instead of lowering to executable machine code.

The method is therefore best read as an **evidence-producing pipeline** rather than
a semantics-preserving compiler. Each IR layer writes a material artifact
(`program_graph.json`, `semantic_mappings.json`, `state_space.json`, matrix JSON,
GNN Markdown, validation report, and optional dashboard figures). Later stages may
consume earlier artifacts, but they do not erase them: a low-confidence mapping,
parser fallback, skipped file, or matrix fallback stays inspectable in the run
directory and in the dashboard. This is the practical reason the manuscript
separates role preservation from strict structural isomorphism: the reverse
synthesizer can preserve the semantic-role population while still adding scaffold
nodes, normalizing matrices, or changing graph surface form.

## Translation rules

The **translation** stage applies declarative rules that refine roles, attach labels, and adjust confidence. Concurrency targets and layering are described in `../cogant/docs/architecture/README.md`. The rule engine composes passes over the graph in a **fixpoint loop**: rules are re-applied until no new semantic mappings emerge or a configurable iteration cap is reached. The fixpoint loop follows the classical formulation of program analysis as fixpoint computation over program-flow graphs and lattices of abstract states [@kildall1973unified; @cousot1977abstract]; in our setting the lattice is the set of semantic mappings partially ordered by inclusion, and the monotone operator is the composition of all registered rule applications. The implementation is intentionally lighter than a full Datalog engine, but it inherits the same declarative-analysis advantage demonstrated by Doop-style points-to specifications: the analysis contract is visible as rules rather than hidden inside ad hoc traversal code [@bravenboer2009strictly]. In the shipped implementation, each pass applies rules in descending `rule.priority`, and conflict resolution later compares `(rule_priority, confidence_score)` tuples when two mappings overlap, following the principle that edit representations should be composable [@yin2019learning].

### Fixpoint iteration, conflict resolution, and coverage

The shipped `TranslationEngine` in `../cogant/py/cogant/translate/engine.py` realizes the fixpoint loop concretely. Each iteration walks every registered rule once: the engine calls `rule.matches(graph, query)` to collect candidate fragments, then calls `rule.apply(graph, match)` on each, accumulating any resulting `SemanticMapping` objects keyed by their stable IDs. A per-pass counter tracks mappings that were genuinely new (not already present in the running set), and the loop terminates as soon as a pass completes with zero additions. The engine logs each iteration boundary through an internal match log, so the number of passes required to reach a fixed point is directly observable in the post-run diagnostics. The default iteration cap is `max_iterations = 10`; in testing, most repositories converge well before that bound, and the cap exists primarily as a safety valve against pathological rule sets that could otherwise oscillate indefinitely.

After fixpoint termination, the engine invokes `_resolve_conflicts()` to reconcile mappings whose `graph_fragment_node_ids` sets overlap. For each overlapping pair the engine retains the mapping with the larger `(rule_priority, confidence_score)` key and discards the other, logging a `conflict_resolved` event that records the losing ID, the winning ID, and the specific overlap set. Most shipped rules use the default `rule.priority` of 0; the mutating-subsystem / hidden-state rule uses priority 1 so it survives overlaps with same-confidence class-level aggregates (for example containment summaries) on the same `CLASS` node. A companion entry point, `translate_with_confidence()`, runs the standard fixpoint loop, rescores every surviving mapping through the `ConfidenceModel`, and then re-resolves conflicts so that any ordering shifts induced by rescoring are honored.

The same run also emits a rule-evidence trace. Each `SemanticMapping` carries additive metadata for the rule identifier, rule priority, matched node IDs, and fixpoint iteration that created it. `build_rule_evidence_trace()` then joins that metadata with graph snippets and the conflict log to produce a reviewer-facing table: mapping ID, role, confidence score, evidence snippets, confidence components, conflict-resolution outcome, and final status. This trace is COGANT's domain-specific analogue of a provenance record: it captures which activity produced the assertion, which graph entities it used, and which conflict-resolution activity modified its status, aligning with the entity/activity/derivation vocabulary of PROV-DM without requiring the JSON sidecar to be a literal PROV serialization [@moreau2013prov]. The finer-grained design is also consonant with provenance-semiring work, where derivation annotations are propagated through relational and Datalog-style fixed points instead of being collapsed into booleans [@green2007provenance]. Optional reviewer annotations mark mappings as accepted or rejected; the calibration summary derived from those annotations reports reviewed counts, accepted/rejected counts, per-rule precision proxies, and review coverage. This is deliberately narrower than a gold-standard recall claim: recall requires a labelled false-negative corpus, while the current artifact measures the precision of mappings that the rule engine actually proposed.

Translation coverage -- the fraction of graph nodes that received at least one semantic mapping -- is reported by `get_coverage_report(graph)`. It returns the total node count, the number of covered nodes, the number of uncovered nodes, a `coverage_percent` value rounded to two decimal places, and the sorted list of uncovered node IDs. The uncovered list is intentionally emitted verbatim so that downstream tooling can target unmapped regions for manual review or rule extension, rather than burying the gap behind a single aggregate number [@allamanis2018survey].

### Algorithm: Fixpoint translation engine {#sec:alg-fixpoint-translation-engine}

```text
input:  program graph G = (V, E), rule set R, maximum iterations K
output: semantic mappings M keyed by stable ID

M := {}
for k in 1..K:
    n_new := 0
    for rule r in R sorted by priority(r) descending:
        for match m in r.matches(G):
            mu := r.apply(G, m)
            if mu exists and mu.id not in M:
                M[mu.id] := mu
                n_new := n_new + 1
    if n_new == 0:
        break

return ResolveConflicts(M)
```

@sec:alg-fixpoint-translation-engine summarizes the engine. Termination is guaranteed because each iteration either produces at least one new mapping (whose stable ID is then fixed in $\mathcal{M}$) or terminates by the break condition; the outer $K$ bound serves as a safety valve for pathological rule sets.

### Algorithm: Priority-ordered conflict resolution {#sec:alg-conflict-resolution}

```text
input:  mapping set M, priority function p
output: reduced mapping set with no overlapping fragments

Build inverted index I: node ID -> mappings touching that node
C := all mapping pairs that co-occur in at least one I[node]
R := {}

for each pair (mu_a, mu_b) in C:
    if mu_a in R or mu_b in R:
        continue
    key_a := (p(mu_a), confidence(mu_a))
    key_b := (p(mu_b), confidence(mu_b))
    if key_a >= key_b:
        R.add(mu_b)
    else:
        R.add(mu_a)

return M minus R
```

@sec:alg-conflict-resolution detects conflicts via an inverted index in $O(\sum_v |\mathcal{I}(v)|^2)$ worst-case time, which is substantially faster than the naive all-pairs scan for graphs where most nodes carry at most one mapping.
