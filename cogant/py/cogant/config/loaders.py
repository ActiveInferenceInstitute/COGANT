"""Strict configuration loading with one deterministic precedence chain."""

from __future__ import annotations

import json
import os
import warnings
from collections.abc import Mapping
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - exercised by dependency checks
    yaml = None

from .pipeline import PipelineConfig
from .presets import PRESETS
from .schema import (
    CURRENT_CONFIG_SCHEMA_VERSION,
    CogantConfig,
    ExportConfig,
    ProjectConfig,
    ValidationConfig,
)

HAS_YAML = yaml is not None


class ConfigMigrationWarning(DeprecationWarning):
    """Warning emitted when a legacy configuration is normalized."""


# One compatibility map is deliberately kept at the loader boundary.  The
# resulting model remains canonical; this map is not a second configuration
# registry and can be removed after the documented deprecation cycle.
_LEGACY_FLAT_FIELDS: dict[str, tuple[str, str]] = {
    # Runtime / resource settings formerly accepted at the document root.
    "version": ("cogant", "version"),
    "environment": ("cogant", "environment"),
    "log_level": ("cogant", "log_level"),
    "log_format": ("cogant", "log_format"),
    "log_file": ("cogant", "log_file"),
    "max_workers": ("cogant", "max_workers"),
    "max_memory_mb": ("cogant", "max_memory_mb"),
    "max_graph_nodes": ("cogant", "max_graph_nodes"),
    "timeout_seconds": ("cogant", "timeout_seconds"),
    "enable_caching": ("cogant", "enable_caching"),
    "cache_ttl_hours": ("cogant", "cache_ttl_hours"),
    "enable_provenance_tracking": ("cogant", "enable_provenance_tracking"),
    "enable_validation": ("cogant", "enable_validation"),
    "enable_gnn_export": ("cogant", "enable_gnn_export"),
    "enable_incremental_analysis": ("cogant", "enable_incremental_analysis"),
    "strict_schema_validation": ("cogant", "strict_schema_validation"),
    "fail_on_warnings": ("cogant", "fail_on_warnings"),
    "preserve_source_formatting": ("cogant", "preserve_source_formatting"),
    # Pipeline fields formerly accepted by the compatibility dataclass.
    "stages": ("pipeline", "stages"),
    "skip_stages": ("pipeline", "skip_stages"),
    "skip_dynamic": ("pipeline", "skip_dynamic"),
    "output_dir": ("pipeline", "output_dir"),
    "layout_output": ("pipeline", "layout_output"),
    "verbose": ("pipeline", "verbose"),
    "dry_run": ("pipeline", "dry_run"),
    "render_visualizations": ("pipeline", "render_visualizations"),
    "incremental_since": ("pipeline", "incremental_since"),
    "min_confidence": ("pipeline", "min_confidence"),
    "profiling_enabled": ("pipeline", "profiling_enabled"),
    "upstream_gnn_validation": ("pipeline", "upstream_gnn_validation"),
    "upstream_gnn_pipeline": ("pipeline", "upstream_gnn_pipeline"),
    "coverage_path": ("pipeline", "coverage_path"),
    "trace_path": ("pipeline", "trace_path"),
    # Export / validation / service settings.
    "primary_format": ("export", "primary_format"),
    "additional_formats": ("export", "additional_formats"),
    "create_bundle": ("export", "create_bundle"),
    "bundle_name": ("export", "bundle_name"),
    "compression": ("export", "compression"),
    "compression_level": ("export", "compression_level"),
    "include_provenance": ("export", "include_provenance"),
    "include_metadata": ("export", "include_metadata"),
    "include_statistics": ("export", "include_statistics"),
    "minify_json": ("export", "minify_json"),
    "validation_level": ("validation", "level"),
    "validate_schema": ("validation", "validate_schema"),
    "validate_references": ("validation", "validate_references"),
    "fail_on_error": ("validation", "fail_on_error"),
    "host": ("server", "host"),
    "port": ("server", "port"),
    "workspace_root": ("server", "workspace_root"),
    "allow_absolute_paths": ("server", "allow_absolute_paths"),
    "auth_token": ("server", "auth_token"),
    "max_request_bytes": ("server", "max_request_bytes"),
    "max_gnn_text_bytes": ("server", "max_gnn_text_bytes"),
    "max_archive_bytes": ("server", "max_archive_bytes"),
    "max_archive_files": ("server", "max_archive_files"),
    "max_concurrent_requests": ("server", "max_concurrent_requests"),
    "request_timeout_seconds": ("server", "request_timeout_seconds"),
    "rate_limit_requests": ("server", "rate_limit_requests"),
    "rate_limit_window_seconds": ("server", "rate_limit_window_seconds"),
}

