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
    # ---------------------------------------------------------------
    # Package identity
    # ---------------------------------------------------------------
    "{{VERSION}}": "package.version",              # Semantic version string (e.g. "0.5.0")
    "{{COGANT_VERSION}}": "package.version",       # Alias for VERSION; used in prose "cogant v{{...}}"
    "{{PACKAGE_NAME}}": "package.name",            # Canonical distribution name ("cogant")
    "{{PYTHON_MIN}}": "package.python_min",        # Minimum supported CPython (from pyproject ``requires-python``)

    # ---------------------------------------------------------------
    # Testing — counts, coverage, and lint health
    # ---------------------------------------------------------------
    "{{TEST_COUNT}}": "testing.test_count_passing",            # Passing tests (load-bearing figure)
    "{{TEST_COUNT_PASSING}}": "testing.test_count_passing",    # Explicit alias for clarity
    "{{TEST_COUNT_TOTAL}}": "testing.test_count_total",        # Total tests collected
    "{{TEST_COUNT_FAILING}}": "testing.test_count_failing",    # Hard failures (target: 0)
    "{{TEST_COUNT_SKIPPED}}": "testing.test_count_skipped",    # Conditional skips (optional deps)
    "{{TEST_COUNT_XFAILED}}": "testing.test_count_xfailed",    # Expected failures
    "{{TEST_COUNT_XPASSED}}": "testing.test_count_xpassed",    # Unexpected passes
    "{{TEST_FILES_UNIT}}": "testing.test_files_unit",          # Unit test file count
    "{{TEST_FILES_INTEGRATION}}": "testing.test_files_integration",  # Integration test file count
    "{{TEST_FILES_PROPERTY}}": "testing.test_files_property",  # Property-based (hypothesis) files
    "{{TEST_FILES_FUZZ}}": "testing.test_files_fuzz",          # Fuzz-testing harness files
    "{{COVERAGE_PCT}}": "testing.coverage_percent",            # Line coverage % of cogant/ package
    "{{COVERAGE_PERCENT}}": "testing.coverage_percent",        # Spelled-out alias
    "{{MYPY_ERRORS}}": "testing.mypy_strict_errors",           # mypy --strict errors (target: 0)
    "{{MYPY_STRICT_ERRORS}}": "testing.mypy_strict_errors",    # Explicit alias
    "{{RUFF_VIOLATIONS}}": "testing.ruff_violations",          # ruff check violations (target: 0)

    # ---------------------------------------------------------------
    # Codebase — source counts and public surface area
    # ---------------------------------------------------------------
    "{{PYTHON_SOURCE_FILES}}": "codebase.python_source_files", # Number of .py files under cogant/
    "{{PYTHON_LOC}}": "codebase.python_loc",                   # Executable python LOC (not blanks/comments)
    "{{PUBLIC_CLASSES}}": "codebase.public_classes",           # Public class count across cogant/
    "{{PUBLIC_FUNCTIONS}}": "codebase.public_functions",       # Public function/method count
    "{{PUBLIC_MODULES}}": "codebase.public_modules",           # Public module count (no underscore prefix)

    # ---------------------------------------------------------------
    # Pipeline — stages and translation rules
    # ---------------------------------------------------------------
    "{{PIPELINE_STAGES}}": "pipeline.stage_count",     # Library-internal pipeline stage count
    "{{STAGE_COUNT}}": "pipeline.stage_count",         # Alias matching METRICS.yaml key
    "{{TRANSLATION_RULES}}": "pipeline.translation_rules",  # Declarative translation rule count

    # ---------------------------------------------------------------
    # Roundtrip evaluation — tier counts
    # ---------------------------------------------------------------
    "{{ISO_COUNT}}": "evaluation.roundtrip.isomorphic_count",        # Targets in ISOMORPHIC tier
    "{{ISOMORPHIC_COUNT}}": "evaluation.roundtrip.isomorphic_count", # Alias
    "{{APPROX_COUNT}}": "evaluation.roundtrip.approximate_count",    # Targets in APPROXIMATE tier
    "{{APPROXIMATE_COUNT}}": "evaluation.roundtrip.approximate_count",  # Alias
    "{{DIV_COUNT}}": "evaluation.roundtrip.divergent_count",         # Targets in DIVERGENT tier
    "{{DIVERGENT_COUNT}}": "evaluation.roundtrip.divergent_count",   # Alias
    "{{TOTAL_TARGETS}}": "evaluation.roundtrip.total_targets",       # Total roundtrip targets

    # ---------------------------------------------------------------
    # Roundtrip evaluation — epsilon statistics
    # ---------------------------------------------------------------
    "{{MEAN_EPSILON}}": "evaluation.roundtrip.mean_epsilon",      # Mean ε across all targets
    "{{MEDIAN_EPSILON}}": "evaluation.roundtrip.median_epsilon",  # Median ε
    "{{MIN_EPSILON}}": "evaluation.roundtrip.min_epsilon",        # Minimum ε (worst-case target)
    "{{MAX_EPSILON}}": "evaluation.roundtrip.max_epsilon",        # Maximum ε (best-case target)
    "{{THRESHOLD_ISO}}": "evaluation.roundtrip.threshold_isomorphic",        # ε ≥ T_iso = ISOMORPHIC
    "{{THRESHOLD_ISOMORPHIC}}": "evaluation.roundtrip.threshold_isomorphic", # Alias
    "{{THRESHOLD_APPROX}}": "evaluation.roundtrip.threshold_approximate",    # ε ≥ T_approx = APPROXIMATE
    "{{THRESHOLD_APPROXIMATE}}": "evaluation.roundtrip.threshold_approximate",  # Alias

    # ---------------------------------------------------------------
    # Roundtrip evaluation — derived / categorised counts (optional;
    # only emitted if generator populates them)
    # ---------------------------------------------------------------
    "{{ISO_PERCENT}}": "evaluation.roundtrip.isomorphic_percent",    # % of total in ISOMORPHIC tier
    "{{ZOO_FIXTURE_COUNT}}": "evaluation.roundtrip.zoo_fixture_count",  # Shipped "zoo" fixtures
    "{{RW_LIB_COUNT}}": "evaluation.roundtrip.rw_lib_count",         # Real-world library targets
    "{{RW_REPO_COUNT}}": "evaluation.roundtrip.rw_repo_count",       # Real-world repo/app targets
    "{{ROUNDTRIP_NOTE}}": "evaluation.roundtrip.note",               # Short human-readable note
    "{{ROUNDTRIP_DATA_SOURCE}}": "evaluation.roundtrip.data_source", # Path to jsonl results file

    # ---------------------------------------------------------------
    # Semantic role F1 estimates (optional; present if semantic
    # evaluation stage has been run)
    # ---------------------------------------------------------------
    "{{COGANT_MACRO_F1}}": "evaluation.semantic.cogant_macro_f1",   # cogant macro-F1 on role labels
    "{{GPT4_MACRO_F1}}": "evaluation.semantic.gpt4_macro_f1",       # GPT-4 baseline macro-F1

    # ---------------------------------------------------------------
    # Benchmark / performance (derived from benchmark run)
    # ---------------------------------------------------------------
    "{{SUITE_RUNTIME_S}}": "benchmark.suite_runtime_s",              # Full suite wall-clock (s)
    "{{SHIPPED_FIXTURE_COUNT}}": "benchmark.shipped_fixture_count",  # Fixtures shipped with package

    # ---------------------------------------------------------------
    # IR schema counts (node/edge kinds + active-inf roles)
    # ---------------------------------------------------------------
    "{{NODE_KIND_COUNT}}": "ir_schema.node_kind_count",              # Distinct NodeKind enum values
    "{{EDGE_KIND_COUNT}}": "ir_schema.edge_kind_count",              # Distinct EdgeKind enum values
    "{{ACTIVE_INF_ROLE_COUNT}}": "ir_schema.active_inf_role_count",  # Active-inference role labels

    # ---------------------------------------------------------------
    # Literature / bibliography
    # ---------------------------------------------------------------
    "{{BIB_ENTRIES}}": "literature.bibliography_entries",       # Total BibTeX entries in LITERATURE.md
    "{{BIBLIOGRAPHY_ENTRIES}}": "literature.bibliography_entries",  # Alias
    "{{LITERATURE_SOURCE}}": "literature.source",               # Path to LITERATURE.md

    # ---------------------------------------------------------------
    # Rust toolchain (FFI acceleration crates)
    # ---------------------------------------------------------------
    "{{RUST_CRATES}}": "rust.crates_total",    # Rust crate count under cogant/rust/
    "{{RUST_FFI}}": "rust.ffi_available",      # Bool: FFI compiled/available

    # ---------------------------------------------------------------
    # Provenance (top-level METRICS.yaml)
    # ---------------------------------------------------------------
    "{{METRICS_GENERATED_AT}}": "generated_at",                # ISO-8601 generation timestamp
    "{{METRICS_SCHEMA_VERSION}}": "schema_version",            # METRICS.yaml schema version
    "{{METRICS_GIT_SHA}}": "generator_git_sha",                # Git SHA at generation time
    "{{COGANT_VERSION_TOP}}": "cogant_version",                # Top-level cogant_version field
}
