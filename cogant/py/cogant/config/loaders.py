"""Strict configuration loading with one deterministic precedence chain."""

from __future__ import annotations

import json
import logging
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
    CogantConfig,
    ExportConfig,
    ProjectConfig,
    ValidationConfig,
)

HAS_YAML = yaml is not None


class ReservedConfigWarning(UserWarning):
    """Warning emitted when a configuration sets a reserved, unconsumed key.

    The per-stage ``pipeline`` sections listed in
    ``_RESERVED_PIPELINE_SECTIONS`` are validated and carried on
    :class:`PipelineConfig`, but no pipeline stage reads them yet, so a value
    set there has no effect on a run.
    """


# Validated per-stage sub-configs that no stage handler consumes yet.
_RESERVED_PIPELINE_SECTIONS: tuple[str, ...] = (
    "ingest",
    "graph",
    "translate",
    "statespace",
    "gnn",
    "reverse",
)


def _warn_reserved_keys(layer: Mapping[str, Any], source: str) -> None:
    """Warn when a user-supplied layer sets a reserved per-stage key."""
    pipeline = layer.get("pipeline")
    if not isinstance(pipeline, Mapping):
        return
    keys: list[str] = []
    for section in _RESERVED_PIPELINE_SECTIONS:
        value = pipeline.get(section)
        if isinstance(value, Mapping):
            keys.extend(f"pipeline.{section}.{field}" for field in value)
        elif value is not None:
            keys.append(f"pipeline.{section}")
    if keys:
        warnings.warn(
            f"Reserved configuration keys have no effect yet ({source}): "
            f"{', '.join(keys)}. They are validated, but no pipeline stage reads them.",
            ReservedConfigWarning,
            stacklevel=3,
        )


# Section names that ``COGANT_<SECTION>__<FIELD>`` environment keys may target.
_CONFIG_SECTIONS = frozenset(
    name for name in ProjectConfig.model_fields if name != "schema_version"
)

logger = logging.getLogger(__name__)


class ConfigLoadError(ValueError):
    """Raised when a configuration source cannot produce a valid model."""


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
        """Collect the environment configuration layer from ``COGANT_*`` keys.

        Only ``COGANT_<SECTION>__<FIELD>`` keys configure this model.
        Single-segment keys are runtime toggles owned by their subsystems.
        Keys that use the double-underscore syntax remain strict: a malformed
        key or unknown section raises :class:`ConfigLoadError`, and unknown
        fields are rejected by model validation.
        """
        result: dict[str, Any] = {}
        for key, raw in values.items():
            if not key.startswith("COGANT_"):
                continue
            name = key.removeprefix("COGANT_")
            if "__" not in name:
                logger.debug("Ignoring non-configuration environment toggle %s", key)
                continue
            else:
                parts = name.split("__")
                if len(parts) != 2 or not all(parts):
                    raise ConfigLoadError(
                        f"Environment key {key!r} must use COGANT_SECTION__FIELD syntax"
                    )
                section, field = (part.lower() for part in parts)
                if section not in _CONFIG_SECTIONS:
                    raise ConfigLoadError(
                        f"Environment key {key!r} names unknown configuration section "
                        f"{section!r}; expected one of: {', '.join(sorted(_CONFIG_SECTIONS))}"
                    )
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
        """Load one validated model using defaults < preset < file < env < CLI.

        User-supplied layers (file, environment, overrides, CLI) that set a
        reserved per-stage ``pipeline`` section emit a
        :class:`ReservedConfigWarning`; presets never do.
        """
        data = ConfigLoader._base(preset)
        if path is not None:
            file_data = ConfigLoader._read_file(path)
            _warn_reserved_keys(file_data, str(path))
            data = _deep_merge(data, file_data)
        env_data = ConfigLoader._environment(environment if environment is not None else os.environ)
        _warn_reserved_keys(env_data, "environment")
        data = _deep_merge(data, env_data)
        if overrides is not None:
            override_data = dict(overrides)
            _warn_reserved_keys(override_data, "overrides")
            data = _deep_merge(data, override_data)
        if cli is not None:
            cli_data = dict(cli)
            _warn_reserved_keys(cli_data, "CLI")
            data = _deep_merge(data, cli_data)
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
