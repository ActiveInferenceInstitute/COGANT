"""Tests for the workflow engine."""

import pytest
from datetime import datetime

from engine import Workflow, WorkflowConfig, WorkflowDefinition
from state import WorkflowState
from tasks import SimpleTask, TaskConfig, TaskResult
from scheduler import TaskScheduler, ScheduleConfig, RetryStrategy


class TestStateMachine:
    """Tests for state machine functionality."""

    def test_initial_state(self):
        """Test workflow starts in PENDING state."""
        config = WorkflowConfig(name="test")
        workflow = Workflow(config)
        assert workflow.state_machine.current_state == WorkflowState.PENDING

    def test_state_transitions(self):
        """Test valid state transitions."""
        config = WorkflowConfig(name="test")
        workflow = Workflow(config)

        assert workflow.state_machine.transition(WorkflowState.RUNNING)
        assert workflow.state_machine.current_state == WorkflowState.RUNNING

        assert workflow.state_machine.transition(WorkflowState.PAUSED)
        assert workflow.state_machine.current_state == WorkflowState.PAUSED

        assert workflow.state_machine.transition(WorkflowState.RUNNING)
        assert workflow.state_machine.current_state == WorkflowState.RUNNING

    def test_invalid_state_transition(self):
        """Test invalid transitions are rejected."""
        config = WorkflowConfig(name="test")
        workflow = Workflow(config)

        # Can't go directly to COMPLETED from PENDING
        assert not workflow.state_machine.transition(WorkflowState.COMPLETED)
        assert workflow.state_machine.current_state == WorkflowState.PENDING


class TestWorkflow:
    """Tests for workflow execution."""

    def test_start_workflow(self):
        """Test starting a workflow."""
        config = WorkflowConfig(name="test")
        workflow = Workflow(config)

        assert workflow.start()
        assert workflow.state_machine.current_state == WorkflowState.RUNNING
        assert workflow.started_at is not None

    def test_pause_resume(self):
        """Test pausing and resuming workflow."""
        config = WorkflowConfig(name="test")
        workflow = Workflow(config)

        workflow.start()
        assert workflow.pause()
        assert workflow.state_machine.current_state == WorkflowState.PAUSED

        assert workflow.resume()
        assert workflow.state_machine.current_state == WorkflowState.RUNNING

    def test_cancel_workflow(self):
        """Test cancelling a workflow."""
        config = WorkflowConfig(name="test")
        workflow = Workflow(config)

        workflow.start()
        assert workflow.cancel()
        assert workflow.state_machine.current_state == WorkflowState.CANCELLED

    def test_add_stages(self):
        """Test adding stages to workflow."""
        config = WorkflowConfig(name="test")
        workflow = Workflow(config)

        workflow.add_stage("validate")
        workflow.add_stage("process")
        workflow.add_stage("complete")

        assert len(workflow.definition.stages) == 3
        assert workflow.definition.stages == ["validate", "process", "complete"]

    def test_add_tasks(self):
        """Test adding tasks to stages."""
        config = WorkflowConfig(name="test")
        workflow = Workflow(config)
        workflow.add_stage("validate")

        task_config = TaskConfig(name="check_input")
        task = SimpleTask(task_config, lambda: True)

        workflow.add_task("validate", "task1", task)
        assert "validate:task1" in workflow.definition.tasks


