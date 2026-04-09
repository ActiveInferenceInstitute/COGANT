# Active Inference primer

> **For readers who have never encountered Active Inference.** This page is intentionally short: just enough to understand the COGANT pipeline and the A / B / C / D matrices.

## What is Active Inference

**Active Inference** is a framework from computational neuroscience (Karl Friston and
collaborators, ~2009 onward) that models any adaptive system — a brain, a robot, a
thermostat, an organization — as an **inference machine** that maintains beliefs about hidden
causes of its sensory input. The system acts on the world specifically to **minimize the
surprise** of its future observations, where "surprise" is the negative log-probability of
an observation under the system's own generative model.

A one-sentence summary: **agents are probabilistic models that update themselves to make
their predictions come true.**

## What is the Free Energy Principle

The **Free Energy Principle** is the underlying claim that *all* self-organizing systems —
biological or artificial — can be described as minimizing a quantity called **variational free
energy**. Variational free energy is an upper bound on surprise, so minimizing it is an
efficient way to minimize surprise without having to compute the intractable marginal
`p(o) = ∫ p(o, s) ds` directly.

For COGANT the important consequence is: **free energy is computable from a generative model
and an observation stream**. If we can give a piece of code a generative-model interpretation
(i.e. A, B, C, D matrices), we can in principle compute its free energy at runtime.

## Why does it apply to software

A program is a machine that takes inputs, maintains internal state, and produces outputs. So
is a thermostat. So is a brain. All three can be described with the same math:

- **Hidden states** (the internal state the program cannot directly see but has to infer).
- **Observations** (what the program reads — inputs, sensors, logged events).
- **Actions** (what the program writes — outputs, control signals, DB updates).
- **A generative model** (the program's belief about how hidden state produces observations,
  and how actions modify hidden state).

Once the mapping is made explicit, every software engineering concept you already know —
modularity, information hiding, the dependency inversion principle, retry and circuit-breaker
patterns — becomes a **special case** of variational inference over a Markov blanket.

## A / B / C / D matrices in 60 seconds

An Active Inference generative model is parameterized by four quantities:

| Matrix | Full name | What it says |
| --- | --- | --- |
| **A** | **Likelihood** `P(o | s)` | "If the hidden state is `s`, what observation do I expect?" |
| **B** | **Transition** `P(s' | s, a)` | "If I take action `a` in state `s`, what state am I in next?" |
| **C** | **Log-preference** over observations | "Which observations do I prefer to see?" (positive is preferred, negative is aversive) |
| **D** | **Prior** `P(s_0)` | "What do I believe about the initial state before any observations?" |

Given these four, an Active Inference agent can:

1. **Infer hidden state** from observations by Bayesian update (`A` inverts observation into
   posterior over state).
2. **Plan actions** by minimizing **expected free energy** — the anticipated surprise of a
   hypothetical future trajectory under `B`, weighted by the preference `C` and prior `D`.
3. **Update its generative model** if the observations consistently disagree with predictions
   (model learning; not done by COGANT in v0.1).

## What is a Markov blanket

A Markov blanket is a set of variables `(s, a)` such that conditioning on them makes the
internal states μ conditionally independent of the external states η:

```text
p(μ | s, a, η) = p(μ | s, a)
```

In software, this is the same property as a well-encapsulated module: the private fields are
conditionally independent of the rest of the program given the public API. The Markov blanket
is the **dual** of information hiding.

COGANT's `py/cogant/markov/blanket.py` computes this partition directly from the program
graph in `O(V + E)`.

## Where to go next

- [Code as a generative model](code_as_generative_model.md) — why software repositories *are*
  generative models, not merely *describable* by them.
- [Active Inference mapping](active_inference.md) — the mechanical rule-by-rule version.
- [GNN format reference](gnn_format_reference.md) — how COGANT writes A/B/C/D to disk.
- [Tutorial 5: reading GNN matrices](../tutorials/05_gnn_interpretation.md) — worked example
  on a real codebase.
- **External.** Smith, Friston & Whyte (2022), *A step-by-step tutorial on active inference*;
  Da Costa et al. (2020), *Active inference on discrete state-spaces*; Parr, Pezzulo &
  Friston (2022), *Active Inference: The Free Energy Principle in Mind, Brain, and Behavior*.
