# CLI Commands

Subcommand implementations for the Typer-based COGANT command-line interface.

| Module | Commands |
|---|---|
| `analyze.py` | Analysis commands and static/graph entry points. |
| `export_validate.py` | Export and validation commands. |
| `ingest.py` | Repository ingest commands. |
| `setup.py` | Project initialization and environment setup commands. |
| `tools.py` | Utility and diagnostic commands. |
| `translate_cmd.py` | Translation and roundtrip commands. |

The app assembly lives one level up in `../_app.py` and `../main.py`. Keep
command implementations thin: parse CLI arguments, call API/orchestration
helpers, and return user-facing output.
