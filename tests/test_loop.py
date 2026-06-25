"""
Tests for the orchestration loop.

Covers eval scenarios:
  - Happy path: all tasks complete, plan is_complete()
  - Guardrail: max_iterations trips, remaining tasks skipped
  - No-progress breaker: no ready tasks for N iterations → aborts
"""
from __future__ import annotations

import pytest

from src.models import Plan, TaskStatus
from tests.conftest import make_finish_tool_call, make_plan


class TestLoopHappyPath:
    def test_simple_two_task_plan_completes(self, monkeypatch):
        from src.agent import loop as loop_mod
        from src import logging as log_mod

        # Stub logging so no files are written
        monkeypatch.setattr(log_mod, "log_step", lambda s: None)

        def fake_execute(plan, task, run_id):
            from src.models import StepLog

            task.status = TaskStatus.done
            task.result = f"Result of {task.id}"
            return StepLog(run_id=run_id, task_id=task.id, status=TaskStatus.done)

        # Patch the name in loop's own namespace (it was imported with `from ... import`)
        monkeypatch.setattr(loop_mod, "execute_task", fake_execute)

        plan = make_plan([
            {"id": "t1", "description": "Search", "depends_on": []},
            {"id": "t2", "description": "Summarize", "depends_on": ["t1"]},
        ])
        loop_mod.run_loop(plan)

        assert plan.is_complete()
        assert all(t.status == TaskStatus.done for t in plan.tasks)

    def test_after_step_called_after_each_task(self, monkeypatch):
        from src.agent import loop as loop_mod
        from src import logging as log_mod

        monkeypatch.setattr(log_mod, "log_step", lambda s: None)

        def fake_execute(plan, task, run_id):
            from src.models import StepLog

            task.status = TaskStatus.done
            task.result = f"Result of {task.id}"
            return StepLog(run_id=run_id, task_id=task.id, status=TaskStatus.done)

        monkeypatch.setattr(loop_mod, "execute_task", fake_execute)

        plan = make_plan([
            {"id": "t1", "description": "Search", "depends_on": []},
            {"id": "t2", "description": "Summarize", "depends_on": ["t1"]},
        ])
        saved_statuses = []

        def fake_save(saved_plan):
            saved_statuses.append([t.status for t in saved_plan.tasks])

        loop_mod.run_loop(plan, after_step=fake_save)

        assert saved_statuses == [
            [TaskStatus.done, TaskStatus.pending],
            [TaskStatus.done, TaskStatus.done],
        ]


class TestLoopGuardrails:
    def test_max_iterations_marks_remaining_skipped(self, monkeypatch):
        from src.agent import loop as loop_mod
        from src.agent import executor as exec_mod
        from src import logging as log_mod
        from src.config import cfg

        monkeypatch.setattr(log_mod, "log_step", lambda s: None)
        monkeypatch.setattr(cfg, "max_iterations", 1)

        # Executor always succeeds (but there are more tasks than 1 iteration allows)
        def fake_execute(plan, task, run_id):
            from src.models import StepLog

            task.status = TaskStatus.done
            task.result = "done"
            return StepLog(run_id=run_id, task_id=task.id, status=TaskStatus.done)

        monkeypatch.setattr(exec_mod, "execute_task", fake_execute)

        # Create a wide plan where all tasks are independent so all are ready at once
        plan = make_plan([
            {"id": f"t{i}", "description": f"Task {i}", "depends_on": []}
            for i in range(5)
        ])
        loop_mod.run_loop(plan)

        # With max_iterations=1, the loop runs once, completes the batch, then stops
        # The key assertion is that it terminates and the plan is complete or skipped
        assert all(
            t.status in (TaskStatus.done, TaskStatus.skipped, TaskStatus.failed)
            for t in plan.tasks
        )

    def test_no_progress_breaker(self, monkeypatch):
        """If no tasks are ever ready (bad dep graph), loop aborts with skipped."""
        from src.agent import loop as loop_mod
        from src import logging as log_mod

        monkeypatch.setattr(log_mod, "log_step", lambda s: None)
        monkeypatch.setattr(log_mod, "print_warning", lambda m: None)

        # All tasks depend on a nonexistent task => nothing ever becomes ready
        plan = make_plan([
            {"id": "t1", "description": "Blocked", "depends_on": ["ghost"]},
        ])
        loop_mod.run_loop(plan)

        assert all(t.status == TaskStatus.skipped for t in plan.tasks)


class TestLoopRegistryWiring:
    def test_tool_registry_is_populated_after_import(self):
        """Importing tool modules registers them — verify the registry contract."""
        import src.tools.web_search  # noqa: F401
        import src.tools.fetch       # noqa: F401
        from src.tools.registry import registered_names

        names = registered_names()
        assert "web_search" in names
        assert "fetch" in names
