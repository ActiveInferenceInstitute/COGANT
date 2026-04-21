"""Main workflow engine implementation."""

from dataclasses import dataclass, field
from datetime import datetime

from scheduler import ScheduleConfig, TaskScheduler
from state import StateMachine, WorkflowState
from tasks import Task


@dataclass
class WorkflowConfig:
    """Configuration for a workflow."""

    name: str
    description: str | None = None
    timeout_seconds: int = 3600
    allow_concurrent_tasks: bool = False


@dataclass
class WorkflowDefinition:
    """Definition of a workflow."""

    name: str
    stages: list[str] = field(default_factory=list)
    tasks: dict[str, Task] = field(default_factory=dict)
    transitions: dict[tuple[str, str], callable] = field(default_factory=dict)


class Workflow:
    """Orchestrates task execution through defined stages."""

    def __init__(self, config: WorkflowConfig, definition: WorkflowDefinition | None = None):
        self.config = config
        self.definition = definition or WorkflowDefinition(name=config.name)

        # Initialize state machine
        self.state_machine = StateMachine(initial_state=WorkflowState.PENDING)
        self._setup_state_machine()

        # Initialize scheduler
        self.scheduler = TaskScheduler(ScheduleConfig())

        # Metadata
        self.created_at = datetime.utcnow()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.current_stage: int = 0
        self.results: dict[str, any] = {}

    def _setup_state_machine(self) -> None:
        """Setup state machine transitions."""
        # Define all possible transitions
        self.state_machine.add_transition(WorkflowState.PENDING, WorkflowState.RUNNING)
        self.state_machine.add_transition(WorkflowState.RUNNING, WorkflowState.PAUSED)
        self.state_machine.add_transition(WorkflowState.PAUSED, WorkflowState.RUNNING)
        self.state_machine.add_transition(WorkflowState.RUNNING, WorkflowState.COMPLETED)
        self.state_machine.add_transition(WorkflowState.RUNNING, WorkflowState.FAILED)
        self.state_machine.add_transition(WorkflowState.PENDING, WorkflowState.CANCELLED)
        self.state_machine.add_transition(WorkflowState.RUNNING, WorkflowState.CANCELLED)
        self.state_machine.add_transition(WorkflowState.PAUSED, WorkflowState.CANCELLED)

    def add_stage(self, stage_name: str) -> None:
        """Add a stage to the workflow."""
        if stage_name not in self.definition.stages:
            self.definition.stages.append(stage_name)

    def add_task(self, stage: str, task_id: str, task: Task) -> None:
        """Add a task to a stage."""
        key = f"{stage}:{task_id}"
        self.definition.tasks[key] = task

    def add_transition_condition(self, from_stage: str, to_stage: str, condition: callable) -> None:
        """Add a conditional transition between stages."""
        key = (from_stage, to_stage)
        self.definition.transitions[key] = condition

    def start(self) -> bool:
        """Start the workflow execution."""
        if not self.state_machine.transition(WorkflowState.RUNNING):
            return False

        self.started_at = datetime.utcnow()
        self.current_stage = 0
        return True

    def pause(self) -> bool:
        """Pause the workflow."""
        return self.state_machine.transition(WorkflowState.PAUSED)

    def resume(self) -> bool:
        """Resume the workflow."""
        return self.state_machine.transition(WorkflowState.RUNNING)

    def cancel(self) -> bool:
        """Cancel the workflow."""
        return self.state_machine.transition(WorkflowState.CANCELLED)

    def execute(self) -> bool:
        """Execute the workflow through all stages."""
        if not self.start():
            return False

        try:
            for stage_idx, stage_name in enumerate(self.definition.stages):
                self.current_stage = stage_idx

                # Get tasks for this stage
                stage_tasks = {
                    task_id: task
                    for task_id, task in self.definition.tasks.items()
                    if task_id.startswith(f"{stage_name}:")
                }

                if not stage_tasks:
                    continue

                # Execute tasks in this stage
                if self.config.allow_concurrent_tasks:
                    results = self.scheduler.execute_batch(stage_tasks)
                else:
                    results = {}
                    for task_id, task in stage_tasks.items():
                        result = self.scheduler.execute(task_id, task)
                        results[task_id] = result

                # Check for failures
                if any(not result.success for result in results.values()):
                    self.state_machine.transition(WorkflowState.FAILED)
                    self.completed_at = datetime.utcnow()
                    return False

                self.results.update(results)

                # Check transition condition to next stage
                if stage_idx < len(self.definition.stages) - 1:
                    next_stage = self.definition.stages[stage_idx + 1]
                    key = (stage_name, next_stage)
                    if key in self.definition.transitions:
                        condition = self.definition.transitions[key]
                        if not condition(self.results):
                            self.state_machine.transition(WorkflowState.FAILED)
                            self.completed_at = datetime.utcnow()
                            return False

            # All stages completed successfully
            self.state_machine.transition(WorkflowState.COMPLETED)
            self.completed_at = datetime.utcnow()
            return True

        except Exception:
            self.state_machine.transition(WorkflowState.FAILED)
            self.completed_at = datetime.utcnow()
            return False

    def get_status(self) -> dict:
        """Get workflow status."""
        duration = None
        if self.started_at:
            end_time = self.completed_at or datetime.utcnow()
            duration = (end_time - self.started_at).total_seconds()

        return {
            "name": self.config.name,
            "state": self.state_machine.current_state.value,
            "current_stage": self.current_stage,
            "total_stages": len(self.definition.stages),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": duration,
            "scheduler_stats": self.scheduler.get_stats(),
        }

    def get_results(self) -> dict:
        """Get workflow execution results."""
        return self.results.copy()