_LEGACY_ENV_FIELDS = {
    f"COGANT_{name.upper()}": path for name, path in _LEGACY_FLAT_FIELDS.items()
}


class ConfigLoadError(ValueError):
    """Raised when a configuration source cannot produce a valid model."""


def _normalize_legacy_mapping(data: Mapping[str, Any], source: str) -> dict[str, Any]:
    """Translate legacy flat fields into the canonical sectioned model.

    The translation happens before precedence merging so a legacy file,
    environment layer, or CLI overlay participates in exactly the same
    ``defaults < preset < file < environment < CLI`` chain as canonical data.
    Canonical nested fields win when both spellings are supplied in one layer.
    """

    result = dict(data)
    raw_version = result.get("schema_version")
    if raw_version is not None:
        version = str(raw_version)
        major_text, separator, _minor_text = version.partition(".")
        if not separator or not major_text.isdigit() or int(major_text) > 1:
            raise ConfigLoadError(
                f"Unsupported configuration schema_version {version!r} in {source}; "
                f"supported versions are 0.x and 1.x"
            )
    result["schema_version"] = CURRENT_CONFIG_SCHEMA_VERSION

    migrated: list[str] = []
    for field_name, (section, canonical_name) in _LEGACY_FLAT_FIELDS.items():
        if field_name not in result:
            continue
        value = result.pop(field_name)
        target = result.setdefault(section, {})
        if not isinstance(target, Mapping):
            raise ConfigLoadError(f"Configuration section {section!r} in {source} must be an object")
        if canonical_name not in target:
            target[canonical_name] = value
        migrated.append(f"{field_name} -> {section}.{canonical_name}")

    if migrated:
        warnings.warn(
            "Legacy flat configuration fields were normalized for one "
            f"deprecation cycle ({source}): {', '.join(migrated)}",
            ConfigMigrationWarning,
            stacklevel=3,
        )
    return result


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(result.get(key), Mapping) and isinstance(value, Mapping):
            result[key] = _deep_merge(result[key], value)  # type: ignore[arg-type]
        else:
            result[key] = value
    return result


def _require_mapping(data: Any, source: str) -> dict[str, Any]:
    if not isinstance(data, Mapping) or isinstance(data, (list, tuple)):
        raise ConfigLoadError(f"Configuration at {source} must be a mapping/object")
    return dict(data)


