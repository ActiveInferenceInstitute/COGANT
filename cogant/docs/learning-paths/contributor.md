# Contributor — Learning Path

You want to contribute to COGANT itself: fix a bug, add a feature, improve
the docs, or land a research result. This path orients you to how the project
is organized, what the current state of the codebase is, and where the
roadmap is heading.

Estimated reading time: ~2 hours, plus whatever it takes to dig into the
specific area you want to work on.

## Steps

1. **AGENTS.md (project root)** — The single most important file for any
   contributor or AI agent working in this repository. It encodes the working
   conventions, the test-first discipline, the no-mocks policy, and the
   "thin orchestrator" rule. Located at `AGENTS.md` in the repository root
   (also surfaced inside the docs at `docs/AGENTS.md`). Read it before
   touching code.

2. **[R&D Status](../evaluation/R&D_LOG.md)** — The current research and
   validation status: active evidence, readiness gaps, and the commands that
   keep the evaluation surface reproducible. Use it to understand the current
   focus before changing a subsystem or claim.

3. **[v1.0 Readiness](../evaluation/V1.0_READINESS.md)** — The honest
   assessment of what's blocking a 1.0 release: which subsystems are stable,
   which are still in flux, and what concrete gaps remain. If you're looking
   for "where can I make the biggest difference right now?", start here.

4. **[Roadmap Overview](../roadmap/overview.md)** — The forward-looking
   complement to step 3. Versions, themes, and the rough order in which
   things are planned. Cross-reference your idea against the roadmap before
   you start a large change — it may already be slated, or it may belong in
   a later release than you'd guess.

## Adjacent reading (pick what matches your work)

- **Code organization:**
    - [Architecture Overview](../architecture/overview.md)
    - [Component Details](../architecture/component_details.md)
    - [Testing Strategy](../architecture/testing_strategy.md)
- **Process:**
    - [Deployment / CI](../CI.md)
    - [Test Coverage Goals](../roadmap/test_coverage_goals.md)
    - [Deprecation Policy](../roadmap/deprecation_policy.md)
- **Research direction:**
    - [Active Inference Mapping (R&D)](../rnd/active_inference_mapping.md)
    - [Calibration (R&D)](../rnd/calibration.md)
    - [Final Report](../evaluation/FINAL_REPORT.md)
    - [Empirical Claim](../evaluation/EMPIRICAL_CLAIM.md)
- **Security and disclosure:**
    - [Responsible Disclosure](../security/responsible_disclosure.md)
    - [Security Release Process](../security/security_release_process.md)

## Where to go next

- For **theoretical** contributions, the [Theory Reader](theory-reader.md)
  path is your prerequisite reading.
- For **plugin-flavored** contributions (new languages, new exporters,
  new rules), the [Plugin Author](plugin-author.md) path covers the
  extension points.
- For **API-shaped** contributions (improving the Python surface, fixing
  edge cases, adding examples), the [API Consumer](api-consumer.md) path
  gets you fluent with the public surface before you start changing it.
