# Organization State Spaces

Status: provisional research note.

Open question: can COGANT's typed graph, state-space, provenance, and GNN export discipline be extended from source repositories to socio-technical organization artifacts without laundering static org charts into behavioral claims?

## Thesis

A typed organization artifact can be treated as a **static prior** over coordination. Organizational units, roles, posts, service ownership records, reporting lines, and process diagrams are useful because they name candidate state factors, action channels, observation surfaces, and controller boundaries. They are not enough to model organizational behavior.

The defensible research direction is a typed organizational surrogate:

- Static artifacts provide schema and role evidence.
- Dynamic traces provide observations: process events, incidents, ticket flow, commits, reviews, approvals, service telemetry, handoffs, and communication edges.
- COGANT-style provenance records keep every inferred state, action, observation, and transition linked to the artifact or trace that produced it.
- Downstream active-inference runtimes can operate on the resulting GNN bundle only after confidence, degraded-output defaults, and trace coverage are exposed.

## Mapping Sketch

| Organizational artifact | COGANT analogue | State-space role |
|---|---|---|
| Organizational unit or team | Module or subsystem node | Hidden state factor or controller scope |
| Role or post | Semantic role / typed interface | Policy, action, or observation channel candidate |
| Reporting line | CONTAINS / CALLS / ownership edge | Structural prior over coordination |
| BPMN task or event | Function/action/event node | Action or observation modality |
| Service ownership | Public API and dependency boundary | Markov-blanket candidate |
| Incident, ticket, commit, approval, telemetry trace | Runtime coverage or dynamic trace | Dynamic evidence for transition updates |

This mapping is intentionally weaker than a claim of organizational simulation. It says that a typed organization graph plus dynamic trace streams could be compiled into a reviewable candidate model, not that the formal chart determines real behavior.

## Capital-Allocation Loop Analogue

AlphaFund's white paper, [Recursive Self-Improvement is a Portfolio Optimization Problem](https://www.alphafund.com/whitepaper), is useful as an adjacent industry framing for how a typed organizational surrogate would need to earn optimization language. Its Economic World Model is not a COGANT component, and its t-RSI statistic is not implemented here. The transferable idea is the bookkeeping discipline: every channel needs a time-indexed history of observations, interventions, costs, and realized outcomes before capital allocation can be audited.

| AlphaFund term | COGANT analogue | Boundary |
|---|---|---|
| Firm or channel history | Dynamic evidence stream | Must be timestamped and provenance-linked; not inferred from static structure alone |
| Economic World Model | Learned surrogate candidate | Future research object, not a shipped COGANT model |
| Sensors | Observation channels | Data feeds, telemetry, tickets, incidents, or process events that expand what the model can condition on |
| Actuators | Action channels | Interventions the organization can execute and later score |
| R&D or parameters | Model-improvement channels | Candidate updates whose effects need held-out or prospective evidence |
| t-RSI | External improvement signal-to-noise concept | Not a COGANT metric; cite only as AlphaFund's proposed statistic |

Read this as a design constraint: a future COGANT organization model should expose the rows that would make an optimizer accountable, not merely assert that an organization is optimizable.

## Typed Organizational Surrogates And Differentiability

"End-to-end differentiable typed corporations" is useful only as shorthand for a future optimization-compatible surrogate model. It should not be read literally. The differentiable object would be a surrogate over typed artifacts, dynamic traces, declared loss terms, and bounded intervention variables. Legal entities, people, incentives, employment decisions, and financial or legal obligations are outside the differentiability claim.

A valid research artifact would need:

- Typed interfaces for teams, roles, services, and process boundaries.
- A differentiable or almost-everywhere differentiable surrogate over model parameters, interventions, or loss functions.
- Explicit observation channels and uncertainty surfaces.
- Provenance links from every model factor back to source artifacts or traces.
- Declared loss/objective terms and intervention bounds.
- Prohibited decision uses, including legal, financial, and HR automation.
- A negative-control suite showing when org-chart-only input produces an underdetermined or misleading model.

The target would be design support: compare bounded interventions, expose coordination bottlenecks, or test whether a proposed structure has enough observable evidence to justify optimization. Optimization means bounded search over the surrogate surface, not a guarantee of organizational improvement.

## Analysis Validation Surface

The provisional checker `../../../tools/organization_state_space_audit.py` gives this note a concrete RedTeam surface. It validates a JSON sketch with required evidence lanes:

- Typed static organization or process artifacts.
- Parseable, time-indexed dynamic traces.
- Candidate state, action, and observation factors.
- Role-compatible, evidence-bearing transitions whose `from_state`, `to_state`, and `action` fields resolve to state, state, and action factors and whose evidence does not leak backward from the future.
- Negative controls for org-chart-only and trace-only inputs.
- When a sketch claims differentiable-surrogate readiness: `optimization_surface`, `loss_terms`, `differentiability_scope`, `intervention_bounds`, `evidence_links`, and `prohibited_decision_uses`.

Run the built-in positive fixture from the COGANT project root:

```bash
uv run python tools/organization_state_space_audit.py \
  --output-dir /tmp/cogant_org_state_space_audit \
  --strict
```

The helper emits:

| Output | Purpose |
|---|---|
| `/tmp/cogant_org_state_space_audit/organization_state_space_audit.json` | Machine-readable findings and claim boundary |
| `/tmp/cogant_org_state_space_audit/organization_state_space_audit.md` | Reviewable prose summary |
| `/tmp/cogant_org_state_space_audit/organization_state_space_audit.svg` | Evidence-lane visualization |

For design reviews, use `--spec path/to/sketch.json` and keep `--strict` enabled. The intended negative controls are simple: a sketch with only an org chart should fail for missing dynamic evidence, and a sketch with only traces should fail for missing typed artifacts. A transition whose supporting event happens after the transition timestamp should also fail, as should a transition that swaps an action factor into a state slot or a state factor into an action slot. A differentiable-surrogate sketch should fail if it omits losses, intervention bounds, evidence links, differentiability scope, or prohibited decision uses. Passing this helper still does not mean COGANT has modeled an organization; it means the sketch has the minimum evidence shape required for further R&D review.

## RedTeam Boundaries

- An org chart is a structural prior, not behavior.
- Dynamic traces are partial, biased observations, not ground truth.
- Incentives, informal power, hidden work, and external constraints can dominate the formal graph.
- Differentiability requires a deliberately designed surrogate surface; arbitrary human organizations are not differentiable programs.
- Optimization without provenance, loss definitions, intervention bounds, and non-use boundaries can produce persuasive but unaccountable management recommendations.

## Promotion Criteria

Promote this note out of `rnd/` only after there is a runnable prototype or checked design report that:

- Ingests at least one typed organization/process artifact and one dynamic trace stream.
- Emits a GNN package with provenance-bearing state/action/observation factors.
- Reports degraded-output defaults and trace coverage.
- Includes negative controls for org-chart-only and trace-only inputs.
- Declares differentiability scope, loss terms, intervention bounds, evidence links, and prohibited decision uses before using optimization language.
- Separates research visualization from any operational recommendation.

## Related Reading

- [Code as generative model](../theory/code_as_generative_model.md)
- [Active Inference mapping](active_inference_mapping.md)
- [Calibration](calibration.md)
- [AlphaFund white paper](https://www.alphafund.com/whitepaper)
- [Evaluation literature](../evaluation/LITERATURE.md)