class ConfigLoader:
    """Build validated :class:`ProjectConfig` objects at every public boundary."""

    @staticmethod
    def _read_yaml(path: str | Path) -> dict[str, Any]:
        if yaml is None:
            raise ConfigLoadError("PyYAML is not installed; install the YAML extra")
        try:
            with Path(path).open(encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle)
        except FileNotFoundError as exc:
            raise ConfigLoadError(f"Configuration file not found: {path}") from exc
        except (OSError, UnicodeDecodeError) as exc:
            raise ConfigLoadError(f"Could not read configuration {path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise ConfigLoadError(f"Invalid YAML in {path}: {exc}") from exc
        return _require_mapping({} if loaded is None else loaded, str(path))

    @staticmethod
    def _read_json(path: str | Path) -> dict[str, Any]:
        try:
            with Path(path).open(encoding="utf-8") as handle:
                loaded = json.load(handle)
        except FileNotFoundError as exc:
            raise ConfigLoadError(f"Configuration file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigLoadError(f"Invalid JSON in {path}: {exc}") from exc
        except (OSError, UnicodeDecodeError) as exc:
            raise ConfigLoadError(f"Could not read configuration {path}: {exc}") from exc
        return _require_mapping(loaded, str(path))

    @staticmethod
    def _read_file(path: str | Path) -> dict[str, Any]:
        suffix = Path(path).suffix.lower()
        if suffix == ".json":
            return ConfigLoader._read_json(path)
        if suffix in {".yaml", ".yml"}:
            return ConfigLoader._read_yaml(path)
        raise ConfigLoadError(f"Configuration file must end in .json, .yaml, or .yml: {path}")

    @staticmethod
    def _environment(values: Mapping[str, str]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, raw in values.items():
            if not key.startswith("COGANT_"):
                continue
            parts = key.removeprefix("COGANT_").split("__")
            if len(parts) == 1 and key in _LEGACY_ENV_FIELDS:
                section, field = _LEGACY_ENV_FIELDS[key]
                warnings.warn(
                    f"Legacy environment variable {key} is deprecated; use "
                    f"COGANT_{section.upper()}__{field.upper()}",
                    ConfigMigrationWarning,
                    stacklevel=3,
                )
            elif len(parts) != 2 or not all(parts):
                raise ConfigLoadError(
                    f"Environment key {key!r} must use COGANT_SECTION__FIELD syntax"
                )
            else:
                section, field = (part.lower() for part in parts)
            try:
                value: Any = json.loads(raw)
            except json.JSONDecodeError:
                value = raw
            result.setdefault(section, {})[field] = value
        return result

    @staticmethod
    def _base(preset: str) -> dict[str, Any]:
        try:
            selected = PRESETS[preset]
        except KeyError as exc:
            available = ", ".join(PRESETS)
            raise ConfigLoadError(f"Unknown preset '{preset}'. Available: {available}") from exc
        return selected.model_dump(mode="python")

    @staticmethod
    def load_project_config(
        path: str | Path | None = None,
        *,
        preset: str = "default",
        overrides: Mapping[str, Any] | None = None,
        environment: Mapping[str, str] | None = None,
        cli: Mapping[str, Any] | None = None,
    ) -> ProjectConfig:
        """Load one validated model using defaults < preset < file < env < CLI."""
        data = ConfigLoader._base(preset)
        if path is not None:
            data = _deep_merge(
                data,
                _normalize_legacy_mapping(ConfigLoader._read_file(path), str(path)),
            )
        env_data = ConfigLoader._environment(environment if environment is not None else os.environ)
        data = _deep_merge(data, env_data)
        if overrides is not None:
            data = _deep_merge(data, _normalize_legacy_mapping(overrides, "overrides"))
        if cli is not None:
            data = _deep_merge(data, _normalize_legacy_mapping(cli, "CLI"))
        try:
            return ProjectConfig.model_validate(data)
        except Exception as exc:  # Pydantic exposes several validation subclasses
            raise ConfigLoadError(f"Invalid project configuration: {exc}") from exc

    @staticmethod
    def load_from_yaml(path: str | Path) -> ProjectConfig:
        """Load and validate a YAML project configuration."""
        return ConfigLoader.load_project_config(path)

    @staticmethod
    def load_json_from_file(path: str | Path) -> ProjectConfig:
        """Load and validate a JSON project configuration."""
        return ConfigLoader.load_project_config(path)

    @staticmethod
    def load_from_dict(data: Mapping[str, Any]) -> ProjectConfig:
        """Validate an in-memory project configuration."""
        if not isinstance(data, Mapping):
            raise ConfigLoadError("Configuration must be a mapping/object")
        return ConfigLoader.load_project_config(overrides=data)

    @staticmethod
    def merge_configs(
        base: Mapping[str, Any], override: Mapping[str, Any], deep: bool = True
    ) -> dict[str, Any]:
        """Merge raw boundary mappings; validation occurs through a loader method."""
        if not isinstance(base, Mapping) or not isinstance(override, Mapping):
            raise ConfigLoadError("Both configuration layers must be mappings")
        if deep:
            return _deep_merge(base, override)
        result = dict(base)
        result.update(override)
        return result

    @staticmethod
    def load_default() -> ProjectConfig:
        return ConfigLoader.load_project_config()

    @staticmethod
    def load_preset(name: str) -> ProjectConfig:
        try:
            return PRESETS[name]
        except KeyError as exc:
            available = ", ".join(PRESETS)
            raise ConfigLoadError(f"Unknown preset '{name}'. Available: {available}") from exc

    @staticmethod
    def build_cogant_config(
        config_dict: Mapping[str, Any] | None = None, preset: str | None = None
    ) -> CogantConfig:
        return ConfigLoader.load_project_config(
            preset=preset or "default", overrides=config_dict or {}
        ).cogant

    @staticmethod
    def build_pipeline_config(
        config_dict: Mapping[str, Any] | None = None, preset: str | None = None
    ) -> PipelineConfig:
        return ConfigLoader.load_project_config(
            preset=preset or "default", overrides=config_dict or {}
        ).pipeline

    @staticmethod
    def build_export_config(
        config_dict: Mapping[str, Any] | None = None, preset: str | None = None
    ) -> ExportConfig:
        return ConfigLoader.load_project_config(
            preset=preset or "default", overrides=config_dict or {}
        ).export

    @staticmethod
    def build_validation_config(
        config_dict: Mapping[str, Any] | None = None, preset: str | None = None
    ) -> ValidationConfig:
        return ConfigLoader.load_project_config(
            preset=preset or "default", overrides=config_dict or {}
        ).validation

    @staticmethod
    def load_all_configs(
        yaml_path: str | Path | None = None, preset: str | None = None
    ) -> ProjectConfig:
        """Deprecated-shaped entry point returning the canonical project model."""
        return ConfigLoader.load_project_config(yaml_path, preset=preset or "default")
