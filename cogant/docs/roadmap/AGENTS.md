# AGENTS.md — Roadmap module

Version plans, feature backlog, performance and coverage targets,
deprecation policy, community milestones, and the mirrored changelog. The
roadmap module is the canonical place to find out *when* something is
expected to happen and *what* the quality bar for each release is.

## Purpose and ownership

Everything here is forward-looking planning except the changelog **stub**
(`changelog.md`), which points readers at the canonical published changelog.
The roadmap is read by contributors, users, and AI
agents who need to know whether a feature is in scope, scheduled, or
ruled out. Owned by whoever is driving the current release train.

## File map

| File | Purpose | Update trigger |
|------|---------|----------------|
| `README.md` | TOC grouped by strategy / version / targets / process | Any time a file is added, removed, or renamed |
| `AGENTS.md` | This file — maintenance rules | When grouping, ownership, or the append-only changelog policy changes |
| `overview.md` | One-page roadmap summary | At every release train kickoff |
| `version_strategy.md` | Semver intent and version bucket definitions | When semver policy changes |
| `version_010_current.md` | Shipped capabilities of the 0.1.x line (retained for historical diff) | Only when a historical correction is needed |
| `version_020_planned.md` | 0.2.x plan (superseded once a version is shipped) | When 0.2.x scope changes |
| `version_030_planned.md` | 0.3.x plan (superseded once a version is shipped) | When 0.3.x scope changes |
| `version_050_shipped.md` | Full arc v0.1.0 → v0.5.0 plus April 2026 hardening history | After each shipped release that extends the shipped arc |
| `version_060_planned.md` | 0.6.x plan (language breadth, streaming, type inference) | When 0.6.x scope changes |
| `version_100_planned.md` | 1.0.0 stability / hardening / public API freeze | When 1.0 scope changes |
| `known_limitations_010.md` | Known limitations of the **current release** (filename retained for link stability; content tracks the latest shipped version) | Whenever a new limitation is discovered or an old one is fixed |
| `deprecation_policy.md` | Breaking-change announcement and staging policy | When the policy changes |
| `performance_targets.md` | Wall-clock and memory targets | When targets are renegotiated |
| `test_coverage_goals.md` | Per-component coverage goals | When coverage targets are renegotiated |
| `benchmarks_and_performance.md` | Benchmark methodology and headline numbers | When benchmarks are re-run |
| `cogant_benchmarks.md` | Detailed benchmark reference and protocol | When the protocol changes |
| `success_metrics_post_10.md` | Post-1.0 adoption and quality metrics | When post-1.0 metrics are defined |
| `feature_backlog.md` | Prioritized unshipped features | Continuously as features are proposed, ranked, or landed |
| `documentation_roadmap.md` | Per-release docs coverage targets | When docs scope for a release changes |
| `community_milestones.md` | Launch and community milestones | When a milestone lands or is rescheduled |
| `budget_resources.md` | Development time and resource estimates | When estimates change materially |
| `contingencies.md` | Slip and scope-cut fallbacks | When a contingency is triggered or added |
| `related_work.md` | Adjacent tools and research tracked for comparison | When a new comparable tool ships |
| `changelog.md` | Stub linking to [`../changelog.md`](../changelog.md); keeps legacy URLs working | Only if the stub workflow text changes |
| `see_also.md` | Cross-links to related modules | When link targets move |

## Changelog

Edit **`CHANGELOG.md`** at the package root, then publish:

```bash
cp CHANGELOG.md docs/changelog.md
```

[`changelog.md`](changelog.md) in this folder is a **stub** only (not a copy). The MkDocs **Changelog** nav entry is `docs/changelog.md`.

## Adding a new doc

1. Decide which of the four groupings (strategy, version, targets,
   process) the new page belongs to and place it near its siblings in
   `README.md`.
2. Use a short, lower-case, underscore-separated slug.
3. Every version-plan file follows the same skeleton: Scope, Goals,
   Scheduled work, Out of scope, Risks. Stick to the skeleton so readers
   can diff versions at a glance.
4. Add a row to the matching group table in `README.md`.

## Known gotchas

- Do not paste full release notes into `roadmap/changelog.md` — it is a stub.
  Sync `docs/changelog.md` from the root `CHANGELOG.md` in the same commit.
- The version-plan files use two suffixes: `_current.md` (the version whose
  content is still authoritative for "what is shipping now"), `_planned.md`
  (a plan that has not yet shipped), and `_shipped.md` (historical
  arc, kept append-only). When a version ships, its `_planned.md` content is
  folded into `version_050_shipped.md` (or the current canonical shipped
  file) rather than renamed in place, and the README's "Version plans"
  table is updated in the same commit.
- `known_limitations_010.md` deliberately keeps its legacy `_010` suffix
  to avoid breaking inbound links; the content inside always tracks the
  latest shipped release, not 0.1.0.
