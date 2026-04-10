"""
Configuration loaders for COGANT system.

Provides utilities to load configurations from YAML files, dictionaries,
and merge configurations with proper override semantics.
"""

import json
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from .defaults import (
    DEFAULT_COGANT_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PIPELINE_CONFIG,
    DEFAULT_VALIDATION_CONFIG,
    PRESETS,
)
from .schema import (
    CogantConfig,
    ExportConfig,
    PipelineConfig,
    ValidationConfig,
)


class ConfigLoadError(Exception):
    """Raised when configuration loading fails."""
    pass


class ConfigLoader:
    """Loads and manages COGANT configurations from various sources."""

    @staticmethod
    def load_from_yaml(path: str | Path) -> dict[str, Any]:
        """
        Load configuration from a YAML file.

        Args:
            path: Path to YAML configuration file.

        Returns:
            Dictionary of configuration data.

        Raises:
            ConfigLoadError: If YAML is not available or file cannot be read.
        """
        if not HAS_YAML:
            raise ConfigLoadError(
                "PyYAML is not installed. Install with: pip install pyyaml"
            )

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
                if data is None:
                    data = {}
                return dict(data) if isinstance(data, dict) else {}
        except FileNotFoundError as e:
            raise ConfigLoadError(f"Configuration file not found: {path}") from e
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Invalid YAML in {path}: {e}") from e
        except Exception as e:
            raise ConfigLoadError(
                f"Error reading configuration from {path}: {e}"
            ) from e

    @staticmethod
    def load_from_dict(data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and normalize configuration dictionary.

        Args:
            data: Configuration dictionary.

        Returns:
            Normalized configuration dictionary.
        """
        if not isinstance(data, dict):
            raise ConfigLoadError("Configuration must be a dictionary")
        return data

    @staticmethod
    def load_json_from_file(path: str | Path) -> dict[str, Any]:
        """
        Load configuration from a JSON file.

        Args:
            path: Path to JSON configuration file.

        Returns:
            Dictionary of configuration data.

        Raises:
            ConfigLoadError: If file cannot be read or JSON is invalid.
        """
        try:
            with open(path) as f:
                loaded = json.load(f)
                return dict(loaded) if isinstance(loaded, dict) else {}
        except FileNotFoundError as e:
            raise ConfigLoadError(f"Configuration file not found: {path}") from e
        except json.JSONDecodeError as e:
            raise ConfigLoadError(f"Invalid JSON in {path}: {e}") from e
        except Exception as e:
            raise ConfigLoadError(
                f"Error reading configuration from {path}: {e}"
            ) from e

    @staticmethod
    def merge_configs(
        base: dict[str, Any],
        override: dict[str, Any],
        deep: bool = True
    ) -> dict[str, Any]:
        """
        Merge configuration dictionaries with override semantics.

        Later values override earlier ones. If deep=True, nested dicts are merged
        recursively; otherwise, top-level keys are replaced entirely.

        Args:
            base: Base configuration dictionary.
            override: Override configuration dictionary.
            deep: If True, merge nested dicts recursively.

        Returns:
            Merged configuration dictionary.
        """
        result = base.copy()

        for key, override_value in override.items():
            if deep and key in result and isinstance(result[key], dict) and isinstance(override_value, dict):
                result[key] = ConfigLoader.merge_configs(
                    result[key], override_value, deep=True
                )
            else:
                result[key] = override_value

        return result

    @staticmethod
    def load_default() -> dict[str, Any]:
        """
        Get the default configuration.

        Returns:
            Default configuration dictionary suitable for building config objects.
        """
        return {
            "cogant": DEFAULT_COGANT_CONFIG.model_dump(),
            "pipeline": DEFAULT_PIPELINE_CONFIG.model_dump(),
            "export": DEFAULT_EXPORT_CONFIG.model_dump(),
            "validation": DEFAULT_VALIDATION_CONFIG.model_dump(),
        }

    @staticmethod
    def load_preset(name: str) -> dict[str, Any]:
        """
        Load a named preset configuration.

        Args:
            name: Preset name ('default', 'minimal', 'comprehensive', 'gnn', 'security').

        Returns:
            Dictionary with 'cogant', 'pipeline', 'export', 'validation' config objects.

        Raises:
            ConfigLoadError: If preset name is unknown.
        """
        if name not in PRESETS:
            available = ", ".join(PRESETS.keys())
            raise ConfigLoadError(
                f"Unknown preset '{name}'. Available: {available}"
            )
        return PRESETS[name]

    @staticmethod
    def build_cogant_config(
        config_dict: dict[str, Any] | None = None,
        preset: str | None = None,
    ) -> CogantConfig:
        """
        Build a CogantConfig from dictionary data and/or preset.

        Args:
            config_dict: Configuration dictionary (from YAML/JSON).
            preset: Optional preset name to use as base.

        Returns:
            CogantConfig object.

        Raises:
            ConfigLoadError: If configuration is invalid.
        """
        if preset:
            try:
                base_configs = ConfigLoader.load_preset(preset)
                base = base_configs["cogant"].model_dump()
            except ConfigLoadError:
                raise
        else:
            base = DEFAULT_COGANT_CONFIG.model_dump()

        if config_dict and "cogant" in config_dict:
            base = ConfigLoader.merge_configs(base, config_dict["cogant"], deep=True)

        try:
            return CogantConfig(**base)
        except Exception as e:
            raise ConfigLoadError(f"Invalid CogantConfig: {e}") from e

    @staticmethod
    def build_pipeline_config(
        config_dict: dict[str, Any] | None = None,
        preset: str | None = None,
    ) -> PipelineConfig:
        """
        Build a PipelineConfig from dictionary data and/or preset.

        Args:
            config_dict: Configuration dictionary (from YAML/JSON).
            preset: Optional preset name to use as base.

        Returns:
            PipelineConfig object.

        Raises:
            ConfigLoadError: If configuration is invalid.
        """
        if preset:
            try:
                base_configs = ConfigLoader.load_preset(preset)
                base = base_configs["pipeline"].model_dump()
            except ConfigLoadError:
                raise
        else:
            base = DEFAULT_PIPELINE_CONFIG.model_dump()

        if config_dict:
            # Map from cogant.yaml structure to schema structure
            pipeline_data = {}

            if "pipeline" in config_dict:
                pipeline_data = config_dict["pipeline"].copy()

            # Handle field name mappings from YAML to schema
            if "stages" in pipeline_data and isinstance(pipeline_data["stages"], list):
                # YAML has "stages" as a list (run_stages), not a dict
                pipeline_data["run_stages"] = pipeline_data.pop("stages")

            if pipeline_data:
                base = ConfigLoader.merge_configs(base, pipeline_data, deep=True)

        try:
            return PipelineConfig(**base)
        except Exception as e:
            raise ConfigLoadError(f"Invalid PipelineConfig: {e}") from e

    @staticmethod
    def build_export_config(
        config_dict: dict[str, Any] | None = None,
        preset: str | None = None,
    ) -> ExportConfig:
        """
        Build an ExportConfig from dictionary data and/or preset.

        Args:
            config_dict: Configuration dictionary (from YAML/JSON).
            preset: Optional preset name to use as base.

        Returns:
            ExportConfig object.

        Raises:
            ConfigLoadError: If configuration is invalid.
        """
        if preset:
            try:
                base_configs = ConfigLoader.load_preset(preset)
                base = base_configs["export"].model_dump()
            except ConfigLoadError:
                raise
        else:
            base = DEFAULT_EXPORT_CONFIG.model_dump()

        if config_dict and "export" in config_dict:
            base = ConfigLoader.merge_configs(base, config_dict["export"], deep=True)

        try:
            return ExportConfig(**base)
        except Exception as e:
            raise ConfigLoadError(f"Invalid ExportConfig: {e}") from e

    @staticmethod
    def build_validation_config(
        config_dict: dict[str, Any] | None = None,
        preset: str | None = None,
    ) -> ValidationConfig:
        """
        Build a ValidationConfig from dictionary data and/or preset.

        Args:
            config_dict: Configuration dictionary (from YAML/JSON).
            preset: Optional preset name to use as base.

        Returns:
            ValidationConfig object.

        Raises:
            ConfigLoadError: If configuration is invalid.
        """
        if preset:
            try:
                base_configs = ConfigLoader.load_preset(preset)
                base = base_configs["validation"].model_dump()
            except ConfigLoadError:
                raise
        else:
            base = DEFAULT_VALIDATION_CONFIG.model_dump()

        if config_dict and "validation" in config_dict:
            base = ConfigLoader.merge_configs(base, config_dict["validation"], deep=True)

        try:
            return ValidationConfig(**base)
        except Exception as e:
            raise ConfigLoadError(f"Invalid ValidationConfig: {e}") from e

    @staticmethod
    def load_all_configs(
        yaml_path: str | Path | None = None,
        preset: str | None = None,
    ) -> dict[str, Any]:
        """
        Load all configuration objects from YAML file and/or preset.

        Args:
            yaml_path: Optional path to YAML configuration file.
            preset: Optional preset name to use as base.

        Returns:
            Dictionary with 'cogant', 'pipeline', 'export', 'validation' config objects.

        Raises:
            ConfigLoadError: If configuration is invalid.
        """
        config_dict = None

        if yaml_path:
            config_dict = ConfigLoader.load_from_yaml(yaml_path)

        cogant_config = ConfigLoader.build_cogant_config(config_dict, preset)
        pipeline_config = ConfigLoader.build_pipeline_config(config_dict, preset)
        export_config = ConfigLoader.build_export_config(config_dict, preset)
        validation_config = ConfigLoader.build_validation_config(config_dict, preset)

        return {
            "cogant": cogant_config,
            "pipeline": pipeline_config,
            "export": export_config,
            "validation": validation_config,
        }
