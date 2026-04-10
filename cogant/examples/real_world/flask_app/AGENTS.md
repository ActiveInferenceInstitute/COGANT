# Agents — examples/real_world/flask_app

Minimal Flask web application used as an ingest/static analysis fixture.

- `app.py` — Flask app factory; `models.py`, `services.py`, `utils.py` — domain layers
- `config.py` — environment-based configuration
- Tests: `cogant/tests/integration/` uses this fixture for real-world evaluation runs
- Parent coordination: [../AGENTS.md](../AGENTS.md)
