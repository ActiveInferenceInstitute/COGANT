# Agents — py/cogant/translate/dsl

## Owner

Semantic Lead

## Responsibilities

YAML (and dict) rule DSL: load `DSLRuleSet`, validate `DSLRule` / `DSLCondition`, compile to `CompiledRule` for injection into the translation engine without new Python modules.

## Coordination

Extends `translate/engine.py`; compiled rules must match `TranslationRule` contracts.

## Files

- `schema.py` — `DSLCondition`, `DSLRule`, `DSLRuleSet`.
- `loader.py` — `load_rules_from_yaml`, `load_rules_from_dict`.
- `compiler.py` — `compile_ruleset`, `CompiledRule`.
- `__init__.py` — public exports.
