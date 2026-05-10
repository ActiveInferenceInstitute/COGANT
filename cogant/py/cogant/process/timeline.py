"""
Timeline construction for process visualization.

Builds stage sequences with expected ordering for Gantt visualization.
"""

import logging
from dataclasses import dataclass, field

from cogant.process.extractor import ProcessModel

logger = logging.getLogger(__name__)


@dataclass
class GanttStage:
    """A stage in a Gantt timeline visualization."""

    stage_id: str
    name: str
    start_time: float = 0.0  # Relative time in seconds
    duration: float = 1.0  # Expected duration in seconds
    dependencies: list[str] = field(default_factory=list)
    criticality: float = 0.5  # 0-1: how critical is this on the path


@dataclass
class Timeline:
    """Complete timeline for process execution."""

    stages: list[GanttStage]
    total_duration: float
    critical_path: list[str]
    parallel_groups: list[list[str]]  # Groups of stages that can run in parallel


class TimelineBuilder:
    """
    Constructs stage sequences with expected ordering for Gantt visualization.
    """

    def __init__(self, process_model: ProcessModel):
        """
        Initialize the builder.

        Args:
            process_model: The process model to build timeline for.
        """
        self.process_model = process_model
        self.gantt_stages: dict[str, GanttStage] = {}
        self.timeline: Timeline | None = None

    def build(self) -> Timeline:
        """
        Build a timeline from the process model.

        Returns:
            Constructed Timeline.
        """
        logger.info("Building process timeline...")

        # Create Gantt stages from process stages
        self._create_gantt_stages()

        # Assign time slots to stages
        self._assign_timing()

        # Find critical path
        critical_path = self._find_critical_path()

        # Mark stages on the critical path with criticality=1.0 so that
        # downstream Gantt/vis consumers can render them distinctly.
        critical_set = set(critical_path)
        for stage_id, gantt_stage in self.gantt_stages.items():
            if stage_id in critical_set:
                gantt_stage.criticality = 1.0

        # Identify parallel groups
        parallel_groups = self._identify_parallel_groups()

        # Compute total duration
        total_duration = self._compute_total_duration()

        self.timeline = Timeline(
            stages=list(self.gantt_stages.values()),
            total_duration=total_duration,
            critical_path=critical_path,
            parallel_groups=parallel_groups,
        )

        logger.info(f"Built timeline: {total_duration:.1f}s, {len(critical_path)} critical stages")
        return self.timeline

    def _create_gantt_stages(self) -> None:
        """
        Create Gantt stages from process model stages.

        Dependencies are taken from ``stage.entry_points`` when present,
        otherwise derived from :class:`ProcessConnection` objects so the
        builder works with either hand-built models or those produced by
        :class:`cogant.process.extractor.ProcessExtractor`.
        """
        # Derive fallback dependencies from connections in case entry_points
        # were not populated.
        derived_deps: dict[str, list[str]] = {sid: [] for sid in self.process_model.stages}
        for conn in self.process_model.connections.values():
            if (
                conn.source_stage_id in derived_deps
                and conn.target_stage_id in derived_deps
                and conn.source_stage_id != conn.target_stage_id
            ):
                if conn.source_stage_id not in derived_deps[conn.target_stage_id]:
                    derived_deps[conn.target_stage_id].append(conn.source_stage_id)

        for stage_id, stage in self.process_model.stages.items():
            deps = (
                list(stage.entry_points) if stage.entry_points else derived_deps.get(stage_id, [])
            )
            gantt_stage = GanttStage(
                stage_id=stage_id,
                name=stage.name,
                duration=stage.expected_duration or 1.0,
                dependencies=deps,
            )
            self.gantt_stages[stage_id] = gantt_stage

    def _assign_timing(self) -> None:
        """
        Assign start times to stages based on dependencies.

        Uses a pull-style DFS: for each stage, the start time is the
        maximum end time over its direct dependencies. Because this is
        recursive on predecessors, we must invoke it for every stage
        (not just the entry point) so downstream stages are reached
        through their dependency links.
        """
        visited: set[str] = set()
        time_map: dict[str, float] = {}

        def assign_time(stage_id: str) -> float:
            """Return the end time (start + duration) of ``stage_id``."""
            if stage_id not in self.gantt_stages:
                return 0.0
            if stage_id in time_map:
                return time_map[stage_id] + self.gantt_stages[stage_id].duration
            if stage_id in visited:
                # Cycle guard — treat the partially-assigned stage as 0.
                # Return the (start + duration) when a partial start has
                # been recorded, so callers see a consistent end-time
                # contract regardless of cycle position.
                start = time_map.get(stage_id, 0.0)
                return start + self.gantt_stages[stage_id].duration
            visited.add(stage_id)

            # Earliest start = max(end_time(dep) for dep in deps), or 0.
            max_end_time = 0.0
            for dep_id in self.gantt_stages[stage_id].dependencies:
                dep_end_time = assign_time(dep_id)
                if dep_end_time > max_end_time:
                    max_end_time = dep_end_time

            time_map[stage_id] = max_end_time
            self.gantt_stages[stage_id].start_time = max_end_time
            return max_end_time + self.gantt_stages[stage_id].duration

        # Walk every stage — pull-style DFS will visit predecessors first
        # and set their start times correctly before this stage is set.
        for stage_id in self.gantt_stages:
            assign_time(stage_id)

    def _find_critical_path(self) -> list[str]:
        """
        Find the critical path (longest path from entry to exit).

        Returns:
            List of stage IDs on the critical path.
        """
        # Compute longest path using dynamic programming
        entry_id = self.process_model.entry_stage_id
        if not entry_id:
            return []

        visited = set()
        path_cache: dict[str, tuple[float, list[str]]] = {}

        def longest_path_from(stage_id: str) -> tuple[float, list[str]]:
            """DP helper: return (max_length, path) reachable from ``stage_id``."""
            if stage_id in path_cache:
                return path_cache[stage_id]

            if stage_id in visited:
                return 0.0, []

            visited.add(stage_id)

            # Get this stage's duration
            stage_duration = (
                self.gantt_stages[stage_id].duration if stage_id in self.gantt_stages else 1.0
            )

            # Find longest path through successors
            max_length = stage_duration
            best_path = [stage_id]

            # Find successor stages
            for conn in self.process_model.connections.values():
                if conn.source_stage_id == stage_id:
                    succ_length, succ_path = longest_path_from(conn.target_stage_id)
                    total_length = stage_duration + succ_length
                    if total_length > max_length:
                        max_length = total_length
                        best_path = [stage_id] + succ_path

            path_cache[stage_id] = (max_length, best_path)
            return max_length, best_path

        _, critical_path = longest_path_from(entry_id)
        return critical_path

    def _identify_parallel_groups(self) -> list[list[str]]:
        """
        Identify groups of stages that can run in parallel.

        Stages can run in parallel if they have the same or overlapping
        time window and don't have dependencies on each other.

        Returns:
            List of stage ID lists representing parallel groups.
        """
        groups = []
        assigned = set()

        # Sort stages by start time
        sorted_stages = sorted(self.gantt_stages.values(), key=lambda s: s.start_time)

        for stage in sorted_stages:
            if stage.stage_id in assigned:
                continue

            # Find all stages that start at similar time and don't depend on each other
            group = [stage.stage_id]
            assigned.add(stage.stage_id)

            for other_stage in sorted_stages:
                if other_stage.stage_id in assigned:
                    continue

                # Check if can run in parallel
                if abs(other_stage.start_time - stage.start_time) < 0.1:  # Same start time
                    if self._can_run_in_parallel(stage.stage_id, other_stage.stage_id):
                        group.append(other_stage.stage_id)
                        assigned.add(other_stage.stage_id)

            if len(group) > 1:
                groups.append(group)

        return groups

    def _can_run_in_parallel(self, stage_id1: str, stage_id2: str) -> bool:
        """
        Check if two stages can run in parallel.

        Args:
            stage_id1: First stage ID.
            stage_id2: Second stage ID.

        Returns:
            True if they can run in parallel, False otherwise.
        """
        # They can't run in parallel if one depends on the other
        s1 = self.gantt_stages.get(stage_id1)
        s2 = self.gantt_stages.get(stage_id2)

        if not s1 or not s2:
            return True

        if stage_id2 in s1.dependencies or stage_id1 in s2.dependencies:
            return False

        return True

    def _compute_total_duration(self) -> float:
        """
        Compute total duration of the process.

        Returns:
            Total duration in seconds.
        """
        max_end_time = 0.0

        for stage in self.gantt_stages.values():
            end_time = stage.start_time + stage.duration
            if end_time > max_end_time:
                max_end_time = end_time

        return max_end_time

    def get_timeline(self) -> Timeline | None:
        """
        Get the constructed timeline.

        Returns:
            Timeline or None if not yet built.
        """
        return self.timeline

    def get_stage_at_time(self, time: float) -> str | None:
        """
        Get the stage ID active at a given time.

        Args:
            time: Time in seconds.

        Returns:
            Stage ID or None.
        """
        for stage in self.gantt_stages.values():
            if stage.start_time <= time < (stage.start_time + stage.duration):
                return stage.stage_id
        return None

    def get_stages_in_range(self, start_time: float, end_time: float) -> list[str]:
        """
        Get stages active during a time range.

        Args:
            start_time: Start time in seconds.
            end_time: End time in seconds.

        Returns:
            List of stage IDs active in range.
        """
        stages = []
        for stage in self.gantt_stages.values():
            stage_end = stage.start_time + stage.duration
            if stage.start_time < end_time and stage_end > start_time:
                stages.append(stage.stage_id)
        return stages

    def export_gantt_data(self) -> dict[str, object]:
        """
        Export timeline data in Gantt-friendly format.

        Returns:
            Dictionary with Gantt visualization data.
        """
        if not self.timeline:
            return {}

        return {
            "total_duration": self.timeline.total_duration,
            "stages": [
                {
                    "id": s.stage_id,
                    "name": s.name,
                    "start": s.start_time,
                    "duration": s.duration,
                    "dependencies": s.dependencies,
                }
                for s in self.timeline.stages
            ],
            "critical_path": self.timeline.critical_path,
            "parallel_groups": self.timeline.parallel_groups,
        }
