from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class ModuleCouplingMetrics:
    module_name: str
    file_path: Path
    afferent_coupling: int = 0
    efferent_coupling: int = 0
    instability: float = 0.0
    abstractness: float = 0.0
    distance_from_main_sequence: float = 0.0
    abstract_classes: int = 0
    concrete_classes: int = 0
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class CouplingReport:
    package_name: str
    modules: list[ModuleCouplingMetrics] = field(default_factory=list)
    average_instability: float = 0.0
    average_abstractness: float = 0.0
    average_distance: float = 0.0
    errors: list[str] = field(default_factory=list)
    def get_unstable_modules(self, threshold: float = 0.8) -> list[ModuleCouplingMetrics]: ...
    def get_zone_of_pain(self) -> list[ModuleCouplingMetrics]: ...
    def get_zone_of_uselessness(self) -> list[ModuleCouplingMetrics]: ...

class CouplingAnalyzer:
    def __init__(self) -> None: ...
    def analyze(
        self,
        import_graph: dict[str, set[str]],
        abstract_classes: dict[str, int] | None = None,
        concrete_classes: dict[str, int] | None = None,
        package_name: str = "unknown",
    ) -> CouplingReport: ...
