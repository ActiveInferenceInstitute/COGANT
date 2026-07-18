from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .pipeline import PipelineConfig as PipelineConfig
from .schema import CogantConfig as CogantConfig
from .schema import ExportConfig as ExportConfig
from .schema import ProjectConfig as ProjectConfig
from .schema import ValidationConfig as ValidationConfig

HAS_YAML: bool

class ConfigMigrationWarning(DeprecationWarning): ...
class ConfigLoadError(Exception): ...

class ConfigLoader:
    @staticmethod
    def load_from_yaml(path: str | Path) -> ProjectConfig: ...
    @staticmethod
    def load_from_dict(data: Mapping[str, Any]) -> ProjectConfig: ...
    @staticmethod
    def load_json_from_file(path: str | Path) -> ProjectConfig: ...
    @staticmethod
    def merge_configs(
        base: Mapping[str, Any], override: Mapping[str, Any], deep: bool = True
    ) -> dict[str, Any]: ...
    @staticmethod
    def load_default() -> ProjectConfig: ...
    @staticmethod
    def load_preset(name: str) -> ProjectConfig: ...
    @staticmethod
    def build_cogant_config(
        config_dict: Mapping[str, Any] | None = None, preset: str | None = None
    ) -> CogantConfig: ...
    @staticmethod
    def build_pipeline_config(
        config_dict: Mapping[str, Any] | None = None, preset: str | None = None
    ) -> PipelineConfig: ...
    @staticmethod
    def build_export_config(
        config_dict: Mapping[str, Any] | None = None, preset: str | None = None
    ) -> ExportConfig: ...
    @staticmethod
    def build_validation_config(
        config_dict: Mapping[str, Any] | None = None, preset: str | None = None
    ) -> ValidationConfig: ...
    @staticmethod
    def load_all_configs(
        yaml_path: str | Path | None = None, preset: str | None = None
    ) -> ProjectConfig: ...
    @staticmethod
    def load_project_config(
        path: str | Path | None = None,
        *,
        preset: str = "default",
        overrides: Mapping[str, Any] | None = None,
        environment: Mapping[str, str] | None = None,
        cli: Mapping[str, Any] | None = None,
    ) -> ProjectConfig: ...
