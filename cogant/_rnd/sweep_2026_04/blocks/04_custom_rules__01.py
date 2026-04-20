# py/cogant/translate/__init__.py

from cogant.translate.rules.semantic import (
    ObservationRule,
    ActionRule,
    PolicyRule,
    PreferenceRule,
    ContextRule,
    ReadOnlyCacheRule,  # <-- add the import
)


def register_default_rules(engine: "TranslationEngine") -> None:
    engine.register_rule(ObservationRule())
    engine.register_rule(ActionRule())
    engine.register_rule(PolicyRule())
    engine.register_rule(PreferenceRule())
    engine.register_rule(ContextRule())
    engine.register_rule(ReadOnlyCacheRule())  # <-- and register it
    # ... other families ...
