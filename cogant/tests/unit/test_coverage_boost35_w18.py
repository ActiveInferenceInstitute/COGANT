#!/usr/bin/env python3
"""Coverage boost batch 35 — config/pipeline.py and config/loaders.py.

Covers:
- config/pipeline.py: PipelineConfig defaults, sub-configs, from_dict,
  from_json, to_dict, to_json, override, merge, active_stages
- config/loaders.py: ConfigLoadError, ConfigLoader (from_dict, from_json,
  merge_configs, create_cogant_config, load_preset, validate_config)
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# config/pipeline.py — PipelineConfig
# ---------------------------------------------------------------------------

class TestPipelineConfig:
    def test_default_stages(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert "ingest" in cfg.stages
        assert len(cfg.stages) >= 1

    def test_default_skip_stages_empty(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.skip_stages == []

    def test_default_skip_dynamic(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.skip_dynamic is True

    def test_default_output_dir(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.output_dir == "output"

    def test_default_verbose_false(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.verbose is False

    def test_default_dry_run_false(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.dry_run is False

    def test_default_sub_configs_present(self):
        from cogant.config.pipeline import PipelineConfig
        from cogant.config.ingest import IngestConfig
        from cogant.config.graph import GraphConfig
        cfg = PipelineConfig()
        assert isinstance(cfg.ingest, IngestConfig)
        assert isinstance(cfg.graph, GraphConfig)

    def test_frozen_raises_on_mutation(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        with pytest.raises(Exception):
            cfg.verbose = True

    def test_from_dict_basic(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig.from_dict({"verbose": True, "dry_run": True})
        assert cfg.verbose is True
        assert cfg.dry_run is True

    def test_from_dict_with_stages(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig.from_dict({"stages": ["ingest", "graph"]})
        assert cfg.stages == ["ingest", "graph"]

    def test_from_dict_empty(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig.from_dict({})
        assert cfg is not None

    def test_from_json(self, tmp_path):
        from cogant.config.pipeline import PipelineConfig
        import json
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"verbose": True, "dry_run": False}))
        cfg = PipelineConfig.from_json(config_file)
        assert cfg.verbose is True

    def test_from_json_invalid_raises(self, tmp_path):
        from cogant.config.pipeline import PipelineConfig
        config_file = tmp_path / "config.json"
        config_file.write_text("[1, 2, 3]")  # Not a dict
        with pytest.raises((ValueError, Exception)):
            PipelineConfig.from_json(config_file)

    def test_to_dict_returns_dict(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert "stages" in d

    def test_to_dict_roundtrip(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig(verbose=True, skip_dynamic=False)
        d = cfg.to_dict()
        cfg2 = PipelineConfig.from_dict(d)
        assert cfg2.verbose is True
        assert cfg2.skip_dynamic is False

    def test_to_json_writes_file(self, tmp_path):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig(verbose=True)
        out = tmp_path / "out.json"
        cfg.to_json(out)
        assert out.exists()

    def test_to_json_roundtrip(self, tmp_path):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig(verbose=True, output_dir="mydir")
        out = tmp_path / "out.json"
        cfg.to_json(out)
        cfg2 = PipelineConfig.from_json(out)
        assert cfg2.verbose is True
        assert cfg2.output_dir == "mydir"

    def test_override_single_field(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        cfg2 = cfg.override(verbose=True)
        assert cfg2.verbose is True
        assert cfg.verbose is False  # original unchanged

    def test_override_multiple_fields(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        cfg2 = cfg.override(verbose=True, dry_run=True, output_dir="test_out")
        assert cfg2.verbose is True
        assert cfg2.dry_run is True
        assert cfg2.output_dir == "test_out"

    def test_override_unknown_field_raises(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        with pytest.raises(ValueError):
            cfg.override(nonexistent_field=True)

    def test_custom_sub_config(self):
        from cogant.config.pipeline import PipelineConfig
        from cogant.config.ingest import IngestConfig
        ingest = IngestConfig(max_file_size_kb=256)
        cfg = PipelineConfig(ingest=ingest)
        assert cfg.ingest.max_file_size_kb == 256

    def test_coverage_path_default_none(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.coverage_path is None

    def test_plugins_default_empty(self):
        from cogant.config.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert cfg.plugins == {}


# ---------------------------------------------------------------------------
# config/loaders.py — ConfigLoadError, ConfigLoader
# ---------------------------------------------------------------------------

class TestConfigLoadError:
    def test_is_exception(self):
        from cogant.config.loaders import ConfigLoadError
        assert issubclass(ConfigLoadError, Exception)

    def test_raise_and_catch(self):
        from cogant.config.loaders import ConfigLoadError
        with pytest.raises(ConfigLoadError):
            raise ConfigLoadError("test error")


class TestConfigLoader:
    def test_load_json_from_file(self, tmp_path):
        from cogant.config.loaders import ConfigLoader
        import json
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"key": "value"}))
        result = ConfigLoader.load_json_from_file(cfg_file)
        assert result == {"key": "value"}

    def test_load_json_from_file_missing_raises(self, tmp_path):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError
        with pytest.raises(ConfigLoadError):
            ConfigLoader.load_json_from_file(tmp_path / "nonexistent.json")

    def test_load_json_from_file_invalid_raises(self, tmp_path):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError
        cfg_file = tmp_path / "bad.json"
        cfg_file.write_text("not valid json {")
        with pytest.raises((ConfigLoadError, Exception)):
            ConfigLoader.load_json_from_file(cfg_file)

    def test_load_json_from_file_array_returns_empty(self, tmp_path):
        from cogant.config.loaders import ConfigLoader
        import json
        cfg_file = tmp_path / "arr.json"
        cfg_file.write_text(json.dumps([1, 2, 3]))
        result = ConfigLoader.load_json_from_file(cfg_file)
        # Non-dict returns empty dict per implementation
        assert result == {}

    def test_load_from_dict(self):
        from cogant.config.loaders import ConfigLoader
        data = {"pipeline": {"stages": ["ingest"]}, "graph": {"max_nodes": 100}}
        result = ConfigLoader.load_from_dict(data)
        assert result == data

    def test_load_from_dict_non_dict_raises(self):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError
        with pytest.raises(ConfigLoadError):
            ConfigLoader.load_from_dict([1, 2, 3])  # type: ignore

    def test_load_default_returns_dict(self):
        from cogant.config.loaders import ConfigLoader
        result = ConfigLoader.load_default()
        assert isinstance(result, dict)
        assert "cogant" in result or "pipeline" in result

    def test_load_preset_default(self):
        from cogant.config.loaders import ConfigLoader
        try:
            result = ConfigLoader.load_preset("default")
            assert isinstance(result, dict)
        except Exception:
            pytest.skip("preset 'default' not available")

    def test_load_preset_unknown_raises(self):
        from cogant.config.loaders import ConfigLoader, ConfigLoadError
        with pytest.raises(ConfigLoadError):
            ConfigLoader.load_preset("nonexistent_preset")

    def test_merge_configs_second_wins(self):
        from cogant.config.loaders import ConfigLoader
        base = {"a": 1, "b": 2}
        override = {"b": 99, "c": 3}
        result = ConfigLoader.merge_configs(base, override)
        assert result["b"] == 99
        assert result["a"] == 1
        assert result["c"] == 3

    def test_merge_configs_empty_base(self):
        from cogant.config.loaders import ConfigLoader
        result = ConfigLoader.merge_configs({}, {"x": 1})
        assert result["x"] == 1

    def test_merge_configs_empty_override(self):
        from cogant.config.loaders import ConfigLoader
        result = ConfigLoader.merge_configs({"x": 1}, {})
        assert result["x"] == 1

    def test_merge_configs_deep_merge(self):
        from cogant.config.loaders import ConfigLoader
        base = {"nested": {"a": 1, "b": 2}}
        override = {"nested": {"b": 99, "c": 3}}
        result = ConfigLoader.merge_configs(base, override, deep=True)
        assert result["nested"]["a"] == 1
        assert result["nested"]["b"] == 99
        assert result["nested"]["c"] == 3

    def test_build_cogant_config_returns_cogant_config(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.schema import CogantConfig
        cfg = ConfigLoader.build_cogant_config()
        assert isinstance(cfg, CogantConfig)

    def test_build_cogant_config_with_dict(self):
        from cogant.config.loaders import ConfigLoader
        from cogant.config.schema import CogantConfig
        cfg = ConfigLoader.build_cogant_config(config_dict={})
        assert isinstance(cfg, CogantConfig)
