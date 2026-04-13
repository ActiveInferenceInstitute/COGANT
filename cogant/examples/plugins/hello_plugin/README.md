# hello_plugin

Minimal COGANT plugin package demonstrating the plugin registration protocol.

- `rule.py` — registers a sample translation rule via the `cogant.rules` entry point
- `pyproject.toml` — plugin package metadata; install with `pip install -e .` from this directory
- After install the rule fires during normal pipeline execution alongside built-in rules

Agent notes: [AGENTS.md](AGENTS.md) · Plugins hub: [../AGENTS.md](../AGENTS.md)
