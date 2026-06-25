"""
Tests for the executor: tool dispatch, finish_task handling, guardrail cap.

Covers eval scenarios:
  - Real tool use (tool is called, result captured)
  - Tool failure handling (tool raises, task still completes)
  - Per-task tool-call cap (loop forced to finish)
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.models import Plan, Task, TaskStatus
from tests.conftest import make_finish_tool_call, make_plan, make_text_message


class TestExecutorFinishTask:
    def test_finish_task_marks_done(self, stub_llm):
        from src.agent.executor import execute_task

        stub_llm([make_finish_tool_call("Found something useful.", ["https://example.com"])])
        plan = make_plan([{"id": "t1", "description": "Search", "depends_on": []}])
        task = plan.tasks[0]

        step = execute_task(plan, task, plan.run_id)

        assert task.status == TaskStatus.done
        assert "Found something useful" in task.result
        assert step.status == TaskStatus.done

    def test_text_response_marks_done(self, stub_llm):
        """Model returns plain text instead of calling finish_task — still done."""
        from src.agent.executor import execute_task

        stub_llm([make_text_message("Here is my answer.")])
        plan = make_plan([{"id": "t1", "description": "Search", "depends_on": []}])
        task = plan.tasks[0]

        step = execute_task(plan, task, plan.run_id)

        assert task.status == TaskStatus.done

    def test_sources_appended_to_result(self, stub_llm):
        from src.agent.executor import execute_task

        stub_llm([
            make_finish_tool_call("Result text.", ["https://a.com", "https://b.com"])
        ])
        plan = make_plan([{"id": "t1", "description": "Search", "depends_on": []}])
        task = plan.tasks[0]
        execute_task(plan, task, plan.run_id)

        assert "https://a.com" in task.result or "Sources" in task.result


class TestExecutorToolDispatch:
    def test_tool_call_dispatched_and_fed_back(self, stub_llm, monkeypatch):
        """Executor dispatches a web_search, then calls finish_task."""
        from src.agent.executor import execute_task
        from src.tools import registry as reg

        # Register a fake tool
        from src.tools.registry import ToolSpec
        reg.register("web_search", ToolSpec(
            fn=lambda query: "Result for: " + query,
            description="Search",
            parameters={"query": {"type": "string", "description": "query"}},
        ))

        # First call: model calls web_search
        tc_search = MagicMock()
        tc_search.id = "call_s1"
        tc_search.function.name = "web_search"
        tc_search.function.arguments = json.dumps({"query": "managed postgres"})

        msg_search = MagicMock()
        msg_search.content = None
        msg_search.tool_calls = [tc_search]

        # Second call: model calls finish_task
        stub_llm([msg_search, make_finish_tool_call("Postgres options found.")])

        plan = make_plan([{"id": "t1", "description": "Search Postgres", "depends_on": []}])
        task = plan.tasks[0]
        step = execute_task(plan, task, plan.run_id)

        assert task.status == TaskStatus.done
        tool_names = [tc.name for tc in step.tool_calls]
        assert "web_search" in tool_names


class TestExecutorToolFailure:
    def test_tool_error_handled_gracefully(self, stub_llm, monkeypatch):
        """A failing tool should not crash the executor — task still finishes."""
        from src.agent.executor import execute_task
        from src.tools import registry as reg
        from src.tools.registry import ToolSpec

        reg.register("web_search", ToolSpec(
            fn=lambda query: (_ for _ in ()).throw(RuntimeError("Network error")),
            description="Search",
            parameters={"query": {"type": "string", "description": "query"}},
        ))

        tc_fail = MagicMock()
        tc_fail.id = "call_f1"
        tc_fail.function.name = "web_search"
        tc_fail.function.arguments = json.dumps({"query": "anything"})

        msg_fail = MagicMock()
        msg_fail.content = None
        msg_fail.tool_calls = [tc_fail]

        stub_llm([msg_fail, make_finish_tool_call("Could not find data, here is what I have.")])

        plan = make_plan([{"id": "t1", "description": "Search", "depends_on": []}])
        task = plan.tasks[0]
        step = execute_task(plan, task, plan.run_id)

        # Task still completes (not failed) because the model called finish_task
        assert task.status == TaskStatus.done
        assert any(tc.error is not None for tc in step.tool_calls if tc.name == "web_search")

    def test_empty_tool_result_finishes_without_fabricating(self, stub_llm, monkeypatch):
        """Empty search results should lead to an honest completion, not invented facts."""
        from src.agent.executor import execute_task
        from src.tools import registry as reg
        from src.tools.registry import ToolSpec

        reg.register("web_search", ToolSpec(
            fn=lambda query: "",
            description="Search",
            parameters={"query": {"type": "string", "description": "query"}},
        ))

        tc_empty = MagicMock()
        tc_empty.id = "call_empty"
        tc_empty.function.name = "web_search"
        tc_empty.function.arguments = json.dumps({"query": "Zorbix Quantum Notes pricing"})

        msg_empty = MagicMock()
        msg_empty.content = None
        msg_empty.tool_calls = [tc_empty]

        stub_llm([
            msg_empty,
            make_finish_tool_call(
                "No reliable official pricing source was found from the search result.",
                [],
            ),
        ])

        plan = make_plan([{"id": "t1", "description": "Search official pricing", "depends_on": []}])
        task = plan.tasks[0]
        step = execute_task(plan, task, plan.run_id)

        assert task.status == TaskStatus.done
        assert "No reliable official pricing source" in (task.result or "")
        assert "official pricing source was found" in (step.result_summary or "")
        assert "19.99" not in (task.result or "")
        assert any(tc.name == "web_search" and tc.result == "" for tc in step.tool_calls)


class TestExecutorToolCap:
    def test_cap_forces_finish(self, monkeypatch):
        """When tool call cap is hit, executor sends a nudge and model must finish."""
        from src.agent.executor import execute_task
        from src.tools import registry as reg
        from src.tools.registry import ToolSpec
        from src.config import cfg

        monkeypatch.setattr(cfg, "max_tool_calls_per_task", 1)

        reg.register("web_search", ToolSpec(
            fn=lambda query: "some result",
            description="Search",
            parameters={"query": {"type": "string", "description": "query"}},
        ))

        tc = MagicMock()
        tc.id = "call_c1"
        tc.function.name = "web_search"
        tc.function.arguments = json.dumps({"query": "q"})

        msg_tool = MagicMock()
        msg_tool.content = None
        msg_tool.tool_calls = [tc]

        call_count = [0]

        def fake_act(messages, tools):
            call_count[0] += 1
            if call_count[0] <= 1:
                return msg_tool, 10
            return make_finish_tool_call("Done after cap."), 10

        import src.llm.client as client_mod
        monkeypatch.setattr(client_mod.llm, "act", fake_act)

        plan = make_plan([{"id": "t1", "description": "Search", "depends_on": []}])
        task = plan.tasks[0]
        step = execute_task(plan, task, plan.run_id)

        assert task.status == TaskStatus.done
