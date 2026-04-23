# Installation

> **What this page is:** Step-by-step COGANT installation instructions for PyPI, source, and editable/development setups, including optional extras.
>
> **Prerequisites:** Python 3.11+ and pip (or `uv`/`pipx`).
>
> **Reading time:** ~5 minutes
>
> **Next steps:** [Quick Start](quickstart.md) · [Tutorial 1: Quickstart](../tutorials/01_quickstart.md) · [API quick start](../api/quick_start.md)

COGANT targets Python **3.11+** and ships a Typer-based CLI (`cogant`) plus a stable Python API (`cogant.api`).

## From PyPI

```bash
pip install cogant
```

With all optional extras (visualization, multi-language parsers, dev tools):

```bash
pip install "cogant[all]"
```

## Extras

| Extra | Contents | When to install |
| --- | --- | --- |
| `dev` | `pytest`, `pytest-cov`, `ruff`, `mypy` | contributing |
| `viz` | `plotly`, `matplotlib`, `jinja2` | HTML site + PNG export |
| `multilang` | `tree-sitter` Python / JS / TS grammars | non-Python repos |
| `all` | everything above | full experience |

## From source (uv, recommended)

```bash
git clone https://github.com/cogant-contributors/cogant.git
cd cogant
uv sync --all-extras
uv run cogant --help
```

## From source (pip)

```bash
git clone https://github.com/cogant-contributors/cogant.git
cd cogant
pip install -e ".[dev,viz]"
cogant --help
```

## Verify the install

```bash
cogant --help           # authoritative list: 28 top-level names (26 commands + plugin + migrate groups)
cogant scan .           # run a minimal static analysis on the current directory
```

If `cogant --help` lists subcommands, the install is working. **Leaves:** 29 runnable subcommands in total — the two groups add `plugin list`, `plugin info`, and `migrate migrate` under the 26 `@app.command` registrations. Four commands (`analyze-static`, `analyze-graph`, `visualize`, `export`) are **preview stubs** (API pointers only) — see [CLI reference](../cli_reference.md). If the `cogant` entry point is missing or `--help` fails, re-check Python 3.11+ and that the venv containing COGANT is activated.
