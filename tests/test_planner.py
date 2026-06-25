"""
Tests for the planner: schema validation, error recovery (re-ask on bad plan).

LLM is stubbed so tests run offline and are deterministic.
"""
from __future__ import annotations

import json
import pytest

from src.models import Plan


class TestPlannerSchemaValidation:
    """Unit tests for the internal validation helpers in planner.py."""

    def test_valid_plan_passes(self):
        from src.agent.planner import _raw_to_plan, _validate_task_ids

        raw = {
            "goal": "test",
            "tasks": [
                {"id": "search", "description": "Search", "depends_on": []},
                {"id": "summarize", "description": "Summarize", "depends_on": ["search"]},
            ],
        }
        plan = _raw_to_plan("test", raw)
        assert _validate_task_ids(plan) == []

    def test_duplicate_ids_caught(self):
        from src.agent.planner import _raw_to_plan, _validate_task_ids

        raw = {
            "goal": "test",
            "tasks": [
                {"id": "a", "description": "A", "depends_on": []},
                {"id": "a", "description": "A dup", "depends_on": []},
            ],
        }
        plan = _raw_to_plan("test", raw)
        errors = _validate_task_ids(plan)
        assert any("Duplicate" in e for e in errors)

    def test_unknown_dep_caught(self):
        from src.agent.planner import _raw_to_plan, _validate_task_ids

        raw = {
            "goal": "test",
            "tasks": [
                {"id": "a", "description": "A", "depends_on": ["nonexistent"]},
            ],
        }
        plan = _raw_to_plan("test", raw)
        errors = _validate_task_ids(plan)
        assert any("unknown" in e for e in errors)

    def test_empty_plan_caught(self):
        from src.agent.planner import _raw_to_plan, _validate_task_ids

        raw = {"goal": "test", "tasks": []}
        plan = _raw_to_plan("test", raw)
        errors = _validate_task_ids(plan)
        assert any("no tasks" in e.lower() for e in errors)

    def test_over_max_tasks_caught(self, monkeypatch):
        from src import config
        from src.agent.planner import _raw_to_plan, _validate_task_ids

        monkeypatch.setattr(config.cfg, "max_plan_tasks", 2)
        raw = {
            "goal": "test",
            "tasks": [
                {"id": f"t{i}", "description": f"Task {i}", "depends_on": []}
                for i in range(5)
            ],
        }
        plan = _raw_to_plan("test", raw)
        errors = _validate_task_ids(plan)
        assert any("max" in e.lower() for e in errors)


class TestPlannerRetry:
    """Test that create_plan retries once on validation failure."""

    def test_retries_on_bad_plan(self, monkeypatch):
        from src.agent import planner as planner_mod

        call_count = [0]
        good_raw = {
            "goal": "goal",
            "tasks": [{"id": "t1", "description": "Search", "depends_on": []}],
        }
        bad_raw = {"goal": "goal", "tasks": []}  # fails validation (empty)

        def fake_plan_json(system, user, schema):
            call_count[0] += 1
            return bad_raw if call_count[0] == 1 else good_raw

        import src.llm.client as client_mod
        monkeypatch.setattr(client_mod.llm, "plan_json", fake_plan_json)

        plan = planner_mod.create_plan("goal")
        assert isinstance(plan, Plan)
        assert call_count[0] == 2  # first attempt failed, second succeeded

    def test_raises_after_two_bad_plans(self, monkeypatch):
        from src.agent import planner as planner_mod

        def fake_plan_json(system, user, schema):
            return {"goal": "goal", "tasks": []}  # always invalid

        import src.llm.client as client_mod
        monkeypatch.setattr(client_mod.llm, "plan_json", fake_plan_json)

        with pytest.raises(ValueError):
            planner_mod.create_plan("goal")
