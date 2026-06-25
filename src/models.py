"""Pydantic schemas for structured LLM output."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"
    failed = "failed"
    skipped = "skipped"


class Task(BaseModel):
    id: str
    description: str
    depends_on: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.pending
    result: str | None = None
    error: str | None = None


class Plan(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    goal: str
    tasks: list[Task]

    def ready_tasks(self) -> list[Task]:
        done = {t.id for t in self.tasks if t.status == TaskStatus.done}
        return [
            t for t in self.tasks
            if t.status == TaskStatus.pending and all(d in done for d in t.depends_on)
        ]

    def is_complete(self) -> bool:
        terminal = (TaskStatus.done, TaskStatus.failed, TaskStatus.skipped)
        return all(t.status in terminal for t in self.tasks)

    def compact_view(self) -> str:
        return "\n".join(
            f"[{t.status.value:<11}] {t.id}: {t.description}" for t in self.tasks
        )


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: str | None = None
    error: str | None = None


class StepLog(BaseModel):
    run_id: str
    task_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: TaskStatus
    tool_calls: list[ToolCall] = Field(default_factory=list)
    result_summary: str | None = None
    error: str | None = None
    tokens_used: int | None = None
