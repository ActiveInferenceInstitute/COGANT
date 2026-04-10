from pathlib import Path
from typing import Any

from cogant.translate.dsl.schema import KNOWN_CONDITION_KEYS as KNOWN_CONDITION_KEYS
from cogant.translate.dsl.schema import DSLCondition as DSLCondition
from cogant.translate.dsl.schema import DSLRule as DSLRule
from cogant.translate.dsl.schema import DSLRuleSet as DSLRuleSet

def load_rules_from_yaml(path: Path | str) -> DSLRuleSet: ...
def load_rules_from_dict(data: dict[str, Any]) -> DSLRuleSet: ...
