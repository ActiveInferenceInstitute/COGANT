"""Temporary placeholder — real implementation arrives in the next step."""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RoundtripResult:
    is_isomorphic: bool = False
    role_match_score: float = 0.0
    original_roles: Dict[str, int] = field(default_factory=dict)
    synthesized_roles: Dict[str, int] = field(default_factory=dict)
    errors: list = field(default_factory=list)


def verify_roundtrip(*args, **kwargs) -> RoundtripResult:
    return RoundtripResult()
