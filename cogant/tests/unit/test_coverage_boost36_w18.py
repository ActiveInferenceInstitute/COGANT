#!/usr/bin/env python3
"""Coverage boost batch 36 — config/schema.py and config/defaults.py.

Covers:
- config/schema.py: LogLevel, CogantConfig, LanguageConfig, PipelineStage,
  PipelineConfig (schema version), ExportFormat, ExportConfig, ValidationConfig
- config/defaults.py: DEFAULT_COGANT_CONFIG, DEFAULT_PIPELINE_CONFIG,
  DEFAULT_EXPORT_CONFIG, DEFAULT_VALIDATION_CONFIG, PRESETS
"""

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# config/schema.py — LogLevel
# ---------------------------------------------------------------------------


class TestLogLevel:
    def test_debug(self):
        from cogant.config.schema import LogLevel

        assert LogLevel.DEBUG == "debug"

    def test_info(self):
        from cogant.config.schema import LogLevel

        assert LogLevel.INFO == "info"

    def test_warning(self):
        from cogant.config.schema import LogLevel

        assert LogLevel.WARNING == "warning"

    def test_error(self):
        from cogant.config.schema import LogLevel

        assert LogLevel.ERROR == "error"

    def test_critical(self):
        from cogant.config.schema import LogLevel

        assert LogLevel.CRITICAL == "critical"


# ---------------------------------------------------------------------------
# config/schema.py — CogantConfig
# ---------------------------------------------------------------------------


