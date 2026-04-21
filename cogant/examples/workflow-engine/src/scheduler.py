"""Task scheduler with retry and backoff logic."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from tasks import Task, TaskResult


class RetryStrategy(str, Enum):
    """Retry strategies."""

    IMMEDIATE = "immediate"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIBONACCI_BACKOFF = "fibonacci_backoff"


@dataclass
class ScheduleConfig:
    """Configuration for task scheduling."""

    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_retries: int = 3
    initial_delay: int = 1  # seconds
    max_delay: int = 300  # 5 minutes
    timeout: int = 300  # 5 minutes


class TaskScheduler:
    """Schedules and executes tasks with retry logic."""

    def __init__(self, config: ScheduleConfig | None = None):
        self.config = config or ScheduleConfig()
        self.scheduled_tasks: dict[str, Task] = {}
        self.execution_history: list[tuple[str, TaskResult, datetime]] = []

    def schedule(self, task_id: str, task: Task) -> None:
        """Schedule a task for execution."""
        self.scheduled_tasks[task_id] = task

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        if task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task_id]
            return True
        return False

    def _get_retry_delay(self, retry_count: int) -> int:
        """Calculate retry delay based on strategy."""
        if self.config.strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.initial_delay * (retry_count + 1)
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.initial_delay * (2**retry_count)
        elif self.config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = self._fibonacci(retry_count + 1) * self.config.initial_delay
        else:
            delay = self.config.initial_delay

        return min(delay, self.config.max_delay)

    @staticmethod
    def _fibonacci(n: int) -> int:
        """Calculate nth Fibonacci number."""
        if n <= 1:
            return 1
        a, b = 1, 1
        for _ in range(n - 1):
            a, b = b, a + b
        return b

    def execute(self, task_id: str, task: Task) -> TaskResult:
        """Execute a task with retry logic."""
        result = None
        retry_count = 0

        while retry_count <= self.config.max_retries:
            try:
                result = task.execute()

                if result.success:
                    self.execution_history.append((task_id, result, datetime.utcnow()))
                    return result

                retry_count += 1
                if retry_count <= self.config.max_retries:
                    delay = self._get_retry_delay(retry_count - 1)
                    if delay > 0:
                        # In real implementation, would use asyncio.sleep or similar
                        pass

            except Exception as e:
                retry_count += 1
                if retry_count > self.config.max_retries:
                    error_result = TaskResult(
                        success=False,
                        error=f"Task failed after {self.config.max_retries} retries: {str(e)}",
                        duration_seconds=0.0,
                    )
                    self.execution_history.append((task_id, error_result, datetime.utcnow()))
                    return error_result

        if result is None:
            result = TaskResult(
                success=False,
                error="Task execution failed",
                duration_seconds=0.0,
            )

        self.execution_history.append((task_id, result, datetime.utcnow()))
        return result

    async def execute_async(self, task_id: str, task: Task) -> TaskResult:
        """Execute a task asynchronously with retry logic."""
        # For async execution, we'd use asyncio.sleep for delays
        result = self.execute(task_id, task)
        return result

    def execute_batch(self, tasks: dict[str, Task]) -> dict[str, TaskResult]:
        """Execute multiple tasks."""
        results = {}
        for task_id, task in tasks.items():
            results[task_id] = self.execute(task_id, task)
        return results

    def get_execution_history(self, task_id: str | None = None):
        """Get execution history for a task or all tasks."""
        if task_id:
            return [
                (tid, result, timestamp)
                for tid, result, timestamp in self.execution_history
                if tid == task_id
            ]
        return self.execution_history

    def get_stats(self) -> dict:
        """Get scheduler statistics."""
        total_executions = len(self.execution_history)
        successful = sum(1 for _, result, _ in self.execution_history if result.success)
        failed = total_executions - successful

        total_duration = sum(result.duration_seconds for _, result, _ in self.execution_history)
        avg_duration = total_duration / total_executions if total_executions > 0 else 0

        return {
            "total_executions": total_executions,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total_executions * 100) if total_executions > 0 else 0,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": avg_duration,
        }
