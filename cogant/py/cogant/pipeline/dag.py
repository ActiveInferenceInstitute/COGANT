"""DAG-based pipeline execution engine.

Stages declare dependencies and are executed in topological order
(Kahn's algorithm). If a stage fails, all transitive dependents are
skipped. Pure stdlib -- no external graph libraries.
"""

from __future__ import annotations

import enum
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class StageStatus(enum.Enum):
    """Outcome of a single stage execution."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class Stage:
    """A named pipeline stage with optional dependencies.

    Parameters
    ----------
    name:
        Unique identifier for this stage.
    fn:
        Callable ``(context: dict) -> dict`` that returns context updates.
    deps:
        Names of stages that must complete before this one runs.
    timeout:
        Maximum wall-clock seconds (reserved for future async support).
    """

    name: str
    fn: Callable[[dict[str, Any]], dict[str, Any]]
    deps: list[str] = field(default_factory=list)
    timeout: float = 60.0


@dataclass
class StageResult:
    """Result of executing a single stage."""

    name: str
    status: StageStatus
    elapsed: float = 0.0
    error: str | None = None
    output: dict[str, Any] = field(default_factory=dict)


@dataclass
class DAGResult:
    """Aggregate result of a full pipeline run."""

    stage_results: dict[str, StageResult] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    elapsed: float = 0.0


class PipelineDAG:
    """DAG-based pipeline that resolves stage dependencies via Kahn's algorithm."""

    def __init__(self) -> None:
        self._stages: dict[str, Stage] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_stage(self, stage: Stage) -> None:
        """Register a stage. Raises ``ValueError`` on duplicate names."""
        if stage.name in self._stages:
            raise ValueError(f"Duplicate stage name: {stage.name!r}")
        self._stages[stage.name] = stage

    def run(self, context: dict[str, Any]) -> DAGResult:
        """Execute all stages in topological order.

        Parameters
        ----------
        context:
            Initial shared state passed to stages. Each stage receives
            the accumulated context and may return updates that are
            merged in for subsequent stages.

        Returns
        -------
        DAGResult
            Aggregate outcome including per-stage results.
        """
        if not self._stages:
            return DAGResult()

        self._validate_deps()
        self._validate_no_cycles()
        order = self._topological_sort()

        t0 = time.monotonic()
        ctx = dict(context)
        results: dict[str, StageResult] = {}
        errors: list[str] = []
        failed_ancestors: set[str] = set()

        for name in order:
            stage = self._stages[name]

            # Skip if any dependency failed or was skipped.
            if any(dep in failed_ancestors for dep in stage.deps):
                results[name] = StageResult(
                    name=name,
                    status=StageStatus.SKIPPED,
                    error="Dependency failed",
                )
                failed_ancestors.add(name)
                continue

            # Execute stage.
            st = time.monotonic()
            try:
                output = stage.fn(ctx)
                if not isinstance(output, dict):
                    output = {}
                ctx.update(output)
                results[name] = StageResult(
                    name=name,
                    status=StageStatus.SUCCESS,
                    elapsed=time.monotonic() - st,
                    output=output,
                )
            except Exception as exc:  # noqa: BLE001
                elapsed = time.monotonic() - st
                err_msg = f"Stage {name!r} failed: {exc}"
                errors.append(err_msg)
                results[name] = StageResult(
                    name=name,
                    status=StageStatus.FAILED,
                    elapsed=elapsed,
                    error=str(exc),
                )
                failed_ancestors.add(name)

        return DAGResult(
            stage_results=results,
            errors=errors,
            elapsed=time.monotonic() - t0,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _topological_sort(self) -> list[str]:
        """Kahn's algorithm -- iterative, no recursion.

        Ties are broken alphabetically for deterministic ordering.

        Returns
        -------
        List[str]
            Stage names in valid execution order.

        Raises
        ------
        ValueError
            If the graph contains a cycle.
        """
        in_degree: dict[str, int] = dict.fromkeys(self._stages, 0)
        dependents: dict[str, list[str]] = {name: [] for name in self._stages}

        for name, stage in self._stages.items():
            for dep in stage.deps:
                dependents[dep].append(name)
                in_degree[name] += 1

        # Seed with zero-in-degree nodes, sorted for determinism.
        queue: deque[str] = deque(sorted(n for n, d in in_degree.items() if d == 0))
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            # Process children in sorted order for determinism.
            for child in sorted(dependents[node]):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(order) != len(self._stages):
            # Remaining nodes form cycle(s).
            remaining = set(self._stages) - set(order)
            cycle_path = self._find_cycle(remaining)
            raise ValueError(f"Cycle detected in pipeline DAG: {' -> '.join(cycle_path)}")

        return order

    def _validate_no_cycles(self) -> None:
        """Validate that the DAG has no cycles.

        Delegates to ``_topological_sort`` which raises on cycles.
        """
        self._topological_sort()

    def _validate_deps(self) -> None:
        """Ensure every declared dependency references a known stage."""
        known = set(self._stages)
        for name, stage in self._stages.items():
            for dep in stage.deps:
                if dep not in known:
                    raise ValueError(f"Stage {name!r} depends on unknown stage {dep!r}")

    def _find_cycle(self, nodes: set[str]) -> list[str]:
        """Find one cycle among *nodes* for a useful error message."""
        visited: set[str] = set()
        path: list[str] = []

        def _dfs(n: str) -> list[str] | None:
            if n in visited:
                idx = path.index(n)
                return path[idx:] + [n]
            visited.add(n)
            path.append(n)
            for dep in self._stages[n].deps:
                if dep in nodes:
                    result = _dfs(dep)
                    if result is not None:
                        return result
            path.pop()
            return None

        for start in sorted(nodes):
            visited.clear()
            path.clear()
            result = _dfs(start)
            if result is not None:
                return result

        # Fallback: just list the nodes.
        return sorted(nodes)
