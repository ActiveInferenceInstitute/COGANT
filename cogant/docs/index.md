# COGANT

> **What this page is:** The documentation entry point for COGANT — what the project does, why it exists, and where to go next.
>
> **Prerequisites:** None.
>
> **Reading time:** ~4 minutes
>
> **Next steps:** [Installation](getting-started/installation.md) · [Tutorial 1: Quickstart](tutorials/01_quickstart.md) · [Active Inference for programmers](concepts/active_inference.md)

**Codebase-to-GNN Translation Engine** — turn software repositories into Active Inference state-space models expressed in Generalized Notation Notation (GNN).

COGANT parses a repository, builds a typed program graph, assigns semantic mappings to the nodes and fragments it can justify (HIDDEN_STATE / OBSERVATION / ACTION / POLICY / CONSTRAINT / ...), compiles a Markov blanket, derives A/B/C/D generative-model matrices, and exports a validated GNN package plus JSON / PyArrow / HTML artifacts for downstream training pipelines and audits. Unmapped nodes remain explicit in coverage reports rather than being silently forced into a role.

---

## Why COGANT

- **Structural, not heuristic.** Roles are assigned from `NodeKind`, `EdgeKind`, name keywords, and degree statistics — every decision is inspectable and reproducible.
- **Provenance-first.** Every node, edge, and mapping is traceable to a source span or a documented inference rule.
- **Confidence-aware.** Every mapping carries an epistemic score; partial inputs degrade gracefully instead of halting.
- **GNN-native.** Output follows the Active Inference Institute's Generalized Notation Notation bracket format and validates against a shipped schema.

---

## Install

```bash
pip install cogant
# or, with all extras (viz + multilang + dev):
pip install "cogant[all]"
```

From source:

```bash
git clone https://github.com/docxology/cogant.git
cd cogant
uv sync --all-extras
```

See [Installation](getting-started/installation.md) for the full matrix.

---

## Quickstart

Translate a repository into a full GNN bundle:

```bash
cogant translate ./my_repo --output output/ --layout-output
cogant validate output/
cogant explain ./my_repo my_function
```

The full Python API and CLI walkthrough live in [Quick Start](getting-started/quickstart.md).

---

## Where to go next

- **[Documentation modules](reference/documentation_modules.md)** — map of every `docs/<module>/` area (API, architecture, evaluation, export, and others).
- **[Evaluation index](evaluation/README.md)** — current readiness, roundtrip, calibration, and empirical-evidence pages. Machine-readable corpora and dashboards live in the `evaluation/` directory at the repository root (sibling of `docs/`; not shipped in the installable wheel).
- **[Small repo walkthrough](tutorials/calculator.md)** — step through the `calculator` fixture: 6 mappings, 12 nodes, one clean Markov blanket.
- **[Flask app walkthrough](tutorials/flask.md)** — a 98-node / 597-edge real-world example with role counts and GNN output excerpts.
- **[Active Inference mapping](theory/active_inference.md)** — the 22 translation rules and the seven **Active Inference** `MappingKind` labels counted in `METRICS.yaml` (HIDDEN_STATE, OBSERVATION, ACTION, POLICY, PREFERENCE, CONSTRAINT, CONTEXT). `SemanticRole` and rule outputs also use values such as PARAMETER separately; see the mapping page.
- **[Round-trip verification](theory/roundtrip.md)** — `roundtrip_status`, `role_preservation_score`, strict invariant ledgers, and generated-code checks.
- **[GNN format](theory/gnn_format.md)** — bracket notation, A/B/C/D matrices, and an example export block.
- **[CLI Reference](cli_reference.md)** — every subcommand, flag, and output artifact.
- **[API Reference](api/translate.md)** — auto-generated module docs for `cogant.translate`, `cogant.gnn`, `cogant.markov`, `cogant.statespace`, `cogant.static`, and `cogant.simulate`.

---

## Docs layout (maintainers)

- **Agent routing and tooling:** [AGENTS.md](AGENTS.md).
- **Module map:** [Documentation modules](reference/documentation_modules.md).
- **Changelog mirror:** [changelog.md](changelog.md) (source of truth: package root `CHANGELOG.md`; sync with `cp CHANGELOG.md docs/changelog.md`).
- **Package README:** [repository `README.md`](https://github.com/docxology/cogant/blob/main/cogant/README.md) (install and repo overview).