class TestCogantConfig:
    def test_default_version(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig()
        assert cfg.version == "1.0.0"

    def test_default_environment(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig()
        assert cfg.environment == "production"

    def test_default_log_level(self):
        from cogant.config.schema import CogantConfig, LogLevel

        cfg = CogantConfig()
        assert cfg.log_level == LogLevel.INFO

    def test_default_max_workers(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig()
        assert cfg.max_workers == 4

    def test_default_max_memory_mb(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig()
        assert cfg.max_memory_mb == 4096

    def test_default_enable_caching(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig()
        assert cfg.enable_caching is True

    def test_default_enable_validation(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig()
        assert cfg.enable_validation is True

    def test_default_enable_gnn_export(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig()
        assert cfg.enable_gnn_export is True

    def test_custom_environment(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig(environment="development")
        assert cfg.environment == "development"

    def test_custom_max_workers(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig(max_workers=8)
        assert cfg.max_workers == 8

    def test_enable_incremental_analysis_default(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig()
        assert cfg.enable_incremental_analysis is False

    def test_strict_schema_validation_default(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig()
        assert cfg.strict_schema_validation is True

    def test_fail_on_warnings_default(self):
        from cogant.config.schema import CogantConfig

        cfg = CogantConfig()
        assert cfg.fail_on_warnings is False


# ---------------------------------------------------------------------------
# config/schema.py — LanguageConfig
# ---------------------------------------------------------------------------


class TestLanguageConfig:
    def test_creation(self):
        from cogant.config.schema import LanguageConfig

        cfg = LanguageConfig(language="python", analyzer_name="tree_sitter")
        assert cfg.language == "python"
        assert cfg.analyzer_name == "tree_sitter"

    def test_enabled_default(self):
        from cogant.config.schema import LanguageConfig

        cfg = LanguageConfig(language="js", analyzer_name="tree_sitter_js")
        assert cfg.enabled is True

    def test_analyzer_config_default_empty(self):
        from cogant.config.schema import LanguageConfig

        cfg = LanguageConfig(language="ts", analyzer_name="ts_analyzer")
        assert cfg.analyzer_config == {}

    def test_custom_analyzer_config(self):
        from cogant.config.schema import LanguageConfig

        cfg = LanguageConfig(
            language="py",
            analyzer_name="ast",
            analyzer_config={"strict": True},
        )
        assert cfg.analyzer_config["strict"] is True


# ---------------------------------------------------------------------------
# config/schema.py — PipelineStage
# ---------------------------------------------------------------------------


class TestPipelineStage:
    def test_creation(self):
        from cogant.config.schema import PipelineStage

        stage = PipelineStage(name="ingest")
        assert stage.name == "ingest"

    def test_enabled_default(self):
        from cogant.config.schema import PipelineStage

        stage = PipelineStage(name="graph")
        assert stage.enabled is True

    def test_timeout_default(self):
        from cogant.config.schema import PipelineStage

        stage = PipelineStage(name="translate")
        assert stage.timeout_seconds == 300.0

    def test_retry_count_default(self):
        from cogant.config.schema import PipelineStage

        stage = PipelineStage(name="validate")
        assert stage.retry_count == 0

    def test_skip_on_error_default(self):
        from cogant.config.schema import PipelineStage

        stage = PipelineStage(name="export")
        assert stage.skip_on_error is False

    def test_parameters_default_empty(self):
        from cogant.config.schema import PipelineStage

        stage = PipelineStage(name="ingest")
        assert stage.parameters == {}


# ---------------------------------------------------------------------------
# config/schema.py — PipelineConfig (schema version)
# ---------------------------------------------------------------------------


class TestSchemaPipelineConfig:
    def test_default_name(self):
        from cogant.config.schema import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.name == "default"

    def test_default_run_stages(self):
        from cogant.config.schema import PipelineConfig

        cfg = PipelineConfig()
        assert "ingest" in cfg.run_stages
        assert len(cfg.run_stages) >= 3

    def test_default_analyze_tests(self):
        from cogant.config.schema import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.analyze_tests is True

    def test_default_follow_imports(self):
        from cogant.config.schema import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.follow_imports is True

    def test_custom_name(self):
        from cogant.config.schema import PipelineConfig

        cfg = PipelineConfig(name="my_pipeline")
        assert cfg.name == "my_pipeline"

    def test_exclude_patterns_default_empty(self):
        from cogant.config.schema import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.exclude_patterns == []

    def test_max_import_depth_default(self):
        from cogant.config.schema import PipelineConfig

        cfg = PipelineConfig()
        assert cfg.max_import_depth == 5


# ---------------------------------------------------------------------------
# config/schema.py — ExportFormat
# ---------------------------------------------------------------------------


class TestExportFormat:
    def test_json(self):
        from cogant.config.schema import ExportFormat

        assert ExportFormat.JSON == "json"

    def test_json_lines(self):
        from cogant.config.schema import ExportFormat

        assert ExportFormat.JSON_LINES == "jsonl"

    def test_parquet(self):
        from cogant.config.schema import ExportFormat

        assert ExportFormat.PARQUET == "parquet"

    def test_protobuf(self):
        from cogant.config.schema import ExportFormat

        assert ExportFormat.PROTOBUF == "protobuf"


# ---------------------------------------------------------------------------
# config/schema.py — ExportConfig
# ---------------------------------------------------------------------------


class TestExportConfig:
    def test_default_primary_format(self):
        from cogant.config.schema import ExportConfig, ExportFormat

        cfg = ExportConfig()
        assert cfg.primary_format == ExportFormat.JSON

    def test_default_output_dir(self):
        from cogant.config.schema import ExportConfig

        cfg = ExportConfig()
        assert "cogant" in cfg.output_dir.lower() or cfg.output_dir != ""

    def test_default_create_bundle(self):
        from cogant.config.schema import ExportConfig

        cfg = ExportConfig()
        assert cfg.create_bundle is True

    def test_default_compression(self):
        from cogant.config.schema import ExportConfig

        cfg = ExportConfig()
        assert cfg.compression == "gzip"

    def test_default_compression_level(self):
        from cogant.config.schema import ExportConfig

        cfg = ExportConfig()
        assert cfg.compression_level == 6

    def test_custom_primary_format(self):
        from cogant.config.schema import ExportConfig, ExportFormat

        cfg = ExportConfig(primary_format=ExportFormat.PARQUET)
        assert cfg.primary_format == ExportFormat.PARQUET


# ---------------------------------------------------------------------------
# config/defaults.py — defaults and presets
# ---------------------------------------------------------------------------


class TestConfigDefaults:
    def test_default_cogant_config_type(self):
        from cogant.config.defaults import DEFAULT_COGANT_CONFIG
        from cogant.config.schema import CogantConfig

        assert isinstance(DEFAULT_COGANT_CONFIG, CogantConfig)

    def test_default_pipeline_config_type(self):
        from cogant.config.defaults import DEFAULT_PIPELINE_CONFIG
        from cogant.config.schema import PipelineConfig

        assert isinstance(DEFAULT_PIPELINE_CONFIG, PipelineConfig)

    def test_default_export_config_type(self):
        from cogant.config.defaults import DEFAULT_EXPORT_CONFIG
        from cogant.config.schema import ExportConfig

        assert isinstance(DEFAULT_EXPORT_CONFIG, ExportConfig)

    def test_default_validation_config_exists(self):
        from cogant.config.defaults import DEFAULT_VALIDATION_CONFIG

        assert DEFAULT_VALIDATION_CONFIG is not None

    def test_presets_is_dict(self):
        from cogant.config.defaults import PRESETS

        assert isinstance(PRESETS, dict)

    def test_presets_non_empty(self):
        from cogant.config.defaults import PRESETS

        assert len(PRESETS) >= 1

    def test_presets_each_has_cogant(self):
        from cogant.config.defaults import PRESETS

        for name, preset in PRESETS.items():
            assert "cogant" in preset, f"Preset '{name}' missing 'cogant' key"

    def test_presets_each_has_pipeline(self):
        from cogant.config.defaults import PRESETS

        for name, preset in PRESETS.items():
            assert "pipeline" in preset, f"Preset '{name}' missing 'pipeline' key"
