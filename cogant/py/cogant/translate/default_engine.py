"""Default TranslationEngine factory backed by the shipped rule registry."""

from __future__ import annotations

from cogant.translate import rules as rule_mod
from cogant.translate.engine import TranslationEngine

__all__ = ["default_translation_engine"]


def default_translation_engine() -> TranslationEngine:
    """Construct a ``TranslationEngine`` with every concrete rule in ``rules.__all__``."""
    eng = TranslationEngine()
    for name in rule_mod.__all__:
        if name == "TranslationRule":
            continue
        eng.register_rule(getattr(rule_mod, name)())
    return eng
