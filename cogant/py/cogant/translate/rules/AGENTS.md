# Agents — py/cogant/translate/rules

## Owner

Semantic Lead

## Responsibilities

Family-organized `TranslationRule` implementations: structural, behavioral, control, semantic, resilience modules re-exported from this package so `from cogant.translate.rules import …` stays stable.

## Coordination

Rules are registered and run by `translate/engine.py`; see parent [../AGENTS.md](../AGENTS.md) for engine behavior and fixpoint iteration.

## Files

- `structural.py`, `behavioral.py`, `control.py`, `semantic.py`, `resilience.py` — rule classes.
- `__init__.py` — umbrella re-exports and `TranslationRule` alias.
