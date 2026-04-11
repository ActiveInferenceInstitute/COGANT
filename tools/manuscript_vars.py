"""Registry of manuscript template variables and their METRICS.yaml paths.

Usage:
    from tools.manuscript_vars import MANUSCRIPT_VARS
    # MANUSCRIPT_VARS["{{TEST_COUNT}}"] == "testing.test_count_passing"
"""

from __future__ import annotations

import re
from typing import Any

_PLACEHOLDER_INNER = re.compile(r"^\{\{([A-Za-z0-9_]+)\}\}$")


def resolve_path(data: dict[str, Any] | Any, dotpath: str) -> Any:
    """Traverse a nested mapping using dotted path segments."""
    cur: Any = data
    for part in dotpath.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur


def format_value_for_path(path: str, value: Any) -> str:
    """Format a METRICS value for manuscript substitution (aligned with inject tool)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if "epsilon" in path or "threshold_" in path:
            s = f"{value:.4f}"
            return s.rstrip("0").rstrip(".") if "." in s else s
        if "coverage_percent" in path:
            return f"{value:.2f}"
        if "macro_f1" in path or path.endswith("_f1"):
            return f"{value:.2f}"
        if "isomorphic_percent" in path or ("_percent" in path and "coverage" not in path):
            return f"{value:.1f}"
        return f"{value:.1f}"
    return str(value)


def placeholder_to_json_key(placeholder: str) -> str:
    """Map ``{{NAME}}`` -> ``NAME`` for JSON keys."""
    m = _PLACEHOLDER_INNER.match(placeholder.strip())
    if m:
        return m.group(1)
    return placeholder.strip("{}").replace("{", "").replace("}", "")


def build_flat_variables(metrics: dict[str, Any]) -> dict[str, str]:
    """Build ``NAME -> formatted string`` for manuscript_variables.json."""
    out: dict[str, str] = {}
    for placeholder, path in MANUSCRIPT_VARS.items():
        value = resolve_path(metrics, path)
        if value is None:
            continue
        key = placeholder_to_json_key(placeholder)
        out[key] = format_value_for_path(path, value)
    return out


def substitute_text(text: str, metrics: dict[str, Any]) -> tuple[str, list[str]]:
    """Replace every registered ``{{VAR}}`` in *text*; return (new_text, log lines)."""
    substitutions: list[str] = []
    for var, path in MANUSCRIPT_VARS.items():
        value = resolve_path(metrics, path)
        if value is None:
            continue
        formatted = format_value_for_path(path, value)
        if var in text:
            substitutions.append(f"  {var} → {formatted} (from {path})")
            text = text.replace(var, formatted)
    return text, substitutions


MANUSCRIPT_VARS: dict[str, str] = {
    # Package identity
    "{{VERSION}}": "package.version",
    "{{COGANT_VERSION}}": "package.version",
    "{{PYTHON_MIN}}": "package.python_min",

    # Testing
    "{{TEST_COUNT}}": "testing.test_count_passing",
    "{{TEST_COUNT_TOTAL}}": "testing.test_count_total",
    "{{TEST_COUNT_FAILING}}": "testing.test_count_failing",
    "{{COVERAGE_PCT}}": "testing.coverage_percent",
    "{{MYPY_ERRORS}}": "testing.mypy_strict_errors",
    "{{RUFF_VIOLATIONS}}": "testing.ruff_violations",

    # Codebase
    "{{PYTHON_SOURCE_FILES}}": "codebase.python_source_files",
    "{{PYTHON_LOC}}": "codebase.python_loc",
    "{{PUBLIC_CLASSES}}": "codebase.public_classes",
    "{{PUBLIC_FUNCTIONS}}": "codebase.public_functions",

    # Pipeline
    "{{PIPELINE_STAGES}}": "pipeline.stage_count",
    "{{TRANSLATION_RULES}}": "pipeline.translation_rules",

    # Roundtrip evaluation
    "{{ISO_COUNT}}": "evaluation.roundtrip.isomorphic_count",
    "{{APPROX_COUNT}}": "evaluation.roundtrip.approximate_count",
    "{{DIV_COUNT}}": "evaluation.roundtrip.divergent_count",
    "{{TOTAL_TARGETS}}": "evaluation.roundtrip.total_targets",
    "{{MEAN_EPSILON}}": "evaluation.roundtrip.mean_epsilon",
    "{{MEDIAN_EPSILON}}": "evaluation.roundtrip.median_epsilon",
    "{{MIN_EPSILON}}": "evaluation.roundtrip.min_epsilon",
    "{{MAX_EPSILON}}": "evaluation.roundtrip.max_epsilon",
    "{{THRESHOLD_ISO}}": "evaluation.roundtrip.threshold_isomorphic",
    "{{THRESHOLD_APPROX}}": "evaluation.roundtrip.threshold_approximate",

    # Literature
    "{{BIB_ENTRIES}}": "literature.bibliography_entries",

    # Codebase — extended
    "{{PUBLIC_MODULES}}": "codebase.public_modules",

    # Testing — extended counts
    "{{TEST_COUNT_SKIPPED}}": "testing.test_count_skipped",
    "{{TEST_COUNT_XFAILED}}": "testing.test_count_xfailed",
    "{{TEST_COUNT_XPASSED}}": "testing.test_count_xpassed",
    "{{TEST_FILES_UNIT}}": "testing.test_files_unit",
    "{{TEST_FILES_INTEGRATION}}": "testing.test_files_integration",

    # Roundtrip evaluation — derived / categorised counts
    "{{ISO_PERCENT}}": "evaluation.roundtrip.isomorphic_percent",
    "{{ZOO_FIXTURE_COUNT}}": "evaluation.roundtrip.zoo_fixture_count",
    "{{RW_LIB_COUNT}}": "evaluation.roundtrip.rw_lib_count",
    "{{RW_REPO_COUNT}}": "evaluation.roundtrip.rw_repo_count",

    # Benchmark / performance (derived from benchmark run)
    "{{SUITE_RUNTIME_S}}": "benchmark.suite_runtime_s",
    "{{SHIPPED_FIXTURE_COUNT}}": "benchmark.shipped_fixture_count",

    # IR schema counts
    "{{NODE_KIND_COUNT}}": "ir_schema.node_kind_count",
    "{{EDGE_KIND_COUNT}}": "ir_schema.edge_kind_count",
    "{{ACTIVE_INF_ROLE_COUNT}}": "ir_schema.active_inf_role_count",

    # Semantic role F1 estimates
    "{{COGANT_MACRO_F1}}": "evaluation.semantic.cogant_macro_f1",
    "{{GPT4_MACRO_F1}}": "evaluation.semantic.gpt4_macro_f1",

    # Rust
    "{{RUST_CRATES}}": "rust.crates_total",
    "{{RUST_FFI}}": "rust.ffi_available",

    # Provenance (top-level METRICS.yaml)
    "{{METRICS_GENERATED_AT}}": "generated_at",
}
