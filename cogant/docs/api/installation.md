## Installation

> **What this page is:** Quick install instructions for COGANT from a source checkout — minimum required for the API to be importable.
>
> **Prerequisites:** Python 3.11+ and pip.
>
> **Reading time:** ~3 minutes
>
> **Next steps:** [API overview](overview.md) · [Quick Start](quick_start.md) · [Getting started: Installation](../getting-started/installation.md)

From the repository root:

```bash
uv sync --all-extras
```

Or: `pip install -e ".[dev,viz]"`. Sources: `py/cogant/`. Compatibility pins:
`py/requirements.txt` (optional).
