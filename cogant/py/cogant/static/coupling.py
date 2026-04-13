"""Coupling metrics: instability, abstractness, and distance from main sequence."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ModuleCouplingMetrics:
    """Coupling metrics for a single module."""

    module_name: str
    """Module name."""

    file_path: Path
    """Source file path."""

    afferent_coupling: int = 0
    """Ca: number of modules that depend on this module."""

    efferent_coupling: int = 0
    """Ce: number of modules this module depends on."""

    instability: float = 0.0
    """I = Ce / (Ca + Ce), range [0, 1]. 0 = maximally stable."""

    abstractness: float = 0.0
    """A = abstract_classes / total_classes. Range [0, 1]."""

    distance_from_main_sequence: float = 0.0
    """D = |A + I - 1|. Ideal is 0, range [0, 1]."""

    abstract_classes: int = 0
    """Count of abstract classes/interfaces."""

    concrete_classes: int = 0
    """Count of concrete classes."""

    dependencies: set[str] = field(default_factory=set)
    """Set of modules this module depends on."""

    dependents: set[str] = field(default_factory=set)
    """Set of modules that depend on this module."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


@dataclass
class CouplingReport:
    """Aggregated coupling metrics for a package."""

    package_name: str
    """Package name."""

    modules: list[ModuleCouplingMetrics] = field(default_factory=list)
    """Per-module coupling metrics."""

    average_instability: float = 0.0
    """Average instability across all modules."""

    average_abstractness: float = 0.0
    """Average abstractness across all modules."""

    average_distance: float = 0.0
    """Average distance from main sequence."""

    errors: list[str] = field(default_factory=list)
    """Errors encountered during analysis."""

    def get_unstable_modules(self, threshold: float = 0.8) -> list[ModuleCouplingMetrics]:
        """Get modules with high instability.

        Args:
            threshold: Instability threshold (default 0.8).

        Returns:
            Sorted list of unstable modules.
        """
        unstable = [m for m in self.modules if m.instability >= threshold]
        return sorted(unstable, key=lambda m: m.instability, reverse=True)

    def get_zone_of_pain(self) -> list[ModuleCouplingMetrics]:
        """Get modules in zone of pain (high concrete + high instability).

        Returns:
            Modules where distance > 0.3 and instability > 0.8.
        """
        return [m for m in self.modules if m.distance_from_main_sequence > 0.3 and m.instability > 0.8]

    def get_zone_of_uselessness(self) -> list[ModuleCouplingMetrics]:
        """Get modules in zone of uselessness (high abstract + low use).

        Returns:
            Modules where distance > 0.3 and instability < 0.2.
        """
        return [m for m in self.modules if m.distance_from_main_sequence > 0.3 and m.instability < 0.2]


class CouplingAnalyzer:
    """Analyze module coupling and stability metrics."""

    def __init__(self) -> None:
        """Initialize coupling analyzer."""
        pass

    def analyze(
        self,
        import_graph: dict[str, set[str]],
        abstract_classes: dict[str, int] | None = None,
        concrete_classes: dict[str, int] | None = None,
        package_name: str = "unknown",
    ) -> CouplingReport:
        """Analyze coupling metrics.

        Args:
            import_graph: Dict mapping module name to set of modules it imports.
            abstract_classes: Optional dict mapping module to abstract class count.
            concrete_classes: Optional dict mapping module to concrete class count.
            package_name: Package name for report.

        Returns:
            CouplingReport with coupling metrics.
        """
        if abstract_classes is None:
            abstract_classes = {}
        if concrete_classes is None:
            concrete_classes = {}

        report = CouplingReport(package_name=package_name)

        # Compute afferent coupling (Ca) for each module
        afferent: dict[str, set[str]] = {}
        for module_name, imports in import_graph.items():
            if module_name not in afferent:
                afferent[module_name] = set()
            for imported in imports:
                if imported not in afferent:
                    afferent[imported] = set()
                afferent[imported].add(module_name)

        # Build metrics for each module
        all_modules = set(import_graph.keys()) | set(afferent.keys())
        for module_name in all_modules:
            ce = len(import_graph.get(module_name, set()))
            ca = len(afferent.get(module_name, set()))

            # Compute instability
            total = ca + ce
            i = ce / total if total > 0 else 0.0

            # Compute abstractness
            abstract = abstract_classes.get(module_name, 0)
            concrete = concrete_classes.get(module_name, 0)
            total_classes = abstract + concrete
            a = abstract / total_classes if total_classes > 0 else 0.0

            # Distance from main sequence
            d = abs(a + i - 1.0)

            metrics = ModuleCouplingMetrics(
                module_name=module_name,
                file_path=Path(module_name),
                afferent_coupling=ca,
                efferent_coupling=ce,
                instability=i,
                abstractness=a,
                distance_from_main_sequence=d,
                abstract_classes=abstract,
                concrete_classes=concrete,
                dependencies=import_graph.get(module_name, set()),
                dependents=afferent.get(module_name, set()),
            )
            report.modules.append(metrics)

        # Compute aggregates
        if report.modules:
            i_values = [m.instability for m in report.modules]
            a_values = [m.abstractness for m in report.modules]
            d_values = [m.distance_from_main_sequence for m in report.modules]
            report.average_instability = sum(i_values) / len(i_values)
            report.average_abstractness = sum(a_values) / len(a_values)
            report.average_distance = sum(d_values) / len(d_values)

        return report
