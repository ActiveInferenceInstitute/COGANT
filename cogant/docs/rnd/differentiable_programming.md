# Differentiable programming and COGANT

Which differentiable-programming ideas can improve COGANT's executable models
while preserving the distinction between source structure and model semantics?

Status: 2026-10-26. Primary-source review and bounded numerical implementation;
broader proposals remain research work. Numerical contracts live in the
[inference API reference](../api/inference.md); existing scientific
limits remain in [end-to-end inference](end_to_end_inference.md).

## Source review

[The Elements of Differentiable Programming](https://diffprog.github.io/),
by Mathieu Blondel and Vincent Roulet, connects parameterized programs,
derivatives, probabilistic inference, and optimization. The following mapping
is our interpretation of its primary text applied to COGANT.

| Primary source and exact section | Connection to COGANT | Consequence |
| --- | --- | --- |
| [Chapter 4, §§4.1.1–4.1.3](https://diffprog.github.io/neural_nets.html#sec-4.1) | Computation graphs represent dependencies between intermediate function values. COGANT's ProgramGraph records program entities and relations at a coarser level. | Operation semantics, variable versions, shapes, and primitive derivative rules would be needed before treating this graph as an autodiff representation. |
| [Chapter 5, §§5.6.1–5.6.3](https://diffprog.github.io/cf.html#cf:sec:if_else) | Branch inputs and comparison predicates have different derivative behavior. COGANT chooses modal observations and minimum-score actions discretely. | Fix the action sequence when differentiating; changing to a soft policy would change the model contract and needs separate admission and tests. |
| [Chapter 7, §7.3](https://diffprog.github.io/finite_diff.html#sec-7.3) | Symmetric finite differences provide an independent derivative approximation, with step-size truncation and roundoff trade-offs. | Check analytic gradients at multiple perturbation sizes on asymmetric models. |
| [Chapter 8, §§8.4.1–8.4.3](https://diffprog.github.io/auto_diff.html#sec-8.4) | Derivative primitives and their composition require explicit rules; stable numerical primitives matter. | Keep sensitivity in the shared categorical kernel so runtime and generated code use one implementation. |
| [Chapter 10, §10.9.1](https://diffprog.github.io/gm.html#sec-10.9.1) | Gradients of exponential-family log-partition functions yield expected sufficient statistics. C's normalized log preferences use a categorical log-partition. | Expose a precisely scoped derivative of the existing policy score with respect to C. |

## Implemented connection: log-preference sensitivity

For fixed A, B, belief, and policy of length H, let `p_t = A @ q_t` after
each controlled prediction. With normalized stochastic matrices, COGANT's
existing risk-plus-ambiguity score can be written as

```text
G(C) = sum_t [sum_j p_t[j] * (log(p_t[j]) - C[j] + logsumexp(C))
              + expected_likelihood_ambiguity(q_t)]
```

The ambiguity and `p_t` do not depend on C under these fixed inputs, so

```text
gradient_C G[j] = H * softmax(C)[j] - sum_t p_t[j]
```

This is our derivation for the implemented objective, rather than a claim that
the book evaluates COGANT. For outcome mass `m_t` within floating-point
admission tolerance, the implementation sums `m_t * softmax(C)[j] - p_t[j]`.
This matches the score actually computed without silently renormalizing inputs.
The gradient sums to zero up to rounding, reflecting invariance under a common
offset to C. It remains informative even when the predicted outcome has zero
mass; no `log(0)` is needed for this derivative.

The API is `CategoricalModel.score_preference_gradient(beliefs, policy)`, also
available through `MatrixFunctions` and generated `matrices.py`. Tests compare
every coordinate against central differences, independently calculated action
sequences, offset invariance, saturated preferences, admission-tolerance
behavior, input rejection, and isolated generated execution with `-I -S`.

No automatic parameter updates or gradient optimizer are introduced. The
existing frequency-based A/D learning retains its documented meaning.

## Further work with concrete admission requirements

1. **Posterior JVP:** for fixed observation likelihood `a`, prior `d`,
   normalizer `Z = dot(a,d)`, posterior `q`, and prior direction `v`, use
   `(a*v - q*dot(a,v))/Z`. Define simplex tangent and support contracts first;
   retain zero-evidence refusal and test against independent perturbations.
2. **Matrix-free curvature for C:** the fixed-policy Hessian for exactly
   normalized outcomes is `H * (diag(p) - p*p.T)`, where `p = softmax(C)`.
   Test Hessian-vector products, common-offset null direction, and positive
   semidefiniteness before adding any optimization API.
3. **Operation-level program representation:** retain input/output identities,
   mutation ordering, operation types, shapes, and unsupported primitives.
   Reject unresolved operations rather than assigning a derivative based on a
   function's name or a structural role.
4. **Source-bound witness interoperability:** GNN v5.0.1 adds finite-filtering
   and passive linear-Gaussian witnesses. COGANT's code-derived aggregate
   matrices need a separately checked axis/timing/parameter contract before
   claiming admission to those witnesses. See the
   [published release](https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation/releases/tag/v5.0.1).

These proposals do not establish differentiability of arbitrary repositories,
preservation of source behavior, posterior parameter inference, or task success.
