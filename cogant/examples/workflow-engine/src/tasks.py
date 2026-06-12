"""Task definitions for workflow engine."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TaskResult:
    """Result of task execution."""

    success: bool
    output: Any = None
    error: str | None = None
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskConfig:
    """Configuration for a task."""

    name: str
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 5
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


class Task(ABC):
    """Abstract base class for tasks."""

    def __init__(self, config: TaskConfig):
        self.config = config
        self.result: TaskResult | None = None
        self.retry_count = 0
        self.created_at = datetime.utcnow()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None

    @abstractmethod
    def execute(self) -> TaskResult:
        """Execute the task."""
        pass

    def get_duration(self) -> float | None:
        """Get task execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return self.retry_count < self.config.max_retries

    def get_retry_delay(self) -> int:
        """Get delay before next retry in seconds."""
        return self.config.retry_delay_seconds * (2**self.retry_count)


class SimpleTask(Task):
    """Simple synchronous task."""

    def __init__(self, config: TaskConfig, operation: callable):
        super().__init__(config)
        self.operation = operation

    def execute(self) -> TaskResult:
        """Execute the task."""
        self.started_at = datetime.utcnow()
        try:
            output = self.operation()
            self.completed_at = datetime.utcnow()
            duration = self.get_duration() or 0.0
            return TaskResult(
                success=True,
                output=output,
                duration_seconds=duration,
            )
        except Exception as e:
            self.completed_at = datetime.utcnow()
            duration = self.get_duration() or 0.0
            return TaskResult(
                success=False,
                error=str(e),
                duration_seconds=duration,
            )


class DatabaseTask(Task):
    """Task that performs database operations."""

    def __init__(self, config: TaskConfig, query: str, params: dict | None = None):
        super().__init__(config)
        self.query = query
        self.params = params or {}

    def execute(self) -> TaskResult:
        """Execute simulated database query."""
        self.started_at = datetime.utcnow()
        try:
            # In a real implementation, this would execute the query
            result = {"rows_affected": 0, "query": self.query}
            self.completed_at = datetime.utcnow()
            duration = self.get_duration() or 0.0
            return TaskResult(
                success=True,
                output=result,
                duration_seconds=duration,
            )
        except Exception as e:
            self.completed_at = datetime.utcnow()
            duration = self.get_duration() or 0.0
            return TaskResult(
                success=False,
                error=str(e),
                duration_seconds=duration,
            )


class HttpTask(Task):
    """Task that makes HTTP requests."""

    def __init__(
        self,
        config: TaskConfig,
        url: str,
        method: str = "GET",
        headers: dict | None = None,
        data: dict | None = None,
    ):
        super().__init__(config)
        self.url = url
        self.method = method
        self.headers = headers or {}
        self.data = data

    def execute(self) -> TaskResult:
        """Execute simulated HTTP request."""
        self.started_at = datetime.utcnow()
        try:
            # In a real implementation, this would make an HTTP request
            result = {
                "method": self.method,
                "url": self.url,
                "status_code": 200,
            }
            self.completed_at = datetime.utcnow()
            duration = self.get_duration() or 0.0
            return TaskResult(
                success=True,
                output=result,
                duration_seconds=duration,
            )
        except Exception as e:
            self.completed_at = datetime.utcnow()
            duration = self.get_duration() or 0.0
            return TaskResult(
                success=False,
                error=str(e),
                duration_seconds=duration,
            )
