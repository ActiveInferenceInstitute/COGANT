"""Normalization module for converting language-specific facts into canonical form."""

from cogant.normalize.canonical import CanonicalNormalizer, LanguageFact, NormalizedFact
from cogant.normalize.identities import IdentityRecord, IdentityResolver

__all__ = [
    "CanonicalNormalizer",
    "LanguageFact",
    "NormalizedFact",
    "IdentityResolver",
    "IdentityRecord",
]
