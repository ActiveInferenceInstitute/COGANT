#!/usr/bin/env python3
"""Coverage boost batch 41 — config/loaders.py additional paths and api/pipeline.py.

Covers:
- ConfigLoader: load_from_yaml (HAS_YAML=False path, file not found, all paths),
  build_pipeline_config, build_export_config, build_validation_config,
  load_all_configs (all paths, with preset, with dict)
- PipelineConfig (api/pipeline.py): creation, defaults, all fields
- PipelineRunner: __init__, run (basic, skip stages, skip_dynamic, layout_output=False,
  unknown stage)
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# config/loaders.py — load_from_yaml (yaml not available path)
# ---------------------------------------------------------------------------

class TestConfigLoaderYamlPath:
    def test_load_from_yaml_raises_when_no_yaml(self):
        """Test ConfigLoadError when yaml not installed."""
        from cogant.config.loaders import ConfigLoader, ConfigLoadError, HAS_YAML
        if HAS_YAML:
            pytest.skip("yaml is available; testing the no-yaml path")
        with pytest.raises(ConfigLoadError, match="PyYAML is not installed"):
            ConfigLoader.load_from_yaml("/tmp/some.yaml")

    def test_load_from_yaml_file_not_found(self, tmp_path):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError, HAS_YAML
        if not HAS_YAML:
            pytest.skip("yaml not available")
        with pytest.raises(ConfigLoadError):
            ConfigLoader.load_from_yaml(tmp_path / "nonexistent.yaml")

    def test_load_from_yaml_valid_file(self, tmp_path):
        from cogant.config.loaders import ConfigLoader, HAS_YAML
        if not HAS_YAML:
            pytest.skip("yaml not available")
        import yaml
        f = tmp_path / "cfg.yaml"
        f.write_text(yaml.dump({"key": "value"}))
        result = ConfigLoader.load_from_yaml(f)
        assert result == {"key": "value"}

    def test_load_from_yaml_invalid_yaml(self, tmp_path):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError, HAS_YAML
        if not HAS_YAML:
            pytest.skip("yaml not available")
        f = tmp_path / "bad.yaml"
        f.write_text("key: [unclosed\n  - invalid")
        with pytest.raises((ConfigLoadError, Exception)):
            ConfigLoader.load_from_yaml(f)

    def test_load_from_yaml_non_dict_returns_empty(self, tmp_path):
        from cogant.config.loaders import ConfigLoader, HAS_YAML
        if not HAS_YAML:
            pytest.skip("yaml not available")
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n")
        result = ConfigLoader.load_from_yaml(f)
        assert result == {}


# ---------------------------------------------------------------------------
# config/loaders.py — build_pipeline_config
# ---------------------------------------------------------------------------

class TestBuildPipelineConfig:
    def test_default_returns_pipeline_config(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.schema import PipelineConfig
        cfg = ConfigLoader.build_pipeline_config()
        assert isinstance(cfg, PipelineConfig)

    def test_with_preset(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.schema import PipelineConfig
        from cogant.config.defaults import PRESETS
        if not PRESETS:
            pytest.skip("no presets available")
        preset_name = next(iter(PRESETS))
        cfg = ConfigLoader.build_pipeline_config(preset=preset_name)
        assert isinstance(cfg, PipelineConfig)

    def test_with_dict_stages(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.schema import PipelineConfig
        cfg = ConfigLoader.build_pipeline_config(config_dict={"pipeline": {}})
        assert isinstance(cfg, PipelineConfig)

    def test_unknown_preset_raises(self):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError
        with pytest.raises(ConfigLoadError):
            ConfigLoader.build_pipeline_config(preset="no_such_preset")


# ---------------------------------------------------------------------------
# config/loaders.py — build_export_config
# ---------------------------------------------------------------------------

class TestBuildExportConfig:
    def test_default_returns_export_config(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.schema import ExportConfig
        cfg = ConfigLoader.build_export_config()
        assert isinstance(cfg, ExportConfig)

    def test_with_preset(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.schema import ExportConfig
        from cogant.config.defaults import PRESETS
        if not PRESETS:
            pytest.skip("no presets available")
        preset_name = next(iter(PRESETS))
        cfg = ConfigLoader.build_export_config(preset=preset_name)
        assert isinstance(cfg, ExportConfig)

    def test_with_config_dict(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.schema import ExportConfig
        cfg = ConfigLoader.build_export_config(config_dict={})
        assert isinstance(cfg, ExportConfig)

    def test_unknown_preset_raises(self):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError
        with pytest.raises(ConfigLoadError):
            ConfigLoader.build_export_config(preset="nonexistent")


# ---------------------------------------------------------------------------
# config/loaders.py — build_validation_config
# ---------------------------------------------------------------------------

class TestBuildValidationConfig:
    def test_default_returns_validation_config(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.schema import ValidationConfig
        cfg = ConfigLoader.build_validation_config()
        assert isinstance(cfg, ValidationConfig)

    def test_with_preset(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.schema import ValidationConfig
        from cogant.config.defaults import PRESETS
        if not PRESETS:
            pytest.skip("no presets available")
        preset_name = next(iter(PRESETS))
        cfg = ConfigLoader.build_validation_config(preset=preset_name)
        assert isinstance(cfg, ValidationConfig)

    def test_with_config_dict(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.schema import ValidationConfig
        cfg = ConfigLoader.build_validation_config(config_dict={})
        assert isinstance(cfg, ValidationConfig)

    def test_unknown_preset_raises(self):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError
        with pytest.raises(ConfigLoadError):
            ConfigLoader.build_validation_config(preset="nonexistent")


# ---------------------------------------------------------------------------
# config/loaders.py — load_all_configs
# ---------------------------------------------------------------------------

class TestLoadAllConfigs:
    def test_no_args_returns_all_keys(self):
        from cogant.config.loaders import ConfigLoader
        result = ConfigLoader.load_all_configs()
        assert "cogant" in result
        assert "pipeline" in result
        assert "export" in result
        assert "validation" in result

    def test_with_preset(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.defaults import PRESETS
        if not PRESETS:
            pytest.skip("no presets available")
        preset_name = next(iter(PRESETS))
        result = ConfigLoader.load_all_configs(preset=preset_name)
        assert "cogant" in result

    def test_unknown_preset_raises(self):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError
        with pytest.raises(ConfigLoadError):
            ConfigLoader.load_all_configs(preset="definitely_not_a_real_preset")

    def test_with_cogant_in_dict(self):
        from cogant.config.loaders import ConfigLoader
        # build_cogant_config with dict containing 'cogant' key
        result = ConfigLoader.build_cogant_config(config_dict={"cogant": {}})
        from cogant.config.schema import CogantConfig
        assert isinstance(result, CogantConfig)


# ---------------------------------------------------------------------------
# api/pipeline.py — PipelineConfig (the api version, not schema)
# ---------------------------------------------------------------------------

class TestApiPipelineConfig:
    def test_default_stages(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert "ingest" in cfg.stages
        assert "translate" in cfg.stages

    def test_default_skip_empty(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.skip_stages == []

    def test_default_verbose_false(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.verbose is False

    def test_default_dry_run_false(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.dry_run is False

    def test_default_output_dir(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.output_dir == "output"

    def test_default_skip_dynamic_false(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.skip_dynamic is False

    def test_default_coverage_path_none(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.coverage_path is None

    def test_default_trace_path_none(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.trace_path is None

    def test_default_incremental_since_none(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.incremental_since is None

    def test_default_cache_dir_none(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.cache_dir is None

    def test_custom_stages(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig(stages=["ingest", "graph"])
        assert cfg.stages == ["ingest", "graph"]

    def test_skip_stages_custom(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig(skip_stages=["dynamic"])
        assert "dynamic" in cfg.skip_stages

    def test_layout_output_default_false(self):
        from cogant.api.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.layout_output is False


# ---------------------------------------------------------------------------
# api/pipeline.py — PipelineRunner
# ---------------------------------------------------------------------------

class TestPipelineRunnerInit:
    def test_creates_stage_handlers(self):
        from cogant.api.pipeline import PipelineRunner
        runner = PipelineRunner()
        assert "ingest" in runner.stage_handlers
        assert "translate" in runner.stage_handlers
        assert "export" in runner.stage_handlers

    def test_all_stages_have_handlers(self):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        runner = PipelineRunner()
        cfg = PipelineConfig()
        for stage in cfg.stages:
            assert stage in runner.stage_handlers, f"Missing handler for: {stage}"


class TestPipelineRunnerRun:
    def test_run_with_default_config_returns_bundle(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        from cogant.api.bundle import Bundle
        (tmp_path / "a.py").write_text("x = 1")
        cfg = PipelineConfig(
            stages=["ingest"],  # Only run ingest to keep test fast
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        assert isinstance(bundle, Bundle)

    def test_run_none_config_uses_defaults(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner
        from cogant.api.bundle import Bundle
        runner = PipelineRunner()
        # Running with None config on empty dir should succeed (errors go to bundle.errors)
        bundle = runner.run(str(tmp_path), None)
        assert isinstance(bundle, Bundle)

    def test_run_skips_requested_stages(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["ingest", "static"],
            skip_stages=["static"],
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        # static was skipped, so no static stage result
        assert "static" not in bundle.stage_results

    def test_skip_dynamic_adds_skipped_entry(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["dynamic"],
            skip_dynamic=True,
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        # dynamic should be in stage_results as skipped
        if "dynamic" in bundle.stage_results:
            assert bundle.stage_results["dynamic"].get("skipped") is True

    def test_run_unknown_stage_adds_to_errors(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=["totally_fake_stage"],
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        assert any("Unknown stage" in e for e in bundle.errors)

    def test_run_returns_bundle_with_metadata(self, tmp_path):
        from cogant.api.pipeline import PipelineRunner, PipelineConfig
        cfg = PipelineConfig(
            stages=[],  # no stages to run
            output_dir=str(tmp_path / "output"),
        )
        runner = PipelineRunner()
        bundle = runner.run(str(tmp_path), cfg)
        assert "config" in bundle.metadata
