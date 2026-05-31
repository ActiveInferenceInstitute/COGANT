from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from regenerate_ablation import compute_ablation


def test_compute_ablation_calculator_fixture_is_deterministic() -> None:
    result = compute_ablation([("control_positive", "calculator")])
    assert set(result) == {"rule_family", "by_mapping_kind", "fixpoint", "matrix_fallback"}

    calculator_rule_family = result["rule_family"]["calculator"]
    baseline_total = calculator_rule_family["baseline_mappings_total"]
    assert baseline_total == 11
    assert calculator_rule_family["baseline_by_mapping_kind"]["HIDDEN_STATE"] == 1
    assert calculator_rule_family["baseline_by_mapping_kind"]["OBSERVATION"] > 0
    for family in ("structural", "behavioral", "control", "semantic", "resilience"):
        delta = calculator_rule_family[f"{family}_delta"]
        assert isinstance(delta, int)
        assert 0 <= delta <= baseline_total
        assert family in result["by_mapping_kind"]["calculator"]

    calculator_fixpoint = result["fixpoint"]["calculator"]
    assert calculator_fixpoint["k1"] == calculator_fixpoint["k2"] == calculator_fixpoint["k5"]
    assert calculator_fixpoint["k10"] == 11
    assert calculator_fixpoint["k1"] == calculator_fixpoint["k10"]

    calculator_matrix = result["matrix_fallback"]["calculator"]
    assert calculator_matrix["a_cols_uniform"] == 1
    assert calculator_matrix["a_cols_total"] == 1
    assert calculator_matrix["b_actions_identity"] == 6
    assert calculator_matrix["b_actions_total"] == 6
    assert calculator_matrix["c_entries_zero"] == 3
    assert calculator_matrix["d_uniform"] is True

    result_two = compute_ablation([("control_positive", "calculator")])
    assert result == result_two


def test_compute_ablation_zoo01_and_mapping_kind_decomposition() -> None:
    """The supplement's zoo/01 row is measured, not hand reconstructed."""
    result = compute_ablation([("zoo", "01_simple_state")])
    zoo_rule_family = result["rule_family"]["01_simple_state"]
    assert zoo_rule_family["baseline_mappings_total"] == 4
    assert zoo_rule_family["baseline_by_mapping_kind"] == {
        "ACTION": 2,
        "HIDDEN_STATE": 1,
        "OBSERVATION": 1,
    }

    by_kind = result["by_mapping_kind"]["01_simple_state"]
    assert by_kind["structural"]["HIDDEN_STATE"] == 1
    assert by_kind["semantic"]["OBSERVATION"] >= 0
    assert by_kind["semantic"]["ACTION"] >= 0
    assert by_kind["control"] == {
        "ACTION": 0,
        "HIDDEN_STATE": 0,
        "OBSERVATION": 0,
    }


def test_rule_filter_positive_control_harness_bites() -> None:
    """Positive control: prove the ablation genuinely restricts the rule
    set (so a measured delta of 0 is a real finding, not a no-op filter
    bug). Keeping only the structural family must yield far fewer mappings
    than the full baseline, and ablating the semantic family must remove a
    large, sign-correct number of mappings on the largest fixture."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cogant" / "py"))
    from cogant.api.bundle import Bundle
    from cogant.api.orchestration import (
        _default_translation_engine,
        run_graph,
        run_ingest,
        run_normalize,
        run_static,
    )

    from regenerate_ablation import RULE_FAMILIES

    fixture = str(
        Path(__file__).resolve().parent.parent
        / "cogant"
        / "examples"
        / "real_world"
        / "flask_app"
    )
    bundle = Bundle(target=fixture)
    run_ingest(fixture, bundle)
    run_static(bundle)
    run_normalize(bundle)
    run_graph(bundle, fixture)
    graph = bundle.artifacts["_program_graph"]

    engine = _default_translation_engine()
    baseline_total = len(engine.translate(graph))
    assert baseline_total > 0

    structural = RULE_FAMILIES["structural"]
    only_structural = engine.translate(
        graph, rule_filter=[r.name for r in engine.rules if r.name in structural]
    )
    # Filter genuinely restricts: a single family yields far fewer mappings.
    assert 0 < len(only_structural) < baseline_total

    kept_no_semantic = [
        r.name for r in engine.rules if r.name not in RULE_FAMILIES["semantic"]
    ]
    semantic_delta = baseline_total - len(engine.translate(graph, rule_filter=kept_no_semantic))
    # Ablating the dominant family removes a large, sign-correct number.
    assert semantic_delta > 0
