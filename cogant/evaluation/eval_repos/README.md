# Evaluation corpus

Twelve pinned third-party Python repositories vendored as git submodules and used as benchmark fixtures for COGANT's quantitative evaluation. Each entry is a `160000`-mode pointer; the working-tree contents are upstream code and should not be edited locally.

## Setup — cloning with eval submodules

The 12 submodules are wired through the top-level [`/.gitmodules`](../../../.gitmodules) manifest. Populate them with either:

```bash
# Fresh clone (recommended)
git clone --recurse-submodules https://github.com/docxology/cogant.git

# Existing clone (also works after a normal clone)
git submodule update --init --recursive cogant/evaluation/eval_repos
```

Empty checkouts make benchmarks skip rather than fail, so this step is only needed when running the quantitative evaluation pipeline.

See [`AGENTS.md`](AGENTS.md) for the per-submodule inventory, refresh procedure, and consumer references.

The metrics derived from these fixtures are reported in [`../METRICS.yaml`](../METRICS.yaml) and the manuscript chapter [`../../../manuscript/06_03_performance_and_fixture_metrics.md`](../../../manuscript/06_03_performance_and_fixture_metrics.md).
