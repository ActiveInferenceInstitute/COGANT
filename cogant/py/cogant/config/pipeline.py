"""Composite pipeline configuration.

One :class:`PipelineConfig` per pipeline run. It bundles per-stage
sub-configs (ingest, graph, translate, statespace, gnn, reverse)
together with the top-level execution flags that ``PipelineRunner``
understands (``stages``, ``skip_stages``, ``skip_dynamic``, output
locations, dynamic-stage data paths, etc.).

This class is a *superset* of the compatibility
``cogant.api.pipeline.PipelineConfig`` dataclass: any kwargs that used
to work on the dataclass also work here, so existing call-sites such
as ``PipelineConfig(stages=[...], skip_dynamic=True)`` keep behaving
the same way.

Pipeline configs are validated models. Entry points may derive a run-specific
instance after applying their final CLI values, while all external sources are
validated before execution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cogant.translate.confidence import ConfidenceModel

from .gnn import GNNConfig
from .graph import GraphConfig
from .ingest import IngestConfig
from .reverse import ReverseConfig
from .statespace import StatespaceConfig
from .translate import TranslateConfig

_DEFAULT_STAGES: list[str] = [
    "ingest",
    "static",
    "normalize",
    "graph",
    "dynamic",
    "translate",
    "statespace",
    "process",
    "export",
    "validate",
]

_VALID_STAGES = frozenset(_DEFAULT_STAGES)


def _validate_path_text(value: str) -> str:
    if not value.strip() or "\x00" in value:
        raise ValueError("path values must be non-empty and NUL-free")
    if ".." in Path(value).parts:
        raise ValueError("path traversal components are not permitted")
    return value


class PipelineConfig(BaseModel):
    """Composite config — one per pipeline run.

    Top-level execution fields mirror the compatibility
    ``cogant.api.pipeline.PipelineConfig`` dataclass so existing
    call-sites continue to work unchanged.

    Nested fields (``ingest``, ``graph``, ``translate``, ``statespace``,
    ``gnn``, ``reverse``) carry per-stage parameters as frozen
    sub-configs. Each defaults to its own ``<Stage>Config()``.
    """

    # --- Execution plan -------------------------------------------------
    stages: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_STAGES),
        description="Stages to execute in order",
    )
    skip_stages: list[str] = Field(
        default_factory=list,
        description="Stages to skip entirely for this run",
    )
    skip_dynamic: bool = Field(
        default=False,
        description="Short-circuit the dynamic-analysis stage",
    )

    # --- Output ---------------------------------------------------------
    output_dir: str = Field(
        default="output",
        description="Output directory for artifacts",
    )
    layout_output: bool = Field(
        default=False,
        description="Reorganize flat output into data/diagrams/... subdirs",
    )

    # --- Runtime flags --------------------------------------------------
    verbose: bool = Field(default=False, description="Verbose logging")
    dry_run: bool = Field(default=False, description="Do not produce side effects")

    render_visualizations: bool = Field(
        default=True,
        description="Render raster visualizations during export",
    )

    incremental_since: str | None = Field(default=None)
    cache_dir: str | None = Field(default=None)
    min_confidence: float = Field(
        default=ConfidenceModel.RUNTIME_ONLY_THRESHOLD,
        ge=0.0,
        le=1.0,
    )
    profiling_enabled: bool = Field(default=False)
    upstream_gnn_validation: bool = Field(default=False)
    upstream_gnn_pipeline: bool = Field(default=False)
    upstream_gnn_only_steps: list[int] | None = Field(default=None)
    upstream_gnn_skip_steps: list[int] = Field(default_factory=lambda: [11, 12])
    upstream_gnn_output_dir: str | None = Field(default=None)
    upstream_gnn_frameworks: str = Field(default="lite", min_length=1)
    upstream_gnn_llm_model: str | None = Field(default=None)

    # --- Dynamic-stage inputs ------------------------------------------
    coverage_path: str | None = Field(
        default=None,
        description="Explicit coverage database path for the dynamic stage",
    )
    trace_path: str | None = Field(
        default=None,
        description="Explicit Chrome DevTools trace path for the dynamic stage",
    )
    plugins: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Per-plugin configuration payloads",
    )

    # --- Per-stage sub-configs -----------------------------------------
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    translate: TranslateConfig = Field(default_factory=TranslateConfig)
    statespace: StatespaceConfig = Field(default_factory=StatespaceConfig)
    gnn: GNNConfig = Field(default_factory=GNNConfig)
    reverse: ReverseConfig = Field(default_factory=ReverseConfig)

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @field_validator("stages", "skip_stages")
    @classmethod
    def validate_stage_names(cls, values: list[str]) -> list[str]:
        """Reject unknown, blank, and duplicate execution stage names."""
        unknown = sorted(set(values) - _VALID_STAGES)
        if unknown:
            raise ValueError(f"unknown pipeline stages: {unknown}")
        if any(not stage.strip() for stage in values):
            raise ValueError("pipeline stage names must not be blank")
        if len(values) != len(set(values)):
            raise ValueError("pipeline stages must be unique")
        return values

    @field_validator(
        "output_dir",
        "cache_dir",
        "coverage_path",
        "trace_path",
        "upstream_gnn_output_dir",
        "upstream_gnn_frameworks",
    )
    @classmethod
    def validate_nonempty_path_or_value(cls, value: str | None) -> str | None:
        """Reject empty output/configuration values before execution."""
        return None if value is None else _validate_path_text(value)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PipelineConfig:
        """Build a :class:`PipelineConfig` from a plain dictionary.

        Nested sub-config dicts (``ingest``, ``graph``, ...) are passed
        through pydantic, which coerces them into the corresponding
        typed sub-config models.
        """
        return cls.model_validate(d)

    @classmethod
    def from_yaml(cls, path: str | Path) -> PipelineConfig:
        """Build a :class:`PipelineConfig` from a YAML file.

        Requires ``pyyaml``; a clear :class:`ImportError` is raised if
        it is not installed.
        """
        try:
            import yaml  # type: ignore[import-not-found,import-untyped,unused-ignore]
        except ImportError as exc:  # pragma: no cover - exercised via skipif
            raise ImportError(
                "PipelineConfig.from_yaml requires pyyaml; install with `pip install pyyaml`"
            ) from exc

        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(f"YAML config at {path} must be a mapping, got {type(data).__name__}")
        return cls.from_dict(data)

    @classmethod
    def from_json(cls, path: str | Path) -> PipelineConfig:
        """Build a :class:`PipelineConfig` from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"JSON config at {path} must be an object, got {type(data).__name__}")
        return cls.from_dict(data)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict round-trippable representation."""
        return self.model_dump(mode="python")

    def to_yaml(self, path: str | Path) -> None:
        """Write this config to a YAML file.

        Requires ``pyyaml``; a clear :class:`ImportError` is raised if
        it is not installed.
        """
        try:
            import yaml  # type: ignore[import-not-found,import-untyped,unused-ignore]
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "PipelineConfig.to_yaml requires pyyaml; install with `pip install pyyaml`"
            ) from exc

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            yaml.safe_dump(self.to_dict(), sort_keys=False),
            encoding="utf-8",
        )

    def to_json(self, path: str | Path) -> None:
        """Write this config to a JSON file."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def validate(self) -> list[str]:
        """Return non-throwing run-time checks for legacy callers.

        Construction remains the fail-fast boundary for schema, type, path,
        and stage-name errors.  This method is retained as a compatibility
        diagnostic surface for callers that historically validated an already
        constructed config before dispatching a run.
        """
        errors: list[str] = []
        unknown = sorted(set(self.stages) - _VALID_STAGES)
        errors.extend(f"Unknown stage: {stage}" for stage in unknown)
        unknown_skips = sorted(set(self.skip_stages) - _VALID_STAGES)
        errors.extend(f"Unknown skip_stage: {stage}" for stage in unknown_skips)
        output = Path(self.output_dir)
        if output.exists() and not output.is_dir():
            errors.append("output_dir exists but is not a directory")
        for field_name in ("coverage_path", "trace_path"):
            value = getattr(self, field_name)
            if value is not None and not Path(value).exists():
                errors.append(f"{field_name} does not exist")
        for field_name, values in (
            ("upstream_gnn_only_steps", self.upstream_gnn_only_steps),
            ("upstream_gnn_skip_steps", self.upstream_gnn_skip_steps),
        ):
            if values is not None and any(step < 0 or step > 12 for step in values):
                errors.append(f"{field_name} contains an out-of-range step")
        return errors

    def with_profiling(self) -> PipelineConfig:
        """Return an independent copy with profiling enabled."""
        return self.model_copy(deep=True, update={"profiling_enabled": True})

    # ------------------------------------------------------------------
    # Immutable-update helpers
    # ------------------------------------------------------------------

    def override(self, **kwargs: Any) -> PipelineConfig:
        """Return a new config with top-level fields overridden.

        Unknown fields raise :class:`ValueError` immediately so typos
        don't silently survive as no-ops.
        """
        unknown = set(kwargs) - set(type(self).model_fields)
        if unknown:
            raise ValueError(f"Unknown PipelineConfig fields: {sorted(unknown)}")
        return self.model_copy(update=kwargs)
