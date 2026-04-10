"""Load DSL rules from YAML files or plain dicts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from cogant.translate.dsl.schema import (
    DSLCondition,
    DSLRule,
    DSLRuleSet,
    KNOWN_CONDITION_KEYS,
)


def load_rules_from_yaml(path: Path | str) -> DSLRuleSet:
    """Load a DSL rule-set from a YAML file.

    Requires ``PyYAML`` (``import yaml``).  If the library is not
    installed a helpful ``ImportError`` is raised.

    Args:
        path: Filesystem path to the YAML file.

    Returns:
        Parsed ``DSLRuleSet``.

    Raises:
        ImportError: If PyYAML is not available.
        FileNotFoundError: If *path* does not exist.
        ValueError: On schema violations (unknown condition keys, etc.).
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required to load YAML rule files. "
            "Install it with: pip install pyyaml"
        ) from exc

    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    return load_rules_from_dict(data)


def load_rules_from_dict(data: Dict[str, Any]) -> DSLRuleSet:
    """Load a DSL rule-set from an already-parsed dict.

    This is the preferred entry-point for tests (avoids YAML
    dependency) and for JSON-based rule files.

    Args:
        data: Dict with a ``rules`` key containing a list of rule dicts.

    Returns:
        Parsed ``DSLRuleSet``.

    Raises:
        ValueError: On schema violations (unknown condition keys, missing
            required fields, etc.).
    """
    raw_rules = data.get("rules", [])
    rules: list[DSLRule] = []

    for idx, raw in enumerate(raw_rules):
        conditions = _parse_conditions(raw.get("conditions", []), rule_index=idx)
        rule = DSLRule(
            name=raw["name"],
            role=raw["role"],
            confidence=float(raw["confidence"]),
            conditions=conditions,
            description=raw.get("description"),
        )
        rules.append(rule)

    return DSLRuleSet(rules=rules)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _parse_conditions(
    raw_conditions: list[Dict[str, Any]],
    rule_index: int,
) -> list[DSLCondition]:
    """Parse and validate a list of raw condition dicts."""
    result: list[DSLCondition] = []
    for cond_dict in raw_conditions:
        unknown = set(cond_dict.keys()) - KNOWN_CONDITION_KEYS
        if unknown:
            raise ValueError(
                f"Unknown condition key(s) {unknown} in rule index {rule_index}. "
                f"Allowed keys: {sorted(KNOWN_CONDITION_KEYS)}"
            )
        result.append(
            DSLCondition(
                node_kind=cond_dict.get("node_kind"),
                name_pattern=cond_dict.get("name_pattern"),
                has_method=cond_dict.get("has_method"),
                edge_type=cond_dict.get("edge_type"),
            )
        )
    return result