class TestScheduler:
    """Tests for task scheduler."""

    def test_schedule_task(self):
        """Test scheduling a task."""
        scheduler = TaskScheduler()
        task_config = TaskConfig(name="test")
        task = SimpleTask(task_config, lambda: "result")

        scheduler.schedule("task1", task)
        assert "task1" in scheduler.scheduled_tasks

    def test_execute_successful_task(self):
        """Test executing a successful task."""
        scheduler = TaskScheduler()
        task_config = TaskConfig(name="test")
        task = SimpleTask(task_config, lambda: "success")

        result = scheduler.execute("task1", task)
        assert result.success
        assert result.output == "success"
        assert result.duration_seconds >= 0

    def test_execute_failing_task(self):
        """Test executing a failing task."""
        scheduler = TaskScheduler()
        task_config = TaskConfig(name="test")

        def failing_operation():
            raise ValueError("Task failed")

        task = SimpleTask(task_config, failing_operation)
        result = scheduler.execute("task1", task)

        assert not result.success
        assert "Task failed" in result.error

    def test_retry_strategy_exponential(self):
        """Test exponential backoff retry strategy."""
        config = ScheduleConfig(strategy=RetryStrategy.EXPONENTIAL_BACKOFF, initial_delay=1)
        scheduler = TaskScheduler(config)

        delays = [
            scheduler._get_retry_delay(0),  # 1s
            scheduler._get_retry_delay(1),  # 2s
            scheduler._get_retry_delay(2),  # 4s
        ]

        assert delays[0] == 1
        assert delays[1] == 2
        assert delays[2] == 4

    def test_retry_strategy_linear(self):
        """Test linear backoff retry strategy."""
        config = ScheduleConfig(strategy=RetryStrategy.LINEAR_BACKOFF, initial_delay=1)
        scheduler = TaskScheduler(config)

        delays = [
            scheduler._get_retry_delay(0),  # 1s
            scheduler._get_retry_delay(1),  # 2s
            scheduler._get_retry_delay(2),  # 3s
        ]

        assert delays[0] == 1
        assert delays[1] == 2
        assert delays[2] == 3

    def test_batch_execution(self):
        """Test executing multiple tasks."""
        scheduler = TaskScheduler()

        tasks = {}
        for i in range(3):
            config = TaskConfig(name=f"task{i}")
            task = SimpleTask(config, lambda x=i: f"result{x}")
            tasks[f"task{i}"] = task

        results = scheduler.execute_batch(tasks)

        assert len(results) == 3
        assert all(result.success for result in results.values())

    def test_execution_history(self):
        """Test tracking execution history."""
        scheduler = TaskScheduler()
        task_config = TaskConfig(name="test")
        task = SimpleTask(task_config, lambda: "result")

        scheduler.execute("task1", task)
        scheduler.execute("task2", task)

        history = scheduler.get_execution_history()
        assert len(history) == 2

        history1 = scheduler.get_execution_history("task1")
        assert len(history1) == 1

    def test_scheduler_stats(self):
        """Test scheduler statistics."""
        scheduler = TaskScheduler()

        # Execute some successful tasks
        for i in range(3):
            config = TaskConfig(name=f"task{i}")
            task = SimpleTask(config, lambda: "result")
            scheduler.execute(f"task{i}", task)

        stats = scheduler.get_stats()

        assert stats["total_executions"] == 3
        assert stats["successful"] == 3
        assert stats["failed"] == 0
        assert stats["success_rate"] == 100.0


class TestWorkflowExecution:
    """Tests for complete workflow execution."""

    def test_simple_workflow(self):
        """Test executing a simple workflow."""
        config = WorkflowConfig(name="simple")
        definition = WorkflowDefinition(name="simple")
        workflow = Workflow(config, definition)

        # Create workflow with one stage and one task
        workflow.add_stage("process")

        task_config = TaskConfig(name="work")
        task = SimpleTask(task_config, lambda: "done")
        workflow.add_task("process", "work", task)

        # Execute
        assert workflow.execute()
        assert workflow.state_machine.current_state == WorkflowState.COMPLETED

    def test_multi_stage_workflow(self):
        """Test executing a multi-stage workflow."""
        config = WorkflowConfig(name="multi")
        workflow = Workflow(config)

        # Create three stages
        for stage in ["validate", "process", "finalize"]:
            workflow.add_stage(stage)
            task_config = TaskConfig(name=f"{stage}_task")
            task = SimpleTask(task_config, lambda s=stage: f"{s}_done")
            workflow.add_task(stage, "task", task)

        assert workflow.execute()
        assert workflow.state_machine.current_state == WorkflowState.COMPLETED
        assert len(workflow.get_results()) == 3

    def test_workflow_with_failure(self):
        """Test workflow fails when a task fails."""
        config = WorkflowConfig(name="failing")
        workflow = Workflow(config)

        workflow.add_stage("stage1")
        workflow.add_stage("stage2")

        # Successful task in stage 1
        task_config = TaskConfig(name="task1")
        task = SimpleTask(task_config, lambda: "success")
        workflow.add_task("stage1", "task", task)

        # Failing task in stage 2
        task_config = TaskConfig(name="task2")

        def failing():
            raise Exception("Intentional failure")

        task = SimpleTask(task_config, failing)
        workflow.add_task("stage2", "task", task)

        assert not workflow.execute()
        assert workflow.state_machine.current_state == WorkflowState.FAILED

    def test_workflow_status(self):
        """Test getting workflow status."""
        config = WorkflowConfig(name="test")
        workflow = Workflow(config)

        workflow.add_stage("work")
        task_config = TaskConfig(name="task")
        task = SimpleTask(task_config, lambda: "done")
        workflow.add_task("work", "task", task)

        workflow.execute()

        status = workflow.get_status()
        assert status["name"] == "test"
        assert status["state"] == "completed"
        assert status["total_stages"] == 1
        assert status["current_stage"] == 0
        assert status["duration_seconds"] is not None
