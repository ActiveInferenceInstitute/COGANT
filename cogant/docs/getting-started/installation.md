# Installation

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
cogant --help           # Typer app registers 14 subcommands
cogant scan .           # run a minimal static analysis on the current directory
```

If `cogant --help` shows subcommands you're done. If not, re-check that your active Python is 3.11+ and that the venv containing COGANT is activated.
