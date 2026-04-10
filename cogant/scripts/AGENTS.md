# Agents — scripts/

## Owner

Runtime Lead (thin orchestrators)

## Responsibilities

Repository-level helper scripts that are not part of `cogant` package imports. Currently includes demonstration or analysis drivers (for example empirical claim demos).

## Coordination

Business logic stays in `py/cogant/`; scripts coordinate only. Run from repository root with `uv run python cogant/scripts/<name>.py` as documented per script.

## Files

- `empirical_claim_demo.py` — empirical claim demonstration driver.
