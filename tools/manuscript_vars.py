"""Registry of manuscript template variables and their METRICS.yaml paths.

This module is the authoritative mapping from ``{{PLACEHOLDER}}`` tokens used
in ``manuscript/*.md`` to dotted paths inside ``cogant/evaluation/METRICS.yaml``.
It also provides the shared helpers used by every downstream consumer:

* :func:`resolve_path` — walk a nested mapping by dotted path.
* :func:`format_value_for_path` — render a metric value as the exact string
  that should appear in prose (precision rules live here so every consumer
  agrees on how ``0.86`` becomes ``"86"`` vs ``"86.0"`` vs ``"0.86"``).
* :func:`build_flat_variables` — emit ``{NAME: formatted_str}`` for
  ``output/data/manuscript_variables.json`` (consumed by ``scripts/
  z_generate_manuscript_variables.py``).
* :func:`substitute_text` — replace every registered placeholder in a text
  blob (the workhorse used by both the injector and the generator).

Usage::

    from tools.manuscript_vars import MANUSCRIPT_VARS, substitute_text
    assert MANUSCRIPT_VARS["{{TEST_COUNT}}"] == "testing.test_count_passing"

This module has **no side effects** and performs no I/O — it is safe to import
from unit tests. The callers are responsible for reading ``METRICS.yaml``.
"""

from __future__ import annotations

import re
from typing import Any

_PLACEHOLDER_INNER = re.compile(r"^\{\{([A-Za-z0-9_]+)\}\}$")

# Matches any ``{{IDENT}}`` token (used by strict unresolved-placeholder checks).
PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")
_MISSING = object()


def _resolve_path_raw(data: dict[str, Any] | Any, dotpath: str) -> Any:
    """Traverse a dotted path, preserving present-but-null values."""
    if not dotpath:
        return data
    cur: Any = data
    for part in dotpath.split("."):
        if not isinstance(cur, dict):
            return _MISSING
        if part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


def resolve_path(data: dict[str, Any] | Any, dotpath: str) -> Any:
    """Traverse a nested mapping using dotted path segments.

    Returns ``None`` if any segment is missing, if a non-mapping is hit before
    the final segment, or if the final value is literally ``None``. Accepts an
    empty dotpath (returns *data* unchanged — useful for corner cases).
    """
    value = _resolve_path_raw(data, dotpath)
    return None if value is _MISSING else value


def format_value_for_path(path: str, value: Any) -> str:
    """Format a METRICS value for manuscript substitution (aligned with inject tool)."""
    if value is None:
        if "role_preservation_score" in path:
            return "N/A"
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if "epsilon" in path or "role_preservation_score" in path or "threshold_" in path:
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
        value = _resolve_path_raw(metrics, path)
        if value is _MISSING:
            continue
        key = placeholder_to_json_key(placeholder)
        out[key] = format_value_for_path(path, value)
    return out


def substitute_text(text: str, metrics: dict[str, Any]) -> tuple[str, list[str]]:
    """Replace every registered ``{{VAR}}`` in *text*; return (new_text, log lines).

    Only tokens that appear in :data:`MANUSCRIPT_VARS` AND resolve to a
    non-``None`` value in *metrics* are substituted. Unknown tokens and
    tokens whose path is missing from *metrics* are left untouched so that
    :func:`find_unresolved_placeholders` can flag them for the caller.
    """
    substitutions: list[str] = []
    for var, path in MANUSCRIPT_VARS.items():
        value = _resolve_path_raw(metrics, path)
        if value is _MISSING:
            continue
        formatted = format_value_for_path(path, value)
        if var in text:
            substitutions.append(f"  {var} → {formatted} (from {path})")
            text = text.replace(var, formatted)
    return text, substitutions


def find_unresolved_placeholders(text: str) -> list[str]:
    """Return any ``{{IDENT}}`` tokens still present in *text*, de-duplicated.

    Call after :func:`substitute_text` to detect placeholders that were not
    resolved — typically because they aren't registered in
    :data:`MANUSCRIPT_VARS`, or because the corresponding METRICS.yaml entry
    is missing. Strict CLI modes should treat a non-empty return value as a
    hard error.
    """
    seen: list[str] = []
    for match in PLACEHOLDER_RE.finditer(text):
        tok = "{{" + match.group(1) + "}}"
        if tok not in seen:
            seen.append(tok)
    return seen


