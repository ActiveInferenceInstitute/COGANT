"""Unit tests for ``tools/manuscript_vars.py`` and ``tools/inject_manuscript_vars.py``.

These cover the small but load-bearing helpers used by the manuscript
substitution pipeline:

* :func:`resolve_path` — nested-dict lookups, including the negative cases.
* :func:`format_value_for_path` — precision rules for epsilons / coverage /
  F1 / percents / ints / bools / None.
* :func:`build_flat_variables` — the exact shape of
  ``output/data/manuscript_variables.json``.
* :func:`substitute_text` — the workhorse that rewrites a Markdown blob.
* :func:`find_unresolved_placeholders` — strict-mode guard used by both the
  CLI injector and ``scripts/z_generate_manuscript_variables.py``.

All tests are data-driven and mock-free per the repo's no-mocks policy.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_STAGING_ROOT = Path(__file__).resolve().parents[3]
_TOOLS_DIR = _STAGING_ROOT / "tools"


def _load_manuscript_vars():
    script = _TOOLS_DIR / "manuscript_vars.py"
    assert script.is_file(), f"missing {script}"
    spec = importlib.util.spec_from_file_location("manuscript_vars_under_test", script)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mv():
    return _load_manuscript_vars()


@pytest.fixture
def sample_metrics() -> dict:
    return {
        "schema_version": "1.0",
        "package": {"name": "cogant", "version": "0.5.0", "python_min": "3.11"},
        "testing": {
            "test_count_passing": 6915,
            "test_count_total": 7027,
            "coverage_percent": 90.44,
            "mypy_strict_errors": 0,
            "ruff_violations": 0,
        },
        "pipeline": {"stage_count": 10, "translation_rules": 19},
        "evaluation": {
            "roundtrip": {
                "mean_epsilon": 0.8092,
                "threshold_isomorphic": 0.8,
                "isomorphic_percent": 60.9,
            },
            "semantic": {"cogant_macro_f1": 0.73},
        },
        "rust": {"ffi_available": True},
    }


# ---------------------------------------------------------------------------
# resolve_path
# ---------------------------------------------------------------------------


def test_resolve_path_single_segment(mv, sample_metrics):
    assert mv.resolve_path(sample_metrics, "schema_version") == "1.0"


def test_resolve_path_nested(mv, sample_metrics):
    assert mv.resolve_path(sample_metrics, "testing.test_count_passing") == 6915
    assert mv.resolve_path(sample_metrics, "evaluation.roundtrip.mean_epsilon") == 0.8092


def test_resolve_path_missing_key(mv, sample_metrics):
    assert mv.resolve_path(sample_metrics, "testing.not_a_field") is None
    assert mv.resolve_path(sample_metrics, "does.not.exist") is None


def test_resolve_path_through_non_mapping(mv, sample_metrics):
    # "version" resolves to a string; descending further should return None
    # rather than crash with an AttributeError.
    assert mv.resolve_path(sample_metrics, "package.version.extra") is None


def test_resolve_path_empty_dotpath_returns_data(mv, sample_metrics):
    assert mv.resolve_path(sample_metrics, "") is sample_metrics


# ---------------------------------------------------------------------------
# format_value_for_path
# ---------------------------------------------------------------------------


def test_format_value_none_returns_empty_string(mv):
    assert mv.format_value_for_path("anything", None) == ""


def test_load_bearing_null_is_left_unresolved_not_blanked(mv):
    """A present-but-null load-bearing metric must NOT be silently substituted
    with an empty string; the token stays unresolved so --strict can flag it."""
    metrics = {"testing": {"coverage_percent": None}}
    text = "Coverage is {{COVERAGE_PCT}}%."
    out, _subs = mv.substitute_text(text, metrics)
    assert "{{COVERAGE_PCT}}" in out
    assert mv.find_unresolved_placeholders(out) == ["{{COVERAGE_PCT}}"]


def test_intentionally_nullable_score_still_renders_na(mv):
    """A null native role-preservation score is intentional and renders N/A."""
    metrics = {"evaluation": {"roundtrip": {"mean_role_preservation_score": None}}}
    text = "Mean score: {{MEAN_ROLE_PRESERVATION_SCORE}}."
    out, _subs = mv.substitute_text(text, metrics)
    assert out == "Mean score: N/A."
    assert mv.find_unresolved_placeholders(out) == []


def test_format_value_int_round_trips(mv):
    assert mv.format_value_for_path("testing.test_count_passing", 6915) == "6915"


def test_format_value_bool_stringifies(mv):
    assert mv.format_value_for_path("rust.ffi_available", True) == "True"


def test_format_value_coverage_two_decimals(mv):
    assert mv.format_value_for_path("testing.coverage_percent", 90.44) == "90.44"


def test_format_value_epsilon_strips_trailing_zeros(mv):
    # "epsilon" path → 4dp then strip trailing zeros
    assert mv.format_value_for_path("evaluation.roundtrip.mean_epsilon", 0.8) == "0.8"
    assert mv.format_value_for_path("evaluation.roundtrip.mean_epsilon", 0.8092) == "0.8092"


def test_format_value_threshold_strips_trailing_zeros(mv):
    assert mv.format_value_for_path("threshold_isomorphic", 0.8000) == "0.8"


def test_format_value_macro_f1_two_decimals(mv):
    assert mv.format_value_for_path("evaluation.semantic.cogant_macro_f1", 0.73) == "0.73"


def test_format_value_isomorphic_percent_one_decimal(mv):
    assert mv.format_value_for_path("evaluation.roundtrip.isomorphic_percent", 60.9) == "60.9"


# ---------------------------------------------------------------------------
# build_flat_variables
# ---------------------------------------------------------------------------


def test_build_flat_variables_populates_known_keys(mv, sample_metrics):
    flat = mv.build_flat_variables(sample_metrics)
    # Placeholders are stripped of their braces.
    assert flat["TEST_COUNT"] == "6915"
    assert flat["TEST_COUNT_PASSING"] == "6915"
    assert flat["COVERAGE_PCT"] == "90.44"
    assert flat["VERSION"] == "0.5.0"
    assert flat["STAGE_COUNT"] == "10"
    assert flat["TRANSLATION_RULES"] == "19"


def test_build_flat_variables_skips_missing_entries(mv, sample_metrics):
    flat = mv.build_flat_variables(sample_metrics)
    # No zoo fixture count was supplied — it must not appear with an empty value.
    assert "ZOO_FIXTURE_COUNT" not in flat


# ---------------------------------------------------------------------------
# substitute_text
# ---------------------------------------------------------------------------


def test_substitute_text_replaces_registered_placeholder(mv, sample_metrics):
    text = "COGANT has {{TEST_COUNT}} passing tests at {{COVERAGE_PCT}}% coverage."
    new_text, subs = mv.substitute_text(text, sample_metrics)
    assert "{{TEST_COUNT}}" not in new_text
    assert "6915" in new_text
    assert "90.44" in new_text
    assert len(subs) == 2  # two substitutions were logged


def test_substitute_text_leaves_unknown_token_alone(mv, sample_metrics):
    text = "Unknown placeholder: {{NOT_A_REAL_VAR}}"
    new_text, subs = mv.substitute_text(text, sample_metrics)
    assert new_text == text
    assert subs == []


def test_substitute_text_leaves_registered_but_missing_path_alone(mv):
    # TEST_COUNT is registered, but metrics dict is empty → no substitution.
    text = "{{TEST_COUNT}} tests"
    new_text, subs = mv.substitute_text(text, {})
    assert new_text == text
    assert subs == []


# ---------------------------------------------------------------------------
# find_unresolved_placeholders
# ---------------------------------------------------------------------------


def test_find_unresolved_placeholders_empty_for_clean_text(mv):
    assert mv.find_unresolved_placeholders("no placeholders here") == []


def test_find_unresolved_placeholders_reports_each_unique_token(mv):
    text = "{{ALPHA}} and {{BETA}} and {{ALPHA}} again"
    got = mv.find_unresolved_placeholders(text)
    assert got == ["{{ALPHA}}", "{{BETA}}"]


def test_find_unresolved_placeholders_after_partial_substitution(mv, sample_metrics):
    text = "{{TEST_COUNT}} / {{NOT_REGISTERED}}"
    new_text, _ = mv.substitute_text(text, sample_metrics)
    remaining = mv.find_unresolved_placeholders(new_text)
    assert remaining == ["{{NOT_REGISTERED}}"]


# ---------------------------------------------------------------------------
# Cross-check: every registered placeholder in MANUSCRIPT_VARS must be a
# proper ``{{IDENT}}`` token.
# ---------------------------------------------------------------------------


def test_every_registered_placeholder_has_valid_syntax(mv):
    import re

    pat = re.compile(r"^\{\{[A-Z][A-Z0-9_]*\}\}$")
    for placeholder in mv.MANUSCRIPT_VARS:
        assert pat.match(placeholder), f"malformed placeholder: {placeholder!r}"


def test_every_registered_path_is_non_empty_string(mv):
    for placeholder, path in mv.MANUSCRIPT_VARS.items():
        assert isinstance(path, str) and path, f"empty path for {placeholder!r}"
        # Must contain only identifier / dot characters.
        assert all(part.replace("_", "").isalnum() for part in path.split(".")), (
            f"invalid dotted path for {placeholder!r}: {path!r}"
        )
