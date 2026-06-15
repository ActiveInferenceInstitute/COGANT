# `cogant/evaluation/eval_repos/` — vendored evaluation corpus

## Purpose

External Python repositories used as benchmark fixtures for COGANT's quantitative evaluation. Each entry is a git submodule pointer (mode `160000`) to a pinned upstream commit; agents should treat the contents as **read-only third-party code**.

## Inventory

| Submodule | Upstream | Used by |
| --- | --- | --- |
| `click/` | `pallets/click` | CLI surface fixture for `cogant translate` benchmarks. |
| `dateutil/` | `dateutil/dateutil` | Library fixture (date math, parser stress). |
| `dulwich/` | `jelmer/dulwich` | Pure-Python git impl — large structural repo for graph/translation rules. |
| `fastapi/` | `tiangolo/fastapi` | Web framework fixture for `cogant analyze --incremental` runs. |
| `flask/` | `pallets/flask` | Reference web app referenced in [`docs/tutorials/flask.md`](../../docs/tutorials/flask.md). |
| `httpx/` | `encode/httpx` | Async HTTP client; tests dynamic-flow extraction. |
| `pydantic/` | `pydantic/pydantic` | Heavy generic-typing fixture for type-inference passes. |
| `pyyaml/` | `yaml/pyyaml` | Mixed Python/C parser; exercises tree-sitter fallback. |
| `requests/` | `psf/requests` | Classic HTTP library — small but role-rich. |
| `rich/` | `Textualize/rich` | Terminal rendering library; lots of dataclasses + protocols. |
| `tqdm/` | `tqdm/tqdm` | Tiny utility — used as a fast smoke fixture. |
| `urllib3/` | `urllib3/urllib3` | Lower-level HTTP plumbing for resilience-rule coverage. |

## Cloning with eval submodules

The 12 entries above are tracked as proper git submodules (see the
top-level [`/.gitmodules`](../../../.gitmodules) manifest). Fresh clones
default to *empty* checkouts — populate them with one of:

```bash
# Initial clone (one shot)
git clone --recurse-submodules https://github.com/ActiveInferenceInstitute/COGANT.git

# Existing clone, populate eval corpus
git submodule update --init --recursive cogant/evaluation/eval_repos
```

To bump a single pin to its upstream `HEAD`:

```bash
git submodule update --remote cogant/evaluation/eval_repos/<name>
git add cogant/evaluation/eval_repos/<name>
git commit -m "chore(eval): bump <name> submodule"
```

## Conventions for agents

- Do **not** modify files inside any submodule directory; changes are not tracked at this repo level.
- To refresh a pin, use `git submodule update --remote <path>` (see above) or update the commit OID directly with `git update-index --cacheinfo`.
- Benchmark scripts under [`../../benchmarks/`](../../benchmarks/) reference these paths via `cogant.evaluation.eval_repos.<name>` — do not rename directories without updating the corresponding fixture loaders.
- Empty/missing submodule checkouts make benchmarks skip (`pytest.skip(reason=…)`) rather than fail; see [`../../benchmarks/AGENTS.md`](../../benchmarks/AGENTS.md).

## Related docs

- [`../AGENTS.md`](../AGENTS.md) — `cogant/evaluation/` package overview.
- [`../../docs/evaluation/AGENTS.md`](../../docs/evaluation/AGENTS.md) — evaluation methodology and metric definitions.