MANUSCRIPT_VARS: dict[str, str] = {
    # ---------------------------------------------------------------
    # Package identity
    # ---------------------------------------------------------------
    "{{VERSION}}": "package.version",  # Semantic version string (e.g. "0.5.0")
    "{{COGANT_VERSION}}": "package.version",  # Alias for VERSION; used in prose "cogant v{{...}}"
    "{{PACKAGE_NAME}}": "package.name",  # Canonical distribution name ("cogant")
    "{{PYTHON_MIN}}": "package.python_min",  # Minimum supported CPython (from pyproject ``requires-python``)
    # ---------------------------------------------------------------
    # Testing — counts, coverage, and lint health
    # ---------------------------------------------------------------
    "{{TEST_COUNT}}": "testing.test_count_passing",  # Passing tests (load-bearing figure)
    "{{TEST_COUNT_PASSING}}": "testing.test_count_passing",  # Explicit alias for clarity
    "{{TEST_COUNT_TOTAL}}": "testing.test_count_total",  # Total tests collected
    "{{TEST_COUNT_FAILING}}": "testing.test_count_failing",  # Hard failures (target: 0)
    "{{TEST_COUNT_SKIPPED}}": "testing.test_count_skipped",  # Conditional skips (optional deps)
    "{{TEST_COUNT_XFAILED}}": "testing.test_count_xfailed",  # Expected failures
    "{{TEST_COUNT_XPASSED}}": "testing.test_count_xpassed",  # Unexpected passes
    "{{TEST_FILES_UNIT}}": "testing.test_files_unit",  # Unit test file count
    "{{TEST_FILES_INTEGRATION}}": "testing.test_files_integration",  # Integration test file count
    "{{TEST_FILES_PROPERTY}}": "testing.test_files_property",  # Property-based (hypothesis) files
    "{{TEST_FILES_FUZZ}}": "testing.test_files_fuzz",  # Fuzz-testing harness files
    "{{COVERAGE_PCT}}": "testing.coverage_percent",  # Line coverage % of cogant/ package
    "{{COVERAGE_PERCENT}}": "testing.coverage_percent",  # Spelled-out alias
    "{{MYPY_ERRORS}}": "testing.mypy_strict_errors",  # mypy --strict errors (target: 0)
    "{{MYPY_STRICT_ERRORS}}": "testing.mypy_strict_errors",  # Explicit alias
    "{{RUFF_VIOLATIONS}}": "testing.ruff_violations",  # ruff check violations (target: 0)
    # ---------------------------------------------------------------
    # Codebase — source counts and public surface area
    # ---------------------------------------------------------------
    "{{PYTHON_SOURCE_FILES}}": "codebase.python_source_files",  # Number of .py files under cogant/
    "{{PYTHON_LOC}}": "codebase.python_loc",  # Executable python LOC (not blanks/comments)
    "{{PUBLIC_CLASSES}}": "codebase.public_classes",  # Public class count across cogant/
    "{{PUBLIC_FUNCTIONS}}": "codebase.public_functions",  # Public function/method count
    "{{PUBLIC_MODULES}}": "codebase.public_modules",  # Public module count (no underscore prefix)
    # ---------------------------------------------------------------
    # Pipeline — stages and translation rules
    # ---------------------------------------------------------------
    "{{PIPELINE_STAGES}}": "pipeline.stage_count",  # Library-internal pipeline stage count
    "{{STAGE_COUNT}}": "pipeline.stage_count",  # Alias matching METRICS.yaml key
    "{{TRANSLATION_RULES}}": "pipeline.translation_rules",  # Declarative translation rule count
    # ---------------------------------------------------------------
    # Roundtrip evaluation — status counts
    # ---------------------------------------------------------------
    "{{STRICT_ISOMORPHISM_COUNT}}": "evaluation.roundtrip.strict_isomorphism_count",  # Strict invariant tier
    "{{STRUCTURAL_ISOMORPHISM_COUNT}}": "evaluation.roundtrip.strict_isomorphism_count",  # Alias
    "{{ROLE_PRESERVED_COUNT}}": "evaluation.roundtrip.role_preserved_count",  # Role-preserved tier
    "{{DRIFT_COUNT}}": "evaluation.roundtrip.drift_count",  # Completed but role score below threshold
    "{{FAILED_COUNT}}": "evaluation.roundtrip.failed_count",  # Failed roundtrips
    "{{STALE_LEGACY_COUNT}}": "evaluation.roundtrip.stale_legacy_count",  # Legacy rows outside v0.6 counts
    "{{ISO_COUNT}}": "evaluation.roundtrip.strict_isomorphism_count",  # Legacy placeholder: strict structural tier
    "{{ISOMORPHIC_COUNT}}": "evaluation.roundtrip.strict_isomorphism_count",  # Legacy alias
    "{{APPROX_COUNT}}": "evaluation.roundtrip.drift_count",  # Legacy placeholder: drift count
    "{{APPROXIMATE_COUNT}}": "evaluation.roundtrip.drift_count",  # Legacy alias
    "{{DIV_COUNT}}": "evaluation.roundtrip.failed_count",  # Legacy placeholder: failed count
    "{{DIVERGENT_COUNT}}": "evaluation.roundtrip.failed_count",  # Legacy alias
    "{{TOTAL_TARGETS}}": "evaluation.roundtrip.total_targets",  # Total roundtrip targets
    # ---------------------------------------------------------------
    # Roundtrip evaluation — role-preservation statistics
    # ---------------------------------------------------------------
    "{{MEAN_ROLE_PRESERVATION_SCORE}}": "evaluation.roundtrip.mean_role_preservation_score",  # Mean role score
    "{{MEDIAN_ROLE_PRESERVATION_SCORE}}": "evaluation.roundtrip.median_role_preservation_score",  # Median role score
    "{{MIN_ROLE_PRESERVATION_SCORE}}": "evaluation.roundtrip.min_role_preservation_score",  # Minimum role score
    "{{MAX_ROLE_PRESERVATION_SCORE}}": "evaluation.roundtrip.max_role_preservation_score",  # Maximum role score
    "{{ROLE_PRESERVATION_SCORE_SOURCE}}": (
        "evaluation.roundtrip.role_preservation_score_source"
    ),  # Aggregate score provenance
    "{{THRESHOLD_ROLE_PRESERVED}}": "evaluation.roundtrip.threshold_role_preserved",  # s_role threshold
    "{{THRESHOLD_DRIFT}}": "evaluation.roundtrip.threshold_drift",  # lower status threshold
    "{{MEAN_EPSILON}}": "evaluation.roundtrip.mean_role_preservation_score",  # Legacy alias
    "{{MEDIAN_EPSILON}}": "evaluation.roundtrip.median_role_preservation_score",  # Legacy alias
    "{{MIN_EPSILON}}": "evaluation.roundtrip.min_role_preservation_score",  # Legacy alias
    "{{MAX_EPSILON}}": "evaluation.roundtrip.max_role_preservation_score",  # Legacy alias
    "{{THRESHOLD_ISO}}": "evaluation.roundtrip.threshold_role_preserved",  # Legacy alias
    "{{THRESHOLD_ISOMORPHIC}}": "evaluation.roundtrip.threshold_role_preserved",  # Legacy alias
    "{{THRESHOLD_APPROX}}": "evaluation.roundtrip.threshold_drift",  # Legacy alias
    "{{THRESHOLD_APPROXIMATE}}": "evaluation.roundtrip.threshold_drift",  # Legacy alias
    # ---------------------------------------------------------------
    # Roundtrip evaluation — derived / categorised counts (optional;
    # only emitted if generator populates them)
    # ---------------------------------------------------------------
    "{{ISO_PERCENT}}": "evaluation.roundtrip.isomorphic_percent",  # % of total in ISOMORPHIC tier
    "{{ZOO_FIXTURE_COUNT}}": "evaluation.roundtrip.zoo_fixture_count",  # Shipped "zoo" fixtures
    "{{RW_LIB_COUNT}}": "evaluation.roundtrip.rw_lib_count",  # Real-world library targets
    "{{RW_REPO_COUNT}}": "evaluation.roundtrip.rw_repo_count",  # Real-world repo/app targets
    "{{ROUNDTRIP_NOTE}}": "evaluation.roundtrip.note",  # Short human-readable note
    "{{ROUNDTRIP_DATA_SOURCE}}": "evaluation.roundtrip.data_source",  # Path to jsonl results file
    # ---------------------------------------------------------------
    # Semantic role F1 estimates (optional; present if semantic
    # evaluation stage has been run)
    # ---------------------------------------------------------------
    "{{COGANT_MACRO_F1}}": "evaluation.semantic.cogant_macro_f1",  # cogant macro-F1 on role labels
    "{{GPT4_MACRO_F1}}": "evaluation.semantic.gpt4_macro_f1",  # GPT-4 baseline macro-F1
    # ---------------------------------------------------------------
    # Benchmark / performance (derived from benchmark run)
    # ---------------------------------------------------------------
    "{{SUITE_RUNTIME_S}}": "benchmark.suite_runtime_s",  # Full suite wall-clock (s)
    "{{SHIPPED_FIXTURE_COUNT}}": "benchmark.shipped_fixture_count",  # Fixtures shipped with package
    "{{BENCHMARK_PYTHON_VERSION}}": "benchmark.benchmark_python_version",  # CPython patch version used in benchmark run
    "{{BENCHMARK_SUITE_FILE}}": "benchmark.benchmark_suite_file",  # Benchmark results markdown filename
    "{{BENCHMARK_OS}}": "benchmark.benchmark_os",  # OS/arch used for benchmark run
    # ---------------------------------------------------------------
    # IR schema counts (node/edge kinds + active-inf roles)
    # ---------------------------------------------------------------
    "{{NODE_KIND_COUNT}}": "ir_schema.node_kind_count",  # Distinct NodeKind enum values
    "{{EDGE_KIND_COUNT}}": "ir_schema.edge_kind_count",  # Distinct EdgeKind enum values
    "{{ACTIVE_INF_ROLE_COUNT}}": "ir_schema.active_inf_role_count",  # Active-inference role labels
    # ---------------------------------------------------------------
    # Ablation study (09_ablation.md)
    # ---------------------------------------------------------------
    "{{ABLATION_CALCULATOR_K10}}": "ablation.fixpoint.calculator.k10",
    "{{ABLATION_EVENT_PIPELINE_K10}}": "ablation.fixpoint.event_pipeline.k10",
    "{{ABLATION_FLASK_MINI_K10}}": "ablation.fixpoint.flask_mini.k10",
    "{{ABLATION_FLASK_APP_K10}}": "ablation.fixpoint.flask_app.k10",
    "{{ABLATION_REQUESTS_LIB_K10}}": "ablation.fixpoint.requests_lib.k10",
    "{{ABLATION_JSON_STDLIB_K10}}": "ablation.fixpoint.json_stdlib.k10",
    "{{ABLATION_CALCULATOR_A_ROWS_UNIFORM}}": "ablation.matrix_fallback.calculator.a_rows_uniform",
    "{{ABLATION_CALCULATOR_A_ROWS_TOTAL}}": "ablation.matrix_fallback.calculator.a_rows_total",
    "{{ABLATION_EVENT_PIPELINE_A_ROWS_UNIFORM}}": "ablation.matrix_fallback.event_pipeline.a_rows_uniform",
    "{{ABLATION_EVENT_PIPELINE_A_ROWS_TOTAL}}": "ablation.matrix_fallback.event_pipeline.a_rows_total",
    "{{ABLATION_FLASK_MINI_A_ROWS_UNIFORM}}": "ablation.matrix_fallback.flask_mini.a_rows_uniform",
    "{{ABLATION_FLASK_MINI_A_ROWS_TOTAL}}": "ablation.matrix_fallback.flask_mini.a_rows_total",
    "{{ABLATION_FLASK_APP_A_ROWS_UNIFORM}}": "ablation.matrix_fallback.flask_app.a_rows_uniform",
    "{{ABLATION_FLASK_APP_A_ROWS_TOTAL}}": "ablation.matrix_fallback.flask_app.a_rows_total",
    "{{ABLATION_JSON_STDLIB_A_ROWS_UNIFORM}}": "ablation.matrix_fallback.json_stdlib.a_rows_uniform",
    "{{ABLATION_JSON_STDLIB_A_ROWS_TOTAL}}": "ablation.matrix_fallback.json_stdlib.a_rows_total",
    "{{ABLATION_CALCULATOR_C_ENTRIES_ZERO}}": "ablation.matrix_fallback.calculator.c_entries_zero",
    "{{ABLATION_CALCULATOR_C_ENTRIES_TOTAL}}": "ablation.matrix_fallback.calculator.c_entries_total",
    "{{ABLATION_EVENT_PIPELINE_C_ENTRIES_ZERO}}": "ablation.matrix_fallback.event_pipeline.c_entries_zero",
    "{{ABLATION_EVENT_PIPELINE_C_ENTRIES_TOTAL}}": "ablation.matrix_fallback.event_pipeline.c_entries_total",
    "{{ABLATION_FLASK_MINI_C_ENTRIES_ZERO}}": "ablation.matrix_fallback.flask_mini.c_entries_zero",
    "{{ABLATION_FLASK_MINI_C_ENTRIES_TOTAL}}": "ablation.matrix_fallback.flask_mini.c_entries_total",
    "{{ABLATION_FLASK_APP_C_ENTRIES_ZERO}}": "ablation.matrix_fallback.flask_app.c_entries_zero",
    "{{ABLATION_FLASK_APP_C_ENTRIES_TOTAL}}": "ablation.matrix_fallback.flask_app.c_entries_total",
    "{{ABLATION_REQUESTS_LIB_A_ROWS_UNIFORM}}": "ablation.matrix_fallback.requests_lib.a_rows_uniform",
    "{{ABLATION_REQUESTS_LIB_A_ROWS_TOTAL}}": "ablation.matrix_fallback.requests_lib.a_rows_total",
    "{{ABLATION_REQUESTS_LIB_C_ENTRIES_ZERO}}": "ablation.matrix_fallback.requests_lib.c_entries_zero",
    "{{ABLATION_REQUESTS_LIB_C_ENTRIES_TOTAL}}": "ablation.matrix_fallback.requests_lib.c_entries_total",
    "{{ABLATION_JSON_STDLIB_C_ENTRIES_ZERO}}": "ablation.matrix_fallback.json_stdlib.c_entries_zero",
    "{{ABLATION_JSON_STDLIB_C_ENTRIES_TOTAL}}": "ablation.matrix_fallback.json_stdlib.c_entries_total",
    # Rule-family ablation: measured per-family total-mapping deltas
    # (baseline minus rule_filter-restricted run) for the two fixtures
    # used in @tbl:rule-family-ablation.
    "{{ABLATION_FLASK_APP_BASELINE}}": "ablation.rule_family.flask_app.baseline_mappings_total",
    "{{ABLATION_FLASK_APP_STRUCTURAL_DELTA}}": "ablation.rule_family.flask_app.structural_delta",
    "{{ABLATION_FLASK_APP_SEMANTIC_DELTA}}": "ablation.rule_family.flask_app.semantic_delta",
    "{{ABLATION_FLASK_APP_CONTROL_DELTA}}": "ablation.rule_family.flask_app.control_delta",
    "{{ABLATION_FLASK_APP_BEHAVIORAL_DELTA}}": "ablation.rule_family.flask_app.behavioral_delta",
    "{{ABLATION_FLASK_APP_RESILIENCE_DELTA}}": "ablation.rule_family.flask_app.resilience_delta",
    "{{ABLATION_CALCULATOR_BASELINE}}": "ablation.rule_family.calculator.baseline_mappings_total",
    "{{ABLATION_CALCULATOR_STRUCTURAL_DELTA}}": "ablation.rule_family.calculator.structural_delta",
    "{{ABLATION_CALCULATOR_SEMANTIC_DELTA}}": "ablation.rule_family.calculator.semantic_delta",
    "{{ABLATION_CALCULATOR_CONTROL_DELTA}}": "ablation.rule_family.calculator.control_delta",
    "{{ABLATION_CALCULATOR_BEHAVIORAL_DELTA}}": "ablation.rule_family.calculator.behavioral_delta",
    "{{ABLATION_CALCULATOR_RESILIENCE_DELTA}}": "ablation.rule_family.calculator.resilience_delta",
    "{{ABLATION_ZOO01_BASELINE}}": "ablation.rule_family.01_simple_state.baseline_mappings_total",
    "{{ABLATION_ZOO01_STRUCTURAL_DELTA}}": "ablation.rule_family.01_simple_state.structural_delta",
    "{{ABLATION_ZOO01_SEMANTIC_DELTA}}": "ablation.rule_family.01_simple_state.semantic_delta",
    "{{ABLATION_ZOO01_CONTROL_DELTA}}": "ablation.rule_family.01_simple_state.control_delta",
    "{{ABLATION_ZOO01_BEHAVIORAL_DELTA}}": "ablation.rule_family.01_simple_state.behavioral_delta",
    "{{ABLATION_ZOO01_RESILIENCE_DELTA}}": "ablation.rule_family.01_simple_state.resilience_delta",
    "{{ABLATION_ZOO01_BASELINE_HIDDEN_STATE}}": (
        "ablation.rule_family.01_simple_state.baseline_by_mapping_kind.HIDDEN_STATE"
    ),
    "{{ABLATION_ZOO01_BASELINE_OBSERVATION}}": (
        "ablation.rule_family.01_simple_state.baseline_by_mapping_kind.OBSERVATION"
    ),
    "{{ABLATION_ZOO01_BASELINE_ACTION}}": "ablation.rule_family.01_simple_state.baseline_by_mapping_kind.ACTION",
    "{{ABLATION_ZOO01_STRUCTURAL_HIDDEN_STATE_DELTA}}": (
        "ablation.by_mapping_kind.01_simple_state.structural.HIDDEN_STATE"
    ),
    "{{ABLATION_ZOO01_STRUCTURAL_POLICY_DELTA}}": "ablation.by_mapping_kind.01_simple_state.structural.POLICY",
    "{{ABLATION_ZOO01_SEMANTIC_OBSERVATION_DELTA}}": "ablation.by_mapping_kind.01_simple_state.semantic.OBSERVATION",
    "{{ABLATION_ZOO01_SEMANTIC_ACTION_DELTA}}": "ablation.by_mapping_kind.01_simple_state.semantic.ACTION",
    "{{ABLATION_ZOO01_A_ROWS_UNIFORM}}": "ablation.matrix_fallback.01_simple_state.a_rows_uniform",
    "{{ABLATION_ZOO01_A_ROWS_TOTAL}}": "ablation.matrix_fallback.01_simple_state.a_rows_total",
    "{{ABLATION_ZOO01_B_ACTIONS_IDENTITY}}": "ablation.matrix_fallback.01_simple_state.b_actions_identity",
    "{{ABLATION_ZOO01_B_ACTIONS_TOTAL}}": "ablation.matrix_fallback.01_simple_state.b_actions_total",
    "{{ABLATION_ZOO01_C_ENTRIES_ZERO}}": "ablation.matrix_fallback.01_simple_state.c_entries_zero",
    "{{ABLATION_ZOO01_C_ENTRIES_TOTAL}}": "ablation.matrix_fallback.01_simple_state.c_entries_total",
    # ---------------------------------------------------------------
    # Literature / bibliography
    # ---------------------------------------------------------------
    "{{BIB_ENTRIES}}": "literature.bibliography_entries",  # Total BibTeX entries in LITERATURE.md
    "{{BIBLIOGRAPHY_ENTRIES}}": "literature.bibliography_entries",  # Alias
    "{{LITERATURE_SOURCE}}": "literature.source",  # Path to LITERATURE.md
    # ---------------------------------------------------------------
    # Rust toolchain (FFI acceleration crates)
    # ---------------------------------------------------------------
    "{{RUST_CRATES}}": "rust.crates_total",  # Rust crate count under cogant/rust/
    "{{RUST_FFI}}": "rust.ffi_available",  # Bool: FFI compiled/available
    # ---------------------------------------------------------------
    # Provenance (top-level METRICS.yaml)
    # ---------------------------------------------------------------
    "{{METRICS_GENERATED_AT}}": "generated_at",  # ISO-8601 generation timestamp
    "{{METRICS_SCHEMA_VERSION}}": "schema_version",  # METRICS.yaml schema version
    "{{METRICS_GIT_SHA}}": "generator_git_sha",  # Git SHA at generation time
    "{{COGANT_VERSION_TOP}}": "cogant_version",  # Top-level cogant_version field
}
