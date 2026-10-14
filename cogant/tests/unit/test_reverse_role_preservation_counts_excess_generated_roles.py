"""Role preservation must see role-bearing definitions the synthesizer over-generates.

The synthesized package's ``.cogant_semantic_targets.json`` manifest names
the generated definitions that carry a role (``update_*`` actions,
``get_*`` observations, ``Factor<N>`` states, policy/constraint/context
stubs) so generated runtime support code is not scored.  The manifest used
to be truncated to the *source* role counts, which made the synthesized role
multiset unable to exceed the original: a package with 11 generated actions
for 7 source ACTION mappings scored a perfect 1.0.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from cogant.reverse.idempotency import (
    _role_multiset_from_mappings,
    _role_preservation_score,
    verify_repo_roundtrip,
)
from cogant.reverse.parser import ReverseGNNModel
from cogant.reverse.planner import plan_package
from cogant.reverse.synthesizer import SEMANTIC_TARGETS_MANIFEST, _semantic_role_targets
from cogant.schemas.semantic import MappingKind, SemanticMapping

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
EVENT_PIPELINE = EXAMPLES / "control_positive" / "event_pipeline"


def _three_action_model() -> ReverseGNNModel:
    return ReverseGNNModel(
        model_name="excess",
        hidden_states=["s_f0"],
        actions=["u_c0", "u_c1", "u_c2"],
        cardinalities={"s_f0": 2},
        B=[[[1.0, 1.0, 1.0], [0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]],
        D=[0.5, 0.5],
    )


def test_manifest_names_every_generated_action_beyond_source_count() -> None:
    plan = plan_package(_three_action_model(), expected_roles={"HIDDEN_STATE": 1, "ACTION": 1})

    targets = _semantic_role_targets(plan)

    assert len(plan.action_methods) == 3
    assert targets["ACTION"] == [node.name for node in plan.action_methods]


def test_excess_generated_actions_lower_role_preservation_score() -> None:
    plan = plan_package(_three_action_model(), expected_roles={"HIDDEN_STATE": 1, "ACTION": 1})
    targets = _semantic_role_targets(plan)
    mappings = {
        f"m{i}": SemanticMapping(
            id=f"m{i}",
            kind=MappingKind.ACTION,
            semantic_label=f"{node.name} - Action",
        )
        for i, node in enumerate(plan.action_methods)
    }

    synthesized = _role_multiset_from_mappings(mappings, semantic_targets=targets)
    score, _vacuous = _role_preservation_score({"ACTION": 1}, synthesized)

    assert synthesized["ACTION"] == 3
    assert score < 1.0


def test_repo_roundtrip_counts_every_generated_action(tmp_path: Path) -> None:
    result = verify_repo_roundtrip(EVENT_PIPELINE, output_dir=tmp_path)

    assert result.package_path is not None
    act_source = (result.package_path / "act.py").read_text(encoding="utf-8")
    generated_actions = re.findall(r"^def (update_\w+)\(", act_source, flags=re.MULTILINE)
    manifest = json.loads(
        (result.package_path / SEMANTIC_TARGETS_MANIFEST).read_text(encoding="utf-8")
    )

    assert manifest["semantic_targets"]["ACTION"] == generated_actions
    assert result.synthesized_roles["ACTION"] == len(generated_actions)
    if len(generated_actions) != result.original_roles.get("ACTION", 0):
        assert result.role_preservation_score < 1.0
