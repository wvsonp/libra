"""
Tests for Plan / Task models: schema validation, ready_tasks logic,
compact_view, is_complete.
"""
from __future__ import annotations

import pytest

from src.models import Plan, Task, TaskStatus
from tests.conftest import make_plan


class TestPlanReadyTasks:
    def test_no_deps_all_pending_returns_all(self):
        plan = make_plan([
            {"id": "a", "description": "Task A", "depends_on": []},
            {"id": "b", "description": "Task B", "depends_on": []},
        ])
        ready = plan.ready_tasks()
        assert {t.id for t in ready} == {"a", "b"}

    def test_dep_satisfied_unlocks_task(self):
        plan = make_plan([
            {"id": "a", "description": "Task A", "depends_on": []},
            {"id": "b", "description": "Task B", "depends_on": ["a"]},
        ])
        plan.tasks[0].status = TaskStatus.done
        ready = plan.ready_tasks()
        assert [t.id for t in ready] == ["b"]

    def test_dep_not_done_blocks_task(self):
        plan = make_plan([
            {"id": "a", "description": "Task A", "depends_on": []},
            {"id": "b", "description": "Task B", "depends_on": ["a"]},
        ])
        # a is still pending
        ready = plan.ready_tasks()
        ids = [t.id for t in ready]
        assert "b" not in ids
        assert "a" in ids

    def test_in_progress_task_not_in_ready(self):
        plan = make_plan([
            {"id": "a", "description": "Task A", "depends_on": []},
        ])
        plan.tasks[0].status = TaskStatus.in_progress
        assert plan.ready_tasks() == []


class TestPlanIsComplete:
    def test_all_done_is_complete(self):
        plan = make_plan([
            {"id": "a", "description": "A", "depends_on": []},
        ])
        plan.tasks[0].status = TaskStatus.done
        assert plan.is_complete()

    def test_one_pending_not_complete(self):
        plan = make_plan([
            {"id": "a", "description": "A", "depends_on": []},
            {"id": "b", "description": "B", "depends_on": []},
        ])
        plan.tasks[0].status = TaskStatus.done
        assert not plan.is_complete()

    def test_failed_and_skipped_count_as_complete(self):
        plan = make_plan([
            {"id": "a", "description": "A", "depends_on": []},
            {"id": "b", "description": "B", "depends_on": []},
        ])
        plan.tasks[0].status = TaskStatus.failed
        plan.tasks[1].status = TaskStatus.skipped
        assert plan.is_complete()


class TestPlanCompactView:
    def test_compact_view_includes_all_ids(self):
        plan = make_plan([
            {"id": "search_x", "description": "Search for X", "depends_on": []},
            {"id": "summarize", "description": "Summarize", "depends_on": ["search_x"]},
        ])
        view = plan.compact_view()
        assert "search_x" in view
        assert "summarize" in view
        assert "pending" in view
