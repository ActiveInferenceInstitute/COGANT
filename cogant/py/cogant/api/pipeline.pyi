from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cogant.api.bundle import Bundle
from cogant.config.pipeline import PipelineConfig as PipelineConfig

class PipelineRunner:
    stage_handlers: dict[str, Callable[..., Any]]
    def __init__(self) -> None: ...
    def run(self, target: str, config: PipelineConfig | None = None) -> Bundle: ...

@dataclass
class PipelineResult:
    bundle: Bundle
    timing: dict[str, float] = field(default_factory=dict)
    stage_outputs: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    total_duration_ms: float = ...
