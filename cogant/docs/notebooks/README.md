# Notebooks

> Executable Jupyter notebook walkthroughs of every major COGANT workflow. Each numbered notebook ships as both an `.ipynb` (executable) and an `.md` (rendered for the docs site) where applicable. Use these when you want to step interactively through a workflow with all intermediate state visible.

## Contents

| Page | Description | Level |
|------|-------------|-------|
| [01 Forward Pipeline](01_forward_pipeline.md) | Code -> GNN forward pipeline walkthrough. Background: [program graph](../concepts/program_graph.md), [role assignment](../concepts/role_assignment.md) | Beginner |
| [02 Explore GNN](02_explore_gnn.md) | Inspecting and visualizing a generated GNN. Background: [GNN](../concepts/gnn.md), [Active Inference](../concepts/active_inference.md) | Beginner |
| [03 Reverse Synthesis](03_reverse_synthesis.md) | GNN -> Code reverse synthesis. Background: [roundtrip](../concepts/roundtrip.md), [reverse API](../api/reverse.md) | Intermediate |
| [04 Roundtrip](04_roundtrip.md) | Full forward + reverse roundtrip verification. Background: [roundtrip](../concepts/roundtrip.md), [Markov blanket](../concepts/markov_blanket.md) | Intermediate |
| [05 Custom Rules](05_custom_rules.md) | Writing and registering custom translation rules. Background: [translation rules reference](../reference/translation_rules.md), [rules overview](../rules/overview.md), [custom rules guide](../rules/custom_rules.md) | Intermediate |
| [06 Plugin Authoring](06_plugin_authoring.md) | Authoring a parser/exporter plugin. Background: [plugin API](../api/plugin_api.md), [rules overview](../rules/overview.md) | Advanced |
| [07 Real-World Flask](07_real_world_flask.ipynb) | End-to-end run against a real Flask application | Intermediate |
| [08 Constraint Authoring](08_constraint_authoring.ipynb) | Authoring CONSTRAINT-class translation rules | Advanced |
| [09 Plugin Authoring (Extended)](09_plugin_authoring.ipynb) | Deeper plugin authoring patterns and edge cases | Advanced |
| [10 Rule DSL](10_rule_dsl.ipynb) | Working with the rule DSL directly | Advanced |
| [11 Inference Learning](11_inference_learning.ipynb) | Learning from human review feedback to refine the rule set | Advanced |
| [12 Cross Language](12_cross_language.ipynb) | Cross-language roundtrip and analysis | Advanced |

## Recommended Reading Order

1. [01 Forward Pipeline](01_forward_pipeline.md) — see the full pipeline run live.
2. [02 Explore GNN](02_explore_gnn.md) — learn to read the artifacts you just produced.
3. [03 Reverse Synthesis](03_reverse_synthesis.md) and [04 Roundtrip](04_roundtrip.md) — close the loop.
4. [05 Custom Rules](05_custom_rules.md) — your first customization.
5. [07 Real-World Flask](07_real_world_flask.ipynb) — exercise everything on a non-trivial codebase.
6. [06 Plugin Authoring](06_plugin_authoring.md), [09 Plugin Authoring (Extended)](09_plugin_authoring.ipynb), [10 Rule DSL](10_rule_dsl.ipynb) — extension and authoring patterns.
7. [08 Constraint Authoring](08_constraint_authoring.ipynb), [11 Inference Learning](11_inference_learning.ipynb), [12 Cross Language](12_cross_language.ipynb) — advanced topics.

## Running the notebooks

```bash
pip install "cogant[notebooks]"
jupyter lab docs/notebooks/
```

See [related docs](../index.md) for theory background and the rest of the documentation tree.
