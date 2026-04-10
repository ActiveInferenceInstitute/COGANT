"""Registry of manuscript template variables and their METRICS.yaml paths.

Usage:
    from tools.manuscript_vars import MANUSCRIPT_VARS
    # MANUSCRIPT_VARS["{{TEST_COUNT}}"] == "testing.test_count_passing"
"""

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

    # Rust
    "{{RUST_CRATES}}": "rust.crates_total",
    "{{RUST_FFI}}": "rust.ffi_available",
}
