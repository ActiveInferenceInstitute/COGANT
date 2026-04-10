"""Composite pipeline configuration.

One :class:`PipelineConfig` per pipeline run. It bundles per-stage
sub-configs (ingest, graph, translate, statespace, gnn, reverse)
together with the top-level execution flags that ``PipelineRunner``
understands (``stages``, ``skip_stages``, ``skip_dynamic``, output
locations, dynamic-stage data paths, etc.).

This class is a *superset* of the legacy
``cogant.api.pipeline.PipelineConfig`` dataclass: any kwargs that used
to work on the dataclass also work here, so existing call-sites such
as ``PipelineConfig(stages=[...], skip_dynamic=True)`` keep behaving
the same way.

Pipeline configs are **frozen**. To change a field, use
:meth:`PipelineConfig.override`, which returns a new instance — never
mutate in place. This keeps configs safely shareable across concurrent
stages and avoids the "action at a distance" bugs that come with
globally-mutable config singletons.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
    "translate",
]


class PipelineConfig(BaseModel):
    """Composite config — one per pipeline run.

    Top-level execution fields mirror the legacy
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
        default=True,
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
    verbose: bool = Field(
        default=False, description="Verbose logging"
    )
    dry_run: bool = Field(
        default=False, description="Do not produce side effects"
    )

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

    model_config = ConfigDict(frozen=True)

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
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - exercised via skipif
            raise ImportError(
                "PipelineConfig.from_yaml requires pyyaml; "
                "install with `pip install pyyaml`"
            ) from exc

        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(
                f"YAML config at {path} must be a mapping, got {type(data).__name__}"
            )
        return cls.from_dict(data)

    @classmethod
    def from_json(cls, path: str | Path) -> PipelineConfig:
        """Build a :class:`PipelineConfig` from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(
                f"JSON config at {path} must be an object, got {type(data).__name__}"
            )
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
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "PipelineConfig.to_yaml requires pyyaml; "
                "install with `pip install pyyaml`"
            ) from exc

        Path(path).write_text(
            yaml.safe_dump(self.to_dict(), sort_keys=False),
            encoding="utf-8",
        )

    def to_json(self, path: str | Path) -> None:
        """Write this config to a JSON file."""
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

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
            raise ValueError(
                f"Unknown PipelineConfig fields: {sorted(unknown)}"
            )
        return self.model_copy(update=kwargs)
