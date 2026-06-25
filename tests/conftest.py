"""
Shared test fixtures and the stubbed LLM client.

The stub intercepts LLM calls so tests run fully offline (no API key needed)
and are deterministic. Tests cover the loop/planning logic, not the model quality.
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.models import Plan, Task, TaskStatus


# ── Minimal Plan factory ────────────────────────────────────────────────────

def make_plan(tasks: list[dict]) -> Plan:
    return Plan(
        goal="test goal",
        tasks=[Task(**t) for t in tasks],
    )


# ── Stub LLM message ────────────────────────────────────────────────────────

def make_finish_tool_call(result: str = "Test result.", sources: list[str] | None = None):
    """Build a mock assistant message that immediately calls finish_task."""
    tc = MagicMock()
    tc.id = "call_001"
    tc.function.name = "finish_task"
    tc.function.arguments = json.dumps({"result": result, "sources": sources or []})

    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]
    return msg


def make_text_message(content: str):
    """Build a mock assistant message that returns plain text (no tool call)."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = []
    return msg


@pytest.fixture()
def simple_plan():
    return make_plan([
        {"id": "t1", "description": "Search for X", "depends_on": []},
        {"id": "t2", "description": "Summarize findings", "depends_on": ["t1"]},
    ])


@pytest.fixture()
def stub_llm(monkeypatch):
    """
    Returns a callable that replaces llm.act.
    Usage: stub_llm(responses=[msg1, msg2, ...])
    Each call pops the next response from the list.
    """
    import src.llm.client as client_mod

    responses: list[Any] = []

    def _act(messages, tools):
        if responses:
            return responses.pop(0), 10
        return make_finish_tool_call("Fallback finish."), 10

    def _setup(resp_list):
        responses.clear()
        responses.extend(resp_list)
        monkeypatch.setattr(client_mod.llm, "act", _act)
        return _act

    return _setup


@pytest.fixture()
def stub_summarize(monkeypatch):
    """Replace llm.summarize with a simple passthrough for deterministic output."""
    import src.llm.client as client_mod

    monkeypatch.setattr(client_mod.llm, "summarize", lambda system, user: "Stub brief.")
    return client_mod.llm.summarize
