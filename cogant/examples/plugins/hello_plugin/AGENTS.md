# Agents — examples/plugins/hello_plugin

Minimal plugin package demonstrating the COGANT plugin registration protocol.

- `rule.py` — registers a sample translation rule via the plugin entry point
- `pyproject.toml` — plugin package metadata with `cogant.rules` entry point
- Install with `pip install -e .` from this directory to activate the plugin
- Parent coordination: [../AGENTS.md](../AGENTS.md)
