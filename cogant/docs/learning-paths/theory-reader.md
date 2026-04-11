# Theory Reader — Learning Path

You want to understand the *why* behind COGANT: how Active Inference,
Markov blankets, and the GNN format combine to make "code as a generative
model" a coherent claim rather than a metaphor. This path is for researchers,
reviewers, and anyone who needs to defend or critique the approach.

Estimated reading time: ~3 hours. No hands-on requirement, but having
an example GNN open in a side window helps.

## Steps

1. **[Active Inference for Programmers](../concepts/active_inference.md)** —
   The friendliest entry point. Builds intuition for the Free Energy Principle
   and active inference using programming analogies before any math. Read
   this even if you already know active inference — it sets up the COGANT-
   specific vocabulary used throughout the rest of the docs.

2. **[Markov Blankets in Codebases](../concepts/markov_blanket.md)** — The
   central conceptual move: a function (or module, or service) is a Markov
   blanket separating internal state from sensory inputs and active outputs.
   This is what makes the translation well-defined.

3. **[What is a GNN?](../concepts/gnn.md)** — The notation we emit. Once you
   understand Markov blankets, GNN is "just" a serialization format for the
   resulting state-space model.

4. **[The Forward-Reverse Cycle](../concepts/roundtrip.md)** — Why we care
   about being able to translate code → GNN → code, and what it means for
   the translation to be (approximately) an isomorphism. This is the
   theoretical hinge of the project.

5. **[Roundtrip Evaluation](../evaluation/ROUNDTRIP_EVAL.md)** — The empirical
   counterpart to step 4: how we *measure* whether the roundtrip preserves
   semantics, what the current numbers look like, and how to read them.

6. **[Active Inference Mapping (R&D)](../rnd/active_inference_mapping.md)** —
   The deep dive. Where each piece of an active-inference generative model
   (states, observations, actions, preferences, priors) lives in a real
   codebase, with worked examples.

## Adjacent reading (optional but recommended)

- **[Active Inference Primer (theory/)](../theory/active_inference_primer.md)** —
  More mathematical treatment of the same material as step 1.
- **[Code as Generative Model](../theory/code_as_generative_model.md)** —
  The full theoretical framing.
- **[Isomorphism Theorem](../theory/isomorphism.md)** and the
  [empirical results](../evaluation/ISOMORPHISM_THEOREM.md).
- **[GNN Format Reference](../theory/gnn_format_reference.md)** — When the
  conceptual treatment isn't enough and you need the formal grammar.
- **[Literature](../evaluation/LITERATURE.md)** and
  [Related Work](../evaluation/RELATED_WORK.md) for situating the project.

## Where to go next

- To **see the theory in action** on a real repo, follow the
  [New User](new-user.md) tutorials.
- To **extend the active-inference mapping** to a new construct, follow the
  [Plugin Author](plugin-author.md) path.
- If you have **suggestions, corrections, or want to contribute**, follow the
  [Contributor](contributor.md) path.
