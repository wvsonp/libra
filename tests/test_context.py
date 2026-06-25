"""
Tests for context compaction (eval scenario: context bounds).

Verifies that per-task context includes only the task + dep outputs (not all tasks)
and that long dep outputs are trimmed to the cap.
"""
from __future__ import annotations

import pytest

from src.models import TaskStatus
from tests.conftest import make_plan


class TestContextCompaction:
    def test_messages_contain_task_id(self):
        from src.agent.context import build_executor_messages

        plan = make_plan([
            {"id": "search_x", "description": "Search for X", "depends_on": []},
        ])
        msgs = build_executor_messages(plan, plan.tasks[0], max_tool_calls=3)
        system_content = msgs[0]["content"]
        assert "search_x" in system_content

    def test_only_dep_outputs_included(self):
        """Non-dependency task results must NOT appear in context."""
        from src.agent.context import build_executor_messages

        plan = make_plan([
            {"id": "t1", "description": "Task 1", "depends_on": []},
            {"id": "t2", "description": "Task 2", "depends_on": []},
            {"id": "t3", "description": "Task 3", "depends_on": ["t1"]},
        ])
        plan.tasks[0].status = TaskStatus.done
        plan.tasks[0].result = "Result of T1 — secret sauce"
        plan.tasks[1].status = TaskStatus.done
        plan.tasks[1].result = "Result of T2 — should not appear"

        # t3 only depends on t1, not t2
        msgs = build_executor_messages(plan, plan.tasks[2], max_tool_calls=3)
        system_content = msgs[0]["content"]

        assert "Result of T1" in system_content
        assert "Result of T2" not in system_content

    def test_long_dep_output_trimmed(self):
        """Dep outputs longer than the cap should be trimmed."""
        from src.agent.context import build_executor_messages, _MAX_DEP_OUTPUT_CHARS

        plan = make_plan([
            {"id": "t1", "description": "Big output task", "depends_on": []},
            {"id": "t2", "description": "Consumer", "depends_on": ["t1"]},
        ])
        plan.tasks[0].status = TaskStatus.done
        plan.tasks[0].result = "X" * (_MAX_DEP_OUTPUT_CHARS + 500)

        msgs = build_executor_messages(plan, plan.tasks[1], max_tool_calls=3)
        system_content = msgs[0]["content"]

        # Context should not contain the full overlong output
        assert len(system_content) < (_MAX_DEP_OUTPUT_CHARS + 500) * 2
        assert "trimmed" in system_content

    def test_no_deps_says_none(self):
        from src.agent.context import build_executor_messages

        plan = make_plan([
            {"id": "t1", "description": "Independent task", "depends_on": []},
        ])
        msgs = build_executor_messages(plan, plan.tasks[0], max_tool_calls=3)
        assert "None" in msgs[0]["content"]
