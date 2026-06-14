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


def is_nullable_path(path: str) -> bool:
    """True if a ``None`` value at *path* is intentional (renders ``N/A``).

    Only the native role-preservation score fields are legitimately nullable
    when the current ledger has no scored rows. Every other load-bearing metric that
    resolves to ``None`` is a generation defect and must be surfaced — see
    :func:`substitute_text`, which leaves such tokens unresolved so ``--strict``
    can fail rather than shipping a silent blank.
    """
    return "role_preservation_score" in path


def format_value_for_path(path: str, value: Any) -> str:
    """Format a METRICS value for manuscript substitution (aligned with inject tool)."""
    if value is None:
        if is_nullable_path(path):
            return "N/A"
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if "role_preservation_score" in path or "threshold_" in path:
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
        # Skip missing keys and load-bearing nulls so they surface as unresolved
        # tokens (an intentionally-nullable score still renders "N/A").
        if value is _MISSING or (value is None and not is_nullable_path(path)):
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
        # Leave missing keys and load-bearing nulls unresolved so
        # find_unresolved_placeholders / --strict can flag them, rather than
        # silently substituting an empty string for a present-but-null metric.
        if value is _MISSING or (value is None and not is_nullable_path(path)):
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
    "{{NON_NATIVE_COUNT}}": "evaluation.roundtrip.non_native_count",  # Rows outside current native counts
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
    "{{ABLATION_CALCULATOR_A_COLS_UNIFORM}}": "ablation.matrix_fallback.calculator.a_cols_uniform",
    "{{ABLATION_CALCULATOR_A_COLS_TOTAL}}": "ablation.matrix_fallback.calculator.a_cols_total",
    "{{ABLATION_EVENT_PIPELINE_A_COLS_UNIFORM}}": "ablation.matrix_fallback.event_pipeline.a_cols_uniform",
    "{{ABLATION_EVENT_PIPELINE_A_COLS_TOTAL}}": "ablation.matrix_fallback.event_pipeline.a_cols_total",
    "{{ABLATION_FLASK_MINI_A_COLS_UNIFORM}}": "ablation.matrix_fallback.flask_mini.a_cols_uniform",
    "{{ABLATION_FLASK_MINI_A_COLS_TOTAL}}": "ablation.matrix_fallback.flask_mini.a_cols_total",
    "{{ABLATION_FLASK_APP_A_COLS_UNIFORM}}": "ablation.matrix_fallback.flask_app.a_cols_uniform",
    "{{ABLATION_FLASK_APP_A_COLS_TOTAL}}": "ablation.matrix_fallback.flask_app.a_cols_total",
    "{{ABLATION_JSON_STDLIB_A_COLS_UNIFORM}}": "ablation.matrix_fallback.json_stdlib.a_cols_uniform",
    "{{ABLATION_JSON_STDLIB_A_COLS_TOTAL}}": "ablation.matrix_fallback.json_stdlib.a_cols_total",
    # B-actions identity/total (bound to METRICS so @tbl:matrix-fallback-ablation
    # never drifts again; previously these were hand-typed literals).
    "{{ABLATION_CALCULATOR_B_ACTIONS_IDENTITY}}": "ablation.matrix_fallback.calculator.b_actions_identity",
    "{{ABLATION_CALCULATOR_B_ACTIONS_TOTAL}}": "ablation.matrix_fallback.calculator.b_actions_total",
    "{{ABLATION_EVENT_PIPELINE_B_ACTIONS_IDENTITY}}": "ablation.matrix_fallback.event_pipeline.b_actions_identity",
    "{{ABLATION_EVENT_PIPELINE_B_ACTIONS_TOTAL}}": "ablation.matrix_fallback.event_pipeline.b_actions_total",
    "{{ABLATION_FLASK_MINI_B_ACTIONS_IDENTITY}}": "ablation.matrix_fallback.flask_mini.b_actions_identity",
    "{{ABLATION_FLASK_MINI_B_ACTIONS_TOTAL}}": "ablation.matrix_fallback.flask_mini.b_actions_total",
    "{{ABLATION_FLASK_APP_B_ACTIONS_IDENTITY}}": "ablation.matrix_fallback.flask_app.b_actions_identity",
    "{{ABLATION_FLASK_APP_B_ACTIONS_TOTAL}}": "ablation.matrix_fallback.flask_app.b_actions_total",
    "{{ABLATION_REQUESTS_LIB_B_ACTIONS_IDENTITY}}": "ablation.matrix_fallback.requests_lib.b_actions_identity",
    "{{ABLATION_REQUESTS_LIB_B_ACTIONS_TOTAL}}": "ablation.matrix_fallback.requests_lib.b_actions_total",
    "{{ABLATION_JSON_STDLIB_B_ACTIONS_IDENTITY}}": "ablation.matrix_fallback.json_stdlib.b_actions_identity",
    "{{ABLATION_JSON_STDLIB_B_ACTIONS_TOTAL}}": "ablation.matrix_fallback.json_stdlib.b_actions_total",
    "{{ABLATION_CALCULATOR_C_ENTRIES_ZERO}}": "ablation.matrix_fallback.calculator.c_entries_zero",
    "{{ABLATION_CALCULATOR_C_ENTRIES_TOTAL}}": "ablation.matrix_fallback.calculator.c_entries_total",
    "{{ABLATION_EVENT_PIPELINE_C_ENTRIES_ZERO}}": "ablation.matrix_fallback.event_pipeline.c_entries_zero",
    "{{ABLATION_EVENT_PIPELINE_C_ENTRIES_TOTAL}}": "ablation.matrix_fallback.event_pipeline.c_entries_total",
    "{{ABLATION_FLASK_MINI_C_ENTRIES_ZERO}}": "ablation.matrix_fallback.flask_mini.c_entries_zero",
    "{{ABLATION_FLASK_MINI_C_ENTRIES_TOTAL}}": "ablation.matrix_fallback.flask_mini.c_entries_total",
    "{{ABLATION_FLASK_APP_C_ENTRIES_ZERO}}": "ablation.matrix_fallback.flask_app.c_entries_zero",
    "{{ABLATION_FLASK_APP_C_ENTRIES_TOTAL}}": "ablation.matrix_fallback.flask_app.c_entries_total",
    "{{ABLATION_REQUESTS_LIB_A_COLS_UNIFORM}}": "ablation.matrix_fallback.requests_lib.a_cols_uniform",
    "{{ABLATION_REQUESTS_LIB_A_COLS_TOTAL}}": "ablation.matrix_fallback.requests_lib.a_cols_total",
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
    "{{ABLATION_ZOO01_A_COLS_UNIFORM}}": "ablation.matrix_fallback.01_simple_state.a_cols_uniform",
    "{{ABLATION_ZOO01_A_COLS_TOTAL}}": "ablation.matrix_fallback.01_simple_state.a_cols_total",
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
    # ---------------------------------------------------------------
    # Per-fixture pipeline metrics (from evaluation/figures/metrics.json,
    # merged under `fixtures` by z_generate_manuscript_variables.py).
    # Bind per-fixture numbers cited in prose so they auto-inject from
    # the same artifact @tbl:repo-pipeline-metrics is verified against.
    # ---------------------------------------------------------------
    "{{FIXTURE_CALCULATOR_FILES}}": "fixtures.calculator.files",
    "{{FIXTURE_CALCULATOR_LOC}}": "fixtures.calculator.loc",
    "{{FIXTURE_CALCULATOR_NODES}}": "fixtures.calculator.nodes",
    "{{FIXTURE_CALCULATOR_EDGES}}": "fixtures.calculator.edges",
    "{{FIXTURE_CALCULATOR_MAPPINGS_TOTAL}}": "fixtures.calculator.mappings_total",
    "{{FIXTURE_CALCULATOR_STATE_VARIABLES}}": "fixtures.calculator.state_variables",
    "{{FIXTURE_CALCULATOR_OBSERVATIONS}}": "fixtures.calculator.observations",
    "{{FIXTURE_CALCULATOR_ACTIONS}}": "fixtures.calculator.actions",
    "{{FIXTURE_CALCULATOR_TRANSITIONS}}": "fixtures.calculator.transitions",
    "{{FIXTURE_CALCULATOR_GNN_SECTIONS}}": "fixtures.calculator.gnn_sections",
    "{{FIXTURE_EVENT_PIPELINE_FILES}}": "fixtures.event_pipeline.files",
    "{{FIXTURE_EVENT_PIPELINE_LOC}}": "fixtures.event_pipeline.loc",
    "{{FIXTURE_EVENT_PIPELINE_NODES}}": "fixtures.event_pipeline.nodes",
    "{{FIXTURE_EVENT_PIPELINE_EDGES}}": "fixtures.event_pipeline.edges",
    "{{FIXTURE_EVENT_PIPELINE_MAPPINGS_TOTAL}}": "fixtures.event_pipeline.mappings_total",
    "{{FIXTURE_EVENT_PIPELINE_STATE_VARIABLES}}": "fixtures.event_pipeline.state_variables",
    "{{FIXTURE_EVENT_PIPELINE_OBSERVATIONS}}": "fixtures.event_pipeline.observations",
    "{{FIXTURE_EVENT_PIPELINE_ACTIONS}}": "fixtures.event_pipeline.actions",
    "{{FIXTURE_EVENT_PIPELINE_TRANSITIONS}}": "fixtures.event_pipeline.transitions",
    "{{FIXTURE_EVENT_PIPELINE_GNN_SECTIONS}}": "fixtures.event_pipeline.gnn_sections",
    "{{FIXTURE_FLASK_MINI_FILES}}": "fixtures.flask_mini.files",
    "{{FIXTURE_FLASK_MINI_LOC}}": "fixtures.flask_mini.loc",
    "{{FIXTURE_FLASK_MINI_NODES}}": "fixtures.flask_mini.nodes",
    "{{FIXTURE_FLASK_MINI_EDGES}}": "fixtures.flask_mini.edges",
    "{{FIXTURE_FLASK_MINI_MAPPINGS_TOTAL}}": "fixtures.flask_mini.mappings_total",
    "{{FIXTURE_FLASK_MINI_STATE_VARIABLES}}": "fixtures.flask_mini.state_variables",
    "{{FIXTURE_FLASK_MINI_OBSERVATIONS}}": "fixtures.flask_mini.observations",
    "{{FIXTURE_FLASK_MINI_ACTIONS}}": "fixtures.flask_mini.actions",
    "{{FIXTURE_FLASK_MINI_TRANSITIONS}}": "fixtures.flask_mini.transitions",
    "{{FIXTURE_FLASK_MINI_GNN_SECTIONS}}": "fixtures.flask_mini.gnn_sections",
    "{{FIXTURE_FLASK_APP_FILES}}": "fixtures.flask_app.files",
    "{{FIXTURE_FLASK_APP_LOC}}": "fixtures.flask_app.loc",
    "{{FIXTURE_FLASK_APP_NODES}}": "fixtures.flask_app.nodes",
    "{{FIXTURE_FLASK_APP_EDGES}}": "fixtures.flask_app.edges",
    "{{FIXTURE_FLASK_APP_MAPPINGS_TOTAL}}": "fixtures.flask_app.mappings_total",
    "{{FIXTURE_FLASK_APP_STATE_VARIABLES}}": "fixtures.flask_app.state_variables",
    "{{FIXTURE_FLASK_APP_OBSERVATIONS}}": "fixtures.flask_app.observations",
    "{{FIXTURE_FLASK_APP_ACTIONS}}": "fixtures.flask_app.actions",
    "{{FIXTURE_FLASK_APP_TRANSITIONS}}": "fixtures.flask_app.transitions",
    "{{FIXTURE_FLASK_APP_GNN_SECTIONS}}": "fixtures.flask_app.gnn_sections",
    "{{FIXTURE_REQUESTS_LIB_FILES}}": "fixtures.requests_lib.files",
    "{{FIXTURE_REQUESTS_LIB_LOC}}": "fixtures.requests_lib.loc",
    "{{FIXTURE_REQUESTS_LIB_NODES}}": "fixtures.requests_lib.nodes",
    "{{FIXTURE_REQUESTS_LIB_EDGES}}": "fixtures.requests_lib.edges",
    "{{FIXTURE_REQUESTS_LIB_MAPPINGS_TOTAL}}": "fixtures.requests_lib.mappings_total",
    "{{FIXTURE_REQUESTS_LIB_STATE_VARIABLES}}": "fixtures.requests_lib.state_variables",
    "{{FIXTURE_REQUESTS_LIB_OBSERVATIONS}}": "fixtures.requests_lib.observations",
    "{{FIXTURE_REQUESTS_LIB_ACTIONS}}": "fixtures.requests_lib.actions",
    "{{FIXTURE_REQUESTS_LIB_TRANSITIONS}}": "fixtures.requests_lib.transitions",
    "{{FIXTURE_REQUESTS_LIB_GNN_SECTIONS}}": "fixtures.requests_lib.gnn_sections",
    "{{FIXTURE_JSON_STDLIB_FILES}}": "fixtures.json_stdlib.files",
    "{{FIXTURE_JSON_STDLIB_LOC}}": "fixtures.json_stdlib.loc",
    "{{FIXTURE_JSON_STDLIB_NODES}}": "fixtures.json_stdlib.nodes",
    "{{FIXTURE_JSON_STDLIB_EDGES}}": "fixtures.json_stdlib.edges",
    "{{FIXTURE_JSON_STDLIB_MAPPINGS_TOTAL}}": "fixtures.json_stdlib.mappings_total",
    "{{FIXTURE_JSON_STDLIB_STATE_VARIABLES}}": "fixtures.json_stdlib.state_variables",
    "{{FIXTURE_JSON_STDLIB_OBSERVATIONS}}": "fixtures.json_stdlib.observations",
    "{{FIXTURE_JSON_STDLIB_ACTIONS}}": "fixtures.json_stdlib.actions",
    "{{FIXTURE_JSON_STDLIB_TRANSITIONS}}": "fixtures.json_stdlib.transitions",
    "{{FIXTURE_JSON_STDLIB_GNN_SECTIONS}}": "fixtures.json_stdlib.gnn_sections",
}
